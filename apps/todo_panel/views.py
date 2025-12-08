"""
Vistas de Django para Autenticación y Panel de Tareas
======================================================

Este módulo contiene las vistas que manejan:
- Autenticación OAuth 2.0 con Microsoft (Device Code Flow)
- Gestión de sesiones de usuario
- Visualización del panel de tareas

Flujo de Autenticación:
-----------------------
1. Usuario visita /login
2. Ingresa Client ID de Azure AD
3. Frontend llama a /api/auth/initiate (POST)
4. Backend solicita device code a Microsoft
5. Usuario visita URL y autentica en Microsoft
6. Frontend hace polling a /api/auth/check-status (POST)
7. Backend obtiene tokens y crea/actualiza usuario
8. Usuario es redirigido a /

Seguridad:
----------
- Tokens encriptados en base de datos (Fernet + PBKDF2)
- Client ID hasheado (SHA-256) para identificación
- Sesiones de Django para autenticación
- CSRF protection en todos los POST
- Decorador @login_required para vistas protegidas

Autor: Personal Todo Agent Team
Última modificación: 2025-11-28
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.conf import settings
import hashlib
import json
import logging
from functools import wraps
from typing import Callable
from django.http import HttpResponse
from django.core.cache import cache

from .models import MicrosoftUser
from .services.encryption import encrypt_data, decrypt_data
from .services.microsoft_auth import get_device_code, poll_for_token
from .services.microsoft_client import MicrosoftClient
from .services.task_service import TaskService
from .services.cache_optimizer import CacheOptimizer, RateLimiter
import pandas as pd
import re
import zipfile
import io
from typing import List, Dict


# Configurar logger para este módulo
logger = logging.getLogger(__name__)


def login_required(view_func: Callable) -> Callable:
    """Decorador personalizado para requerir autenticación en vistas."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session:
            logger.debug(f"Usuario no autenticado intentó acceder a {view_func.__name__}")
            return redirect('todo_panel:login')
        
        logger.debug(f"Usuario {request.session['user_id']} accediendo a {view_func.__name__}")
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def login_view(request):
    """Vista de la página de login."""
    if 'user_id' in request.session:
        logger.info(f"Usuario {request.session['user_id']} ya autenticado, redirigiendo a index")
        return redirect('todo_panel:index')
    
    logger.debug("Mostrando página de login")
    return render(request, 'todo_panel/login.html')

@login_required
def profile_view(request):
    """Vista de la página de perfil del usuario."""
    user_id = request.session['user_id']
    try:
        user = MicrosoftUser.objects.get(id=user_id)
        client = MicrosoftClient(user)
        profile_data = client.get_profile()

        context = {
            'profile': profile_data,
        }
        logger.debug(f"Mostrando página de perfil para usuario {user_id}: {profile_data.get('displayName', 'N/A')}")
        return render(request, 'todo_panel/profile.html', context)
    except ObjectDoesNotExist:
        logger.error(f"Usuario con ID {user_id} no encontrado en la base de datos.")
        return redirect('todo_panel:login')
    except Exception as e:
        logger.error(f"Error al obtener el perfil del usuario {user_id}: {e}")
        # Consider a more user-friendly error page or message
        return JsonResponse({'error': 'Error al cargar el perfil'}, status=500)


@require_http_methods(["POST"])
def initiate_auth(request):
    """API endpoint para iniciar el flujo de autenticación OAuth 2.0."""
    try:
        # Parsear JSON del request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning("Request body no es JSON válido")
            return JsonResponse({'error': 'Datos inválidos'}, status=400)
        
        # Extraer y validar client_id
        client_id = data.get('client_id', '').strip()
        
        if not client_id:
            logger.warning("Intento de autenticación sin client_id")
            return JsonResponse({'error': 'Client ID es requerido'}, status=400)
        
        # Validar formato de Client ID
        try:
            from apps.todo_panel.validators import validate_client_id
            validate_client_id(client_id)
        except ValidationError as e:
            logger.warning(f"Client ID inválido: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
        
        logger.info(f"Iniciando autenticación para client_id: {client_id[:8]}...")
        
        # Solicitar device code a Microsoft
        response = get_device_code(client_id)
        
        # Verificar si hubo error
        if 'error' in response:
            error = response.get('error')
            error_description = response.get('error_description', 'Error desconocido')
            
            # Mapeo de errores técnicos a mensajes amigables
            user_friendly_errors = {
                'invalid_client': 'El Client ID proporcionado no es válido. Por favor, verifica que sea correcto.',
                'unauthorized_client': 'El Client ID no está autorizado para usar este flujo de autenticación.',
                'invalid_request': 'La solicitud no es válida. Por favor, intenta nuevamente.',
            }
            
            user_message = user_friendly_errors.get(
                error,
                'Error al iniciar autenticación. Por favor, verifica tu Client ID e intenta nuevamente.'
            )
            
            logger.error(
                f"Error obteniendo device code: {error}",
                extra={
                    'error_code': error,
                    'error_description': error_description,
                    'client_id_prefix': client_id[:8]
                }
            )
            
            # En DEBUG, mostrar error técnico; en producción, mensaje amigable
            if settings.DEBUG:
                return JsonResponse({
                    'error': user_message,
                    'error_code': error,
                    'error_description': error_description
                }, status=400)
            else:
                return JsonResponse({'error': user_message}, status=400)
        
        logger.info(f"Device code obtenido exitosamente: {response.get('user_code')}")
        return JsonResponse(response)
        
    except Exception as e:
        logger.error(f"Error inesperado en initiate_auth: {str(e)}", exc_info=True)
        
        # En DEBUG, mostrar error técnico; en producción, mensaje genérico
        if settings.DEBUG:
            return JsonResponse({'error': f'Error del servidor: {str(e)}'}, status=500)
        else:
            return JsonResponse({
                'error': 'Error del servidor. Por favor, intenta nuevamente más tarde.'
            }, status=500)


@require_http_methods(["POST"])
def check_auth_status(request):
    """API endpoint para verificar el estado de autenticación (polling)."""
    try:
        # Parsear JSON del request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning("Request body no es JSON válido")
            return JsonResponse({'error': 'Datos inválidos'}, status=400)
        
        # Extraer y validar parámetros
        client_id = data.get('client_id', '').strip()
        device_code = data.get('device_code', '').strip()
        
        if not client_id or not device_code:
            logger.warning("Parámetros faltantes en check_auth_status")
            return JsonResponse({'error': 'Parámetros faltantes'}, status=400)
        
        # Validar formato de Client ID y Device Code
        try:
            from apps.todo_panel.validators import validate_client_id, validate_device_code
            validate_client_id(client_id)
            validate_device_code(device_code)
        except ValidationError as e:
            logger.warning(f"Validación fallida en check_auth_status: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
        
        logger.debug(f"Verificando estado de autenticación para client_id: {client_id[:8]}...")
        
        # Hacer UN intento de polling (no bloqueante)
        response = poll_for_token(client_id, device_code)
        
        # Caso 1: Autorización pendiente
        if 'error' in response:
            error = response['error']
            error_description = response.get('error_description', error)
            
            if error == 'authorization_pending':
                logger.debug("Autorización aún pendiente")
                return JsonResponse({'status': 'pending'})
            
            # Caso 2: Errores específicos con mensajes amigables
            user_friendly_errors = {
                'authorization_declined': 'Has rechazado la autorización. Por favor, inicia el proceso nuevamente.',
                'expired_token': 'El código de autenticación ha expirado. Por favor, inicia el proceso nuevamente.',
                'invalid_grant': 'El código de autenticación ya fue usado o es inválido. Por favor, inicia el proceso nuevamente.',
                'bad_verification_code': 'Código de verificación inválido. Por favor, inicia el proceso nuevamente.',
            }
            
            user_message = user_friendly_errors.get(
                error,
                'Error durante la autenticación. Por favor, inicia el proceso nuevamente.'
            )
            
            logger.warning(
                f"Error en autenticación: {error}",
                extra={
                    'error_code': error,
                    'error_description': error_description,
                    'client_id_prefix': client_id[:8]
                }
            )
            
            # En DEBUG, mostrar error técnico; en producción, mensaje amigable
            if settings.DEBUG:
                return JsonResponse({
                    'error': user_message,
                    'error_code': error,
                    'error_description': error_description
                }, status=400)
            else:
                return JsonResponse({'error': user_message}, status=400)
        
        # Caso 3: ¡Éxito! Usuario completó autenticación
        logger.info("Autenticación exitosa, creando/actualizando usuario")
        
        # Extraer tokens de la respuesta
        access_token = response.get('access_token')
        refresh_token = response.get('refresh_token')
        
        if not access_token:
            logger.error("Respuesta exitosa pero sin access_token")
            return JsonResponse({
                'error': 'Error del servidor. Por favor, intenta nuevamente.'
            }, status=500)
        
        # Hashear client_id para identificación (SHA-256)
        client_id_hash = hashlib.sha256(client_id.encode()).hexdigest()
        logger.debug(f"Client ID hash: {client_id_hash[:16]}...")
        
        # Buscar o crear usuario en base de datos
        user, created = MicrosoftUser.objects.get_or_create(
            client_id_hash=client_id_hash,
            defaults={
                'encrypted_client_id': encrypt_data(client_id),
                'encrypted_access_token': encrypt_data(access_token),
                'encrypted_refresh_token': encrypt_data(refresh_token) if refresh_token else b""
            }
        )
        
        # Si el usuario ya existía, actualizar tokens
        if not created:
            logger.info(f"Usuario existente encontrado (ID: {user.id}), actualizando tokens")
            user.encrypted_access_token = encrypt_data(access_token)
            if refresh_token:
                user.encrypted_refresh_token = encrypt_data(refresh_token)
            user.save()
        else:
            logger.info(f"Nuevo usuario creado (ID: {user.id})")
        
        # Crear sesión de usuario
        request.session['user_id'] = user.id
        logger.info(f"Sesión creada para usuario {user.id}")
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error inesperado en check_auth_status: {str(e)}", exc_info=True)
        
        # En DEBUG, mostrar error técnico; en producción, mensaje genérico
        if settings.DEBUG:
            return JsonResponse({'error': f'Error del servidor: {str(e)}'}, status=500)
        else:
            return JsonResponse({
                'error': 'Error del servidor. Por favor, intenta nuevamente más tarde.'
            }, status=500)


def logout_view(request):
    """Vista para cerrar sesión del usuario."""
    user_id = request.session.get('user_id')
    request.session.flush()
    
    if user_id:
        logger.info(f"Usuario {user_id} cerró sesión")
    else:
        logger.debug("Logout llamado sin sesión activa")
    
    return redirect('todo_panel:login')


@login_required
def index(request):
    """Vista principal del panel de tareas."""
    user_id = request.session['user_id']
    logger.info(f"Usuario {user_id} accediendo al panel de tareas")
    
    try:
        user = MicrosoftUser.objects.get(id=user_id)
        logger.debug(f"Usuario {user_id} encontrado en DB")
        
        client = MicrosoftClient(user)
        lists_data = client.get_tasks()
        # logger.info(f"Obtenidas {lists_data}")
        
        if lists_data:
            lists = lists_data
            logger.info(f"Obtenidas {len(lists)} listas para usuario {user_id}")
        else:
            lists = []
            logger.warning(f"No se pudieron obtener listas para usuario {user_id}")
        
        context = {'lists': lists}
        # logger.debug(f"Contenido de 'lists': {lists}")
        # logger.debug(f"Contenido de 'context': {context}")
        return render(request, 'todo_panel/index.html', context)
        
    except ObjectDoesNotExist:
        logger.error(f"Usuario {user_id} no encontrado en DB (sesión huérfana)")
        request.session.flush()
        return redirect('todo_panel:login')
    
    except Exception as e:
        logger.error(f"Error inesperado en index: {str(e)}", exc_info=True)
        context = {'lists': [], 'error': 'Error al cargar las tareas'}
        return render(request, 'todo_panel/index.html', context)

@login_required
def tarea(request, id_list):
    """Vista principal de tareas. Si no están en caché, muestra pantalla de carga."""
    user_id = request.session['user_id']
    try:
        user = MicrosoftUser.objects.get(id=user_id)
        
        # Verificar caché comprimido primero (ahorro ~60-70% memoria)
        cache_key = f"tasks_{user_id}_{id_list}"
        tareas_raw = CacheOptimizer.get_compressed(cache_key)
        
        # Si no hay datos en caché, mostrar pantalla de carga
        if tareas_raw is None:
            logger.info(f"Cache miss para lista {id_list}, mostrando loading...")
            return render(request, 'todo_panel/loading.html', {'list_id': id_list})
            
        # -- SMART SYNC INCREMENTAL (No Bloqueante) --
        # Verificamos si deberíamos intentar sincronizar, pero NO lo hacemos aquí para no freezar.
        # Pasamos un flag al template para que el JS lo haga via AJAX.
        smart_sync_key = f"smart_sync_cd:{user_id}:{id_list}"
        needs_bg_sync = cache.get(smart_sync_key) is None
        # --------------------------------------------

        client = MicrosoftClient(user)
        
        processed_tasks = {}
        # Obtener nombre de la lista (intenta caché)
        list_name = client.get_tasks_list_name(id_list) or "Mis Tareas"

        for tarea in tareas_raw:
            fecha_limite = None
            if tarea.get('dueDateTime'):
                dt_str = tarea.get('dueDateTime').get('dateTime')
                if dt_str:
                    fecha_limite = pd.to_datetime(dt_str).tz_localize('UTC').tz_convert('America/Argentina/Buenos_Aires').strftime('%Y-%m-%d %H:%M:%S')

            fecha_recordatorio = None
            if tarea.get('reminderDateTime'):
                dt_str = tarea.get('reminderDateTime').get('dateTime')
                if dt_str:
                    fecha_recordatorio = pd.to_datetime(dt_str).tz_localize('UTC').tz_convert('America/Argentina/Buenos_Aires').strftime('%Y-%m-%d %H:%M:%S')

            # Procesar adjuntos (Metadatos solamente)
            attachments_list = []
            if tarea.get('hasAttachments') and tarea.get('attachments'):
                for attachment in tarea['attachments']:
                    # No descargamos el contenido aquí (Lazy Loading)
                    # Generamos la clave de caché que se usaría
                    attachment_key = f"microsoft_attachment:{id_list}:{tarea['id']}:{attachment['id']}"
                    
                    attachment_info = {
                        'cache_key': attachment_key,
                        'name': attachment.get('name', 'archivo'),
                        'content_type': attachment.get('contentType', 'application/octet-stream'),
                        'size': attachment.get('size', 0)
                    }
                    attachments_list.append(attachment_info)
            
            estructura_tarea = {
                'id': tarea.get('id'),
                'nombre_lista': list_name,
                'titulo': tarea.get('title'),
                'importancia': tarea.get('importance'),
                'status': tarea.get('status'),
                'isReminderOn': tarea.get('isReminderOn'),
                'createdDateTime': tarea.get('createdDateTime'),
                'subtareas': [{'displayName': item.get('displayName'), 'isChecked': item.get('isChecked')} for item in tarea.get('checklistItems', [])],
                'fecha_limite': fecha_limite,
                'fecha_recordatorio': fecha_recordatorio,
                'attachments': attachments_list,
                'hasAttachments': tarea.get('hasAttachments'),
                'descripcion': tarea.get('body', {}).get('content', '')
            }
            processed_tasks[tarea['id']] = estructura_tarea

        def sort_tasks_key(task):
            is_important = 1 if task.get('importancia') == 'high' else 0
            has_due_date = 1 if task.get('fecha_limite') else 0
            has_attachments = 1 if task.get('hasAttachments') else 0
            has_subtasks = 1 if task.get('subtareas') else 0
            title = task.get('titulo', '')
            return (-is_important, -has_due_date, -has_attachments, -has_subtasks, title)

        sorted_tasks = sorted(processed_tasks.values(), key=sort_tasks_key)

        context = {
            'tareas': sorted_tasks,
            'list_name': list_name,
            'list_id': id_list, # Útil para refrescar
            'needs_bg_sync': str(needs_bg_sync).lower(),  # Pasar a JS
        }
        return render(request, 'todo_panel/tarea.html', context)
    except Exception as e:
        logger.error(f"Error inesperado en tarea: {str(e)}", exc_info=True) 
        context = {'tareas': [], 'error': 'Error al obtener las tareas', 'list_id': id_list}
        return render(request, 'todo_panel/tarea.html', context)


@login_required
def incremental_sync(request, id_list):
    """Endpoint para sincronización incremental (Delta Sync). Retorna si hubo cambios."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
        
    user_id = request.session['user_id']
    try:
        # Rate limiting (compartido con start_sync o específico)
        smart_sync_key = f"smart_sync_cd:{user_id}:{id_list}"
        if cache.get(smart_sync_key):
             return JsonResponse({'status': 'skipped', 'message': 'Cooldown active'})

        user = MicrosoftUser.objects.get(id=user_id)
        service = TaskService(user)
        
        has_updates = service.sync_tasks_incremental(id_list)
        
        # Activar cooldown de 15s
        cache.set(smart_sync_key, 1, timeout=15)
        
        return JsonResponse({'status': 'success', 'updated': has_updates})
    except Exception as e:
        logger.error(f"Error incremental sync: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def serve_attachment(request, cache_key):
    """Sirve un archivo adjunto desde Redis, descargándolo si es necesario."""
    try:
        user_id = request.session['user_id']
        
        # 1. Intentar obtener de Redis
        file_content = cache.get(cache_key)
        
        # 2. Si no está en caché, intentar descargarlo (Lazy Loading)
        if not file_content:
            logger.info(f"Miss de caché para adjunto {cache_key}, intentando descargar...")
            parts = cache_key.split(':')
            # Formato esperado: microsoft_attachment:list_id:task_id:attachment_id
            if len(parts) >= 4 and parts[0] == 'microsoft_attachment':
                try:
                    list_id, task_id, attachment_id = parts[1], parts[2], parts[3]
                    user = MicrosoftUser.objects.get(id=user_id)
                    client = MicrosoftClient(user)
                    
                    # save_attachment descarga, cachea y retorna la clave
                    # Nota: save_attachment internally actually calls get_attachment and sets cache
                    # We can use it directly.
                    client.save_attachment(list_id, task_id, attachment_id)
                    file_content = cache.get(cache_key)
                except Exception as e:
                    logger.error(f"Error recuperando adjunto {cache_key}: {e}")
            
        if not file_content:
            logger.warning(f"Archivo no encontrado en caché ni se pudo descargar: {cache_key}")
            return HttpResponse('Archivo no encontrado o expirado', status=404)
        
        # Intentar determinar el content type desde el cache_key
        # El cache_key tiene formato: microsoft_attachment:list_id:task_id:attachment_id
        # Necesitamos obtener el content type de alguna manera
        # Por ahora, intentaremos detectarlo del contenido o usar un genérico
        
        # Detectar tipo de contenido básico
        content_type = 'application/octet-stream'
        
        # Intentar detectar por los primeros bytes
        if file_content.startswith(b'\\xff\\xd8\\xff'):
            content_type = 'image/jpeg'
        elif file_content.startswith(b'\\x89PNG'):
            content_type = 'image/png'
        elif file_content.startswith(b'GIF8'):
            content_type = 'image/gif'
        elif file_content.startswith(b'%PDF'):
            content_type = 'application/pdf'
        elif file_content.startswith(b'PK\\x03\\x04'):
            content_type = 'application/zip'
        else:
            # Intentar decodificar como texto
            try:
                file_content.decode('utf-8')
                content_type = 'text/plain; charset=utf-8'
            except UnicodeDecodeError:
                pass
        
        response = HttpResponse(file_content, content_type=content_type)
        
        # Refrescar el tiempo de expiración en caché (otros 5 minutos)
        cache.set(cache_key, file_content, timeout=300)
        
        return response
        
    except Exception as e:
        logger.error(f"Error sirviendo adjunto {cache_key}: {str(e)}", exc_info=True)
        return HttpResponse('Error al cargar el archivo', status=500)


@login_required
def redis_test(request):
    """Prueba la conexión a Redis y retorna resultados en JSON."""
    
    # En producción solo administradores deberían poder ver esto, 
    # pero para el prototipo lo dejamos con login_required y verificación de DEBUG
    if not settings.DEBUG:
        # En producción podríamos requerir ser superusuario
        if not request.user.is_superuser:
            return JsonResponse({'error': 'Test not allowed in production without admin privileges'}, status=403)

    results = {
        'status': 'unknown',
        'checks': {}
    }

    try:
        # Test 1: Configuración
        try:
            redis_url = settings.CACHES['default']['LOCATION']
            results['checks']['config'] = {'status': 'ok', 'url': '***' } # Ocultamos la URL por seguridad
        except Exception as e:
            results['checks']['config'] = {'status': 'error', 'message': str(e)}

        # Test 2: Escritura (Set)
        try:
            cache.set('test_key', 'test_value', timeout=10)
            results['checks']['write'] = {'status': 'ok'}
        except Exception as e:
            results['checks']['write'] = {'status': 'error', 'message': str(e)}
            
        # Test 3: Lectura (Get)
        try:
            value = cache.get('test_key')
            if value == 'test_value':
                results['checks']['read'] = {'status': 'ok', 'value': value}
            else:
                results['checks']['read'] = {'status': 'error', 'expected': 'test_value', 'got': value}
        except Exception as e:
            results['checks']['read'] = {'status': 'error', 'message': str(e)}

        # Test 4: Eliminación (Delete)
        try:
            cache.delete('test_key')
            value = cache.get('test_key')
            if value is None:
                results['checks']['delete'] = {'status': 'ok'}
            else:
                results['checks']['delete'] = {'status': 'error', 'details': 'Key still exists'}
        except Exception as e:
            results['checks']['delete'] = {'status': 'error', 'message': str(e)}

        # Determinación final del estado
        if all(check['status'] == 'ok' for check in results['checks'].values()):
            results['status'] = 'success'
            results['message'] = 'Redis is fully functional'
        else:
            results['status'] = 'partial_failure'
            results['message'] = 'Some Redis tests failed'

    except Exception as e:
        results['status'] = 'critical_failure'
        results['error'] = str(e)

    return JsonResponse(results)


@login_required
def export_tasks(request, id_list):
    """
    Exporta las tareas de una lista en formato JSON o Markdown dentro de un ZIP.
    Incluye controles de seguridad: rate limiting, validación de tamaño, auditoría.
    
    Parámetros GET:
    - format: 'json' (default) o 'markdown'
    """
    from .services.export_service import ExportService, ExportLimitExceeded
    
    user_id = request.session['user_id']
    export_format = request.GET.get('format', 'json').lower()
    
    # Validar formato
    if export_format not in ['json', 'markdown']:
        return HttpResponse('Formato inválido. Use "json" o "markdown"', status=400)
    
    try:
        user = MicrosoftUser.objects.get(id=user_id)
        client = MicrosoftClient(user)
        
        # Obtener nombre de lista
        list_name = client.get_tasks_list_name(id_list)
        if not list_name:
            logger.warning(f"Lista {id_list} no encontrada para usuario {user_id}")
            return HttpResponse('Lista no encontrada', status=404)
        
        # Usar servicio de exportación con controles de seguridad
        export_service = ExportService(user_id, client)
        zip_content, zip_filename = export_service.create_export(
            id_list, list_name, export_format
        )
        
        # Retornar respuesta
        response = HttpResponse(zip_content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        return response
        
    except ExportLimitExceeded as e:
        logger.warning(f"Rate limit excedido para usuario {user_id}: {str(e)}")
        return HttpResponse(str(e), status=429)  # Too Many Requests
        
    except ValueError as e:
        logger.warning(f"Error de validación en exportación: {str(e)}")
        return HttpResponse(str(e), status=400)
        
    except ObjectDoesNotExist:
        logger.error(f"Usuario {user_id} no encontrado")
        return HttpResponse('Usuario no encontrado', status=404)
        
    except Exception as e:
        logger.error(f"Error exportando tareas: {str(e)}", exc_info=True)
@login_required
def start_sync_tasks(request, id_list):
    """Inicia la sincronización de tareas en background con rate limiting."""
    user_id = request.session['user_id']
    
    # Rate limiting desde settings
    if not RateLimiter.check_rate_limit(
        user_id, 
        'sync_tasks', 
        limit=settings.RATE_LIMIT_SYNC_TASKS, 
        window=settings.RATE_LIMIT_WINDOW
    ):
        remaining = RateLimiter.get_remaining(user_id, 'sync_tasks', limit=settings.RATE_LIMIT_SYNC_TASKS)
        logger.warning(f"Rate limit exceeded for user {user_id} on sync_tasks")
        return JsonResponse({
            'status': 'error', 
            'message': 'Demasiadas solicitudes. Por favor, espera un momento.',
            'remaining': remaining
        }, status=429)
    
    try:
        user = MicrosoftUser.objects.get(id=user_id)
        service = TaskService(user)
        service.sync_tasks_background(id_list)
        return JsonResponse({'status': 'started'})
    except Exception as e:
        logger.error(f"Error starting sync for user {user_id}: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_sync_progress(request, id_list):
    """Obtiene el progreso de la sincronización."""
    user_id = request.session['user_id']
    try:
        user = MicrosoftUser.objects.get(id=user_id)
        service = TaskService(user)
        progress = service.get_sync_progress(id_list)
        return JsonResponse(progress if progress else {'status': 'unknown'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
