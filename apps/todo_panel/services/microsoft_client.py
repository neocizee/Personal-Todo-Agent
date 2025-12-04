import logging
import requests
from ..models import MicrosoftUser
from .encryption import decrypt_data
from .microsoft_auth import refresh_access_token
from django.core.cache import cache

logger = logging.getLogger(__name__)

class MicrosoftClient:
    """
    Cliente para interactuar con Microsoft Graph API.
    
    Maneja la desencriptación de tokens y la renovación automática si expiran.
    """
    
    BASE_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, user: MicrosoftUser):
        self.user = user
        self.access_token = decrypt_data(user.encrypted_access_token)
        self.client_id = decrypt_data(user.encrypted_client_id)
        
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_profile(self):
        """
        Obtiene los datos del perfil del usuario de Microsoft Graph.
        """
        url = f"{self.BASE_URL}/me"
        
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()  # Lanza una excepción para códigos de estado HTTP erróneos
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener el perfil de Microsoft: {e}")
            # Aquí podrías añadir lógica para refrescar el token si el error es 401
            raise


    def get_tasks(self):
        """
        Obtiene las listas de tareas del usuario.
        """
        url = f"{self.BASE_URL}/me/todo/lists"
        
        try:
            # Intentar obtener del caché primero
            cache_key = f"user_tasks_{self.user.id}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"Retornando tareas desde caché para usuario {self.user.id}")
                return cached_data

            response = requests.get(url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 401:
                logger.info("Token expirado, intentando renovar...")
                if self._refresh_token():
                    # Reintentar con nuevo token
                    response = requests.get(url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Guardar en caché por 5 minutos (300 segundos)
                cache.set(cache_key, data, timeout=300)
                return data
            
            logger.error(f"Error obteniendo tareas: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error en get_tasks: {str(e)}", exc_info=True)
            return None

    def _refresh_token(self) -> bool:
        """
        Intenta renovar el access token usando el refresh token.
        Actualiza el usuario en la DB si tiene éxito.
        """
        refresh_token = decrypt_data(self.user.encrypted_refresh_token)
        if not refresh_token:
            return False
            
        new_tokens = refresh_access_token(self.client_id, refresh_token)
        
        if new_tokens and 'access_token' in new_tokens:
            from .encryption import encrypt_data
            
            self.access_token = new_tokens['access_token']
            self.user.encrypted_access_token = encrypt_data(self.access_token)
            
            if 'refresh_token' in new_tokens:
                self.user.encrypted_refresh_token = encrypt_data(new_tokens['refresh_token'])
                
            self.user.save()
            return True
            
        return False
