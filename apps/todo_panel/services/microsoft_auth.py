"""
Módulo de Autenticación con Microsoft Identity Platform
========================================================

Este módulo implementa el flujo OAuth 2.0 Device Code Flow para autenticación
con Microsoft Identity Platform (Azure AD / Entra ID).

Flujo de Autenticación:
-----------------------
1. get_device_code(): Solicita un código de dispositivo
2. Usuario visita URL y ingresa código
3. poll_for_token(): Espera a que el usuario complete la autenticación
4. refresh_access_token(): Renueva tokens expirados

Casos de Uso:
-------------
- Aplicaciones sin navegador (CLI, IoT, etc.)
- Aplicaciones públicas (sin client secret)
- Autenticación en dispositivos con input limitado

Scopes Utilizados:
------------------
- user.read: Leer perfil básico del usuario
- tasks.readwrite: Leer y escribir tareas en Microsoft To Do
- offline_access: Obtener refresh token para renovación automática

Referencias:
------------
- Documentación oficial: https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code
- Microsoft Graph API: https://learn.microsoft.com/en-us/graph/api/overview

Autor: Personal Todo Agent Team
Última modificación: 2025-11-28
"""

import requests
import time
import logging
from typing import Dict, Optional

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

# Constantes de configuración
DEFAULT_TENANT_ID = "consumers"  # Para cuentas personales de Microsoft
DEFAULT_SCOPES = "user.read tasks.readwrite offline_access"
DEFAULT_POLL_INTERVAL = 5  # Segundos entre intentos de polling


def get_device_code(client_id: str, tenant_id: str = DEFAULT_TENANT_ID) -> Dict:
    """
    Inicia el flujo de Device Code solicitando un código de dispositivo.
    
    Este es el primer paso del flujo OAuth 2.0 Device Code. El servidor retorna:
    - device_code: Código interno para polling
    - user_code: Código que el usuario debe ingresar
    - verification_uri: URL donde el usuario debe autenticarse
    - expires_in: Tiempo de expiración del código (típicamente 15 minutos)
    - interval: Intervalo recomendado para polling (típicamente 5 segundos)
    
    Args:
        client_id (str): Application (client) ID de Azure AD
                         Ejemplo: "12345678-1234-1234-1234-123456789012"
        tenant_id (str): Tenant ID de Azure AD
                         - "consumers": Cuentas personales de Microsoft (default)
                         - "organizations": Cuentas de trabajo/escuela
                         - "common": Ambos tipos
                         - GUID específico: Solo ese tenant
    
    Returns:
        Dict: Diccionario con la respuesta del servidor conteniendo:
              {
                  "user_code": "ABC-DEF-GHI",
                  "device_code": "long_opaque_string",
                  "verification_uri": "https://microsoft.com/devicelogin",
                  "expires_in": 900,
                  "interval": 5,
                  "message": "To sign in, use a web browser to open..."
              }
              
              En caso de error, retorna:
              {
                  "error": "invalid_client",
                  "error_description": "Descripción del error"
              }
    
    Raises:
        No lanza excepciones, retorna dict con 'error' en caso de fallo
    
    Ejemplo de Uso:
    ---------------
    >>> response = get_device_code("my-client-id")
    >>> if 'error' not in response:
    >>>     print(f"Visita: {response['verification_uri']}")
    >>>     print(f"Código: {response['user_code']}")
    >>> else:
    >>>     print(f"Error: {response['error_description']}")
    
    Notas Técnicas:
    ---------------
    - El device_code es válido por 15 minutos (típicamente)
    - El user_code es un código corto y fácil de escribir (ej: "ABC-DEF")
    - La URL de verificación es https://microsoft.com/devicelogin
    - El intervalo de polling debe respetarse para evitar rate limiting
    """
    # Construir URL del endpoint de device code
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
    
    # Preparar payload con client_id y scopes solicitados
    payload = {
        'client_id': client_id,
        'scope': DEFAULT_SCOPES
    }
    
    logger.info(f"Solicitando device code para client_id: {client_id[:8]}...")
    
    try:
        # Realizar petición POST al endpoint
        response = requests.post(url, data=payload, timeout=10)
        
        # Parsear respuesta JSON
        data = response.json()
        
        # Verificar si hubo error
        if response.status_code != 200:
            logger.error(
                f"Error obteniendo device code: {data.get('error')}",
                extra={
                    'error_description': data.get('error_description'),
                    'status_code': response.status_code
                }
            )
            return data
        
        # Éxito
        logger.info(
            f"Device code obtenido exitosamente. Expira en {data.get('expires_in')} segundos",
            extra={
                'user_code': data.get('user_code'),
                'verification_uri': data.get('verification_uri')
            }
        )
        return data
        
    except requests.exceptions.Timeout:
        logger.error("Timeout al solicitar device code")
        return {'error': 'timeout', 'error_description': 'Request timed out'}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red al solicitar device code: {str(e)}", exc_info=True)
        return {'error': 'network_error', 'error_description': str(e)}


def poll_for_token(
    client_id: str,
    device_code: str,
    interval: int = DEFAULT_POLL_INTERVAL,
    tenant_id: str = DEFAULT_TENANT_ID
) -> Dict:
    """
    Consulta (polling) el endpoint de token hasta que el usuario complete la autenticación.
    
    Este método implementa el segundo paso del Device Code Flow. Realiza polling
    al servidor hasta que:
    - El usuario complete la autenticación (éxito)
    - El usuario rechace la autenticación (fallo)
    - El código expire (fallo)
    - Ocurra un error de red (fallo)
    
    ⚠️ IMPORTANTE: Este método es BLOQUEANTE y puede tardar varios minutos.
    En una aplicación web, esto debería ejecutarse de forma asíncrona o en background.
    
    Args:
        client_id (str): Application (client) ID de Azure AD
        device_code (str): Device code obtenido de get_device_code()
        interval (int): Segundos entre intentos de polling (default: 5)
                        Debe respetar el valor retornado por get_device_code()
        tenant_id (str): Tenant ID de Azure AD (default: "consumers")
    
    Returns:
        Dict: En caso de éxito, retorna tokens:
              {
                  "token_type": "Bearer",
                  "scope": "user.read tasks.readwrite offline_access",
                  "expires_in": 3600,
                  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                  "refresh_token": "M.R3_BAY.-CW1CCr...",
                  "id_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
              }
              
              En caso de error, retorna:
              {
                  "error": "authorization_declined",
                  "error_description": "User declined authorization"
              }
    
    Posibles Errores:
    -----------------
    - authorization_pending: Usuario aún no ha completado autenticación (continúa polling)
    - authorization_declined: Usuario rechazó la autenticación (detiene polling)
    - expired_token: El device code expiró (detiene polling)
    - invalid_grant: Device code inválido o ya usado (detiene polling)
    
    Ejemplo de Uso:
    ---------------
    >>> device_response = get_device_code("my-client-id")
    >>> print(f"Visita {device_response['verification_uri']}")
    >>> print(f"Código: {device_response['user_code']}")
    >>> 
    >>> # Esto bloqueará hasta que el usuario autentique
    >>> token_response = poll_for_token(
    >>>     "my-client-id",
    >>>     device_response['device_code'],
    >>>     interval=device_response['interval']
    >>> )
    >>> 
    >>> if 'access_token' in token_response:
    >>>     print("¡Autenticación exitosa!")
    >>> else:
    >>>     print(f"Error: {token_response['error']}")
    
    Notas de Implementación:
    ------------------------
    - Este método NO debe usarse directamente en vistas de Django
    - Para aplicaciones web, usar Celery o similar para ejecutar en background
    - Respetar el intervalo de polling para evitar rate limiting (429 Too Many Requests)
    - El access_token expira en ~1 hora, usar refresh_token para renovar
    """
    # Construir URL del endpoint de token
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    # Preparar payload para solicitud de token
    payload = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        'client_id': client_id,
        'device_code': device_code
    }
    
    logger.info(f"Iniciando polling para token (intervalo: {interval}s)")
    poll_count = 0
    
    # Loop de polling (bloqueante)
    while True:
        poll_count += 1
        logger.debug(f"Intento de polling #{poll_count}")
        
        try:
            # Realizar petición POST al endpoint
            response = requests.post(url, data=payload, timeout=10)
            data = response.json()
            
            # Caso 1: Éxito - Usuario completó autenticación
            if response.status_code == 200:
                logger.info(
                    f"Autenticación exitosa después de {poll_count} intentos",
                    extra={'has_refresh_token': 'refresh_token' in data}
                )
                return data
            
            # Caso 2: Error - Analizar tipo de error
            error = data.get('error')
            error_description = data.get('error_description', '')
            
            # Caso 2a: Autorización pendiente - Continuar polling
            if error == 'authorization_pending':
                logger.debug("Autorización pendiente, esperando...")
                time.sleep(interval)
                continue
            
            # Caso 2b: Usuario rechazó - Detener polling
            elif error == 'authorization_declined':
                logger.warning("Usuario rechazó la autorización")
                return {'error': error, 'error_description': 'User declined authorization'}
            
            # Caso 2c: Código expiró - Detener polling
            elif error == 'expired_token':
                logger.warning(f"Device code expiró después de {poll_count} intentos")
                return {'error': error, 'error_description': 'Device code expired'}
            
            # Caso 2d: Otro error - Detener polling
            else:
                logger.error(
                    f"Error inesperado durante polling: {error}",
                    extra={'error_description': error_description}
                )
                return {'error': error, 'error_description': error_description}
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout en intento de polling #{poll_count}, reintentando...")
            time.sleep(interval)
            continue
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red durante polling: {str(e)}", exc_info=True)
            return {'error': 'network_error', 'error_description': str(e)}


def refresh_access_token(
    client_id: str,
    refresh_token: str,
    tenant_id: str = DEFAULT_TENANT_ID
) -> Optional[Dict]:
    """
    Renueva el access token usando el refresh token.
    
    Los access tokens expiran después de ~1 hora. Para evitar que el usuario
    tenga que autenticarse nuevamente, se usa el refresh token para obtener
    un nuevo access token.
    
    Args:
        client_id (str): Application (client) ID de Azure AD
        refresh_token (str): Refresh token obtenido durante autenticación inicial
        tenant_id (str): Tenant ID de Azure AD (default: "consumers")
    
    Returns:
        Dict | None: En caso de éxito, retorna nuevos tokens:
                     {
                         "token_type": "Bearer",
                         "scope": "user.read tasks.readwrite offline_access",
                         "expires_in": 3600,
                         "access_token": "nuevo_access_token...",
                         "refresh_token": "nuevo_refresh_token..."  # Opcional
                     }
                     
                     En caso de error, retorna None
    
    Posibles Errores:
    -----------------
    - invalid_grant: Refresh token inválido, expirado o revocado
    - invalid_client: Client ID inválido
    - unauthorized_client: Cliente no autorizado para este grant type
    
    Ejemplo de Uso:
    ---------------
    >>> new_tokens = refresh_access_token("my-client-id", "old_refresh_token")
    >>> if new_tokens:
    >>>     # Actualizar tokens en base de datos
    >>>     user.access_token = new_tokens['access_token']
    >>>     if 'refresh_token' in new_tokens:
    >>>         user.refresh_token = new_tokens['refresh_token']
    >>>     user.save()
    >>> else:
    >>>     # Refresh token inválido, usuario debe autenticarse nuevamente
    >>>     redirect_to_login()
    
    Notas Importantes:
    ------------------
    - El refresh token puede expirar después de ~90 días de inactividad
    - Algunos refresh tokens son de un solo uso (se invalidan al usarse)
    - Microsoft puede retornar un nuevo refresh_token en la respuesta
    - Siempre actualizar AMBOS tokens si se recibe nuevo refresh_token
    - Si falla, el usuario debe completar el flujo de autenticación nuevamente
    """
    # Construir URL del endpoint de token
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    # Preparar payload para renovación de token
    payload = {
        'client_id': client_id,
        'scope': DEFAULT_SCOPES,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    
    logger.info(f"Intentando renovar access token para client_id: {client_id[:8]}...")
    
    try:
        # Realizar petición POST al endpoint
        response = requests.post(url, data=payload, timeout=10)
        
        # Verificar respuesta
        if response.status_code == 200:
            data = response.json()
            logger.info(
                "Access token renovado exitosamente",
                extra={
                    'expires_in': data.get('expires_in'),
                    'has_new_refresh_token': 'refresh_token' in data
                }
            )
            return data
        else:
            # Error al renovar
            error_data = response.json()
            logger.error(
                f"Error renovando token: {error_data.get('error')}",
                extra={
                    'error_description': error_data.get('error_description'),
                    'status_code': response.status_code
                }
            )
            return None
            
    except requests.exceptions.Timeout:
        logger.error("Timeout al renovar access token")
        return None
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red al renovar token: {str(e)}", exc_info=True)
        return None
