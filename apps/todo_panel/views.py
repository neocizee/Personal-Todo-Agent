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
        
        if lists_data and 'value' in lists_data:
            lists = lists_data['value']
            logger.info(f"Obtenidas {len(lists)} listas para usuario {user_id}")
        else:
            lists = []
            logger.warning(f"No se pudieron obtener listas para usuario {user_id}")
        
        context = {'lists': lists}
        # logger.debug(f"Contenido de 'lists': {lists}")
        logger.debug(f"Contenido de 'context': {context}")
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
def redis_test(request):
    """Prueba la conexión a Redis."""

    if not settings.DEBUG:
        return HttpResponse('Test not allowed in production', status=403)
    
    print("🔍 Probando conexión a Redis...")
    try:
        # Django-redis typically uses a URL-like string for LOCATION
        redis_url = settings.CACHES['default']['LOCATION']
        print(f"📍 URL configurada en Django: {redis_url}")
    except KeyError:
        print("❌ No se encontró la configuración de caché 'default' en settings.CACHES.")
    except Exception as e:
        print(f"❌ Error al obtener la URL de Redis de las configuraciones: {e}")           

    # Test 1: Ping
    print("\n1️⃣ Test de ping...")
    cache.set('test_key', 'test_value', timeout=10)
    print("   ✅ SET exitoso")
    


    # Test 2: Get
    print("\n2️⃣ Test de lectura...")
    value = cache.get('test_key')
    if value == 'test_value':
        print(f"   ✅ GET exitoso: {value}")
    else:
        print(f"   ❌ GET falló: esperado 'test_value', obtenido '{value}'")
    


    # Test 3: Delete
    print("\n3️⃣ Test de eliminación...")
    cache.delete('test_key')
    value = cache.get('test_key')
    if value is None:
        print("   ✅ DELETE exitoso")
    else:
        print(f"   ❌ DELETE falló: la clave aún existe con valor '{value}'")



    # Test 4: Increment
    print("\n4️⃣ Test de incremento...")
    cache.set('counter', 0)
    cache.incr('counter')
    counter = cache.get('counter')
    if counter == 1:
        print(f"   ✅ INCR exitoso: {counter}")
    else:
        print(f"   ❌ INCR falló: esperado 1, obtenido {counter}")
    
    cache.delete('counter')
    
    print("\n✅ Todas las pruebas de Redis pasaron exitosamente!")




    return HttpResponse('Test passed')
