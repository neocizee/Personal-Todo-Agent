import os
import json
import time
import requests
from typing import Dict, Optional

TOKEN_CACHE_FILE = '.token_cache.json'

def save_token_cache(token_data: Dict):
    """Guarda el token en un archivo de caché."""
    token_data['expires_at'] = time.time() + token_data.get('expires_in', 3600)
    with open(TOKEN_CACHE_FILE, 'w') as f:
        json.dump(token_data, f)

def load_token_cache() -> Optional[Dict]:
    """Carga el token desde el archivo de caché si existe y es válido."""
    if not os.path.exists(TOKEN_CACHE_FILE):
        return None
    
    try:
        with open(TOKEN_CACHE_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def refresh_access_token(client_id: str, refresh_token: str, tenant_id: str = "common") -> Optional[Dict]:
    """Refresca el token de acceso usando el refresh token."""
    if tenant_id == "common":
        tenant_id = "consumers"
        
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "https://graph.microsoft.com/Tasks.Read offline_access"
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()
    return None

def get_access_token_device_code(client_id: str, tenant_id: str = "common") -> str:
    """
    Obtiene un token de acceso usando el flujo de Device Code, con soporte de caché y refresh.

    Args:
        client_id: Application (client) ID de Azure AD
        tenant_id: Tenant ID (por defecto 'common' para cuentas personales)

    Returns:
        Token de acceso
    """
    # 1. Intentar cargar desde caché
    cached_token = load_token_cache()
    if cached_token:
        # Verificar si expiró (con un margen de 5 minutos)
        if time.time() < cached_token.get('expires_at', 0) - 300:
            return cached_token['access_token']
        
        # Si expiró pero tiene refresh token, intentar refrescar
        if 'refresh_token' in cached_token:
            print("El token ha expirado, intentando refrescar...")
            new_token = refresh_access_token(client_id, cached_token['refresh_token'], tenant_id)
            if new_token:
                save_token_cache(new_token)
                print("Token refrescado exitosamente.")
                return new_token['access_token']
            print("No se pudo refrescar el token.")

    # 2. Si no hay caché o falló el refresh, iniciar flujo de Device Code
    # Para cuentas personales de Microsoft, usar 'consumers' en lugar de 'common'
    if tenant_id == "common":
        tenant_id = "consumers"

    # Solicitar código de dispositivo
    device_code_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
    device_code_data = {
        "client_id": client_id,
        "scope": "https://graph.microsoft.com/Tasks.Read offline_access"
    }
    
    response = requests.post(device_code_url, data=device_code_data)
    device_code_response = response.json()
    
    if 'error' in device_code_response:
        raise Exception(f"Error al obtener código de dispositivo: {device_code_response}")
    
    print(f"\n{device_code_response['message']}")
    print(f"Código: {device_code_response['user_code']}")
    print("\nPresiona Enter después de completar la autenticación...")
    input()
    
    # Solicitar token
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": client_id,
        "device_code": device_code_response['device_code']
    }
    
    response = requests.post(token_url, data=token_data)
    token_response = response.json()
    
    if 'error' in token_response:
        raise Exception(f"Error al obtener token: {token_response}")
    
    # Guardar en caché
    save_token_cache(token_response)
    
    return token_response['access_token']
