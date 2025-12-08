import logging
import requests
from ..models import MicrosoftUser
from .encryption import decrypt_data
from .microsoft_auth import refresh_access_token
from django.core.cache import cache
from typing import Dict, List, Optional
import base64

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
    
    def _make_request(self, url, timeout=10):
        """Realiza una petición GET con manejo automático de token expirado."""
        response = requests.get(url, headers=self._get_headers(), timeout=timeout)
        
        if response.status_code == 401:
            logger.info("Token expirado, intentando renovar...")
            if self._refresh_token():
                response = requests.get(url, headers=self._get_headers(), timeout=timeout)
        
        if response.status_code == 200:
            return response.json()
        
        logger.error(f"Error en petición: {response.status_code}")
        return None
    
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

    def get_tasks_delta(self, list_id, delta_link=None):
        """
        Obtiene cambios incrementales usando Microsoft Graph Delta Query.
        
        Args:
            list_id: ID de la lista
            delta_link: URL proporcionada por la llamada anterior (si existe)
            
        Returns:
            Tuple (list[changes], next_delta_link)
        """
        # Si tenemos un link delta, lo usamos directamente. Si no, iniciamos delta query.
        url = delta_link if delta_link else f'{self.BASE_URL}/me/todo/lists/{list_id}/tasks/delta'
        
        all_changes = []
        next_link = None
        
        while url:
            # Usar expand para tener detalles completos incluso en el delta si es nueva tarea
            # Sin embargo, delta link ya incluye expands si la query original los tenía?
            # En ToDo API delta funciona un poco diferente, probemos standard.
            # Nota: delta query en To Do a veces no soporta expand completos en todas las implementaciones.
            # Por simplicidad y eficiencia, pedimos el delta standard.
            
            response = self._make_request(url)
            if not response:
                break
                
            tasks = response.get('value', [])
            all_changes.extend(tasks)
            
            # Graph devuelve '@odata.nextLink' si hay más páginas de cambios
            # y '@odata.deltaLink' al final, que es el que necesitamos para la PROXIMA vez
            url = response.get('@odata.nextLink')
            # El deltaLink solo viene en la última página
            if '@odata.deltaLink' in response:
                next_link = response.get('@odata.deltaLink')
            
        return all_changes, next_link

    def fetch_tasks_pages(self, id_list):
        """
        Generador que obtiene las páginas de tareas de una lista.
        Permite procesar el progreso paso a paso.
        """
        url = f"{self.BASE_URL}/me/todo/lists/{id_list}/tasks?$top=100&$expand=checklistItems,linkedResources,attachments"
        while url:
            # logger.debug(f"Fetching URL: {url}")
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 401:
                logger.info("Token expirado, intentando renovar...")
                if self._refresh_token():
                     response = requests.get(url, headers=self._get_headers())

            if response.status_code == 200:
                data = response.json()
                tasks_page = data.get('value', [])
                if not tasks_page:
                    break
                
                yield tasks_page
                
                url = data.get('@odata.nextLink')
            else:
                logger.error(f"Error fetching tasks page: {response.status_code}")
                raise Exception(f"Error al obtener tareas: {response.status_code} - {response.text}")

    def get_tasks_by_list_id(self, id_list, force_refresh=False):
        """
        Obtiene las tareas de una lista específica.
        Ahora usa el generador fetch_tasks_pages.
        """
        cache_key = f"tasks_{self.user.id}_{id_list}"
        
        if not force_refresh:
            cached_tasks = cache.get(cache_key)
            if cached_tasks:
                logger.info(f"Retornando tareas desde caché para lista {id_list}")
                return cached_tasks

        tasks = []
        for page in self.fetch_tasks_pages(id_list):
            tasks.extend(page)
        
        # Guardar en caché
        cache.set(cache_key, tasks, timeout=300)
        return tasks

    def get_tasks(self):
        """
        Obtiene las listas de tareas del usuario.
        """
        # Intentar obtener del caché primero
        cache_key = f"user_tasks_{self.user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"Retornando tareas desde caché para usuario {self.user.id}")
            return cached_data

        lists = []
        url = f"{self.BASE_URL}/me/todo/lists?$top=100"
        
        try:
            while url:
                response = requests.get(url, headers=self._get_headers(), timeout=10)

                if response.status_code == 401:
                    logger.info("Token expirado, intentando renovar...")
                    if self._refresh_token():
                        # Reintentar con nuevo token
                        response = requests.get(url, headers=self._get_headers(), timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    lists.extend(data.get('value', []))
                    url = data.get('@odata.nextLink')  # Si hay más páginas, continuar
                else:
                    logger.error(f"Error obteniendo tareas: {response.status_code} - {response.text}")
                    return None
            
            # Guardar en caché por 5 minutos (300 segundos) si obtuvimos datos
            if lists:
                cache.set(cache_key, lists, timeout=300)
                
            return lists
            
        except Exception as e:
            logger.error(f"Error en get_tasks: {str(e)}", exc_info=True)
            return None

    def get_tasks_by_name(self, list_name:str) ->  Optional[Dict]:
        tareas = self.get_tasks()
        if tareas and 'value' in tareas:
            for tarea in tareas['value']:
                # logger.debug(f"Tarea: {tarea}")
                if tarea['displayName'].lower() == list_name.lower():
                    return tarea
        return None
    
    def get_tasks_list_name(self, list_id:str) ->  Optional[str]:
        tareas = self.get_tasks()
        for tarea in tareas:
            if tarea['id'] == list_id:
                return tarea['displayName']
        return None

    def get_tasks_by_id(self, list_id:str) ->  Optional[Dict]:
        tareas = self.get_tasks()
        if tareas and 'value' in tareas:
            for tarea in tareas['value']:
                if tarea['id'] == list_id:
                    return tarea
        return None
        

    
    def get_attachment(self, list_id: str, task_id: str, attachment_id: str) -> Dict:
        """Obtiene los detalles completos de un adjunto, incluyendo contentBytes"""
        url = f"{self.BASE_URL}/me/todo/lists/{list_id}/tasks/{task_id}/attachments/{attachment_id}"
        response = requests.get(url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Error al obtener adjunto: {response.status_code} - {response.text}")

    def save_attachment(self, list_id: str, task_id: str, attachment_id: str) -> str:
        """
        Descarga un adjunto y lo guarda temporalmente en caché (Redis) por 5 minutos.
        Retorna la clave de caché del adjunto.
        """
        cache_key = f"microsoft_attachment:{list_id}:{task_id}:{attachment_id}"
        
        # Intentar obtener del caché primero para evitar re-descargar
        cached_content = cache.get(cache_key)
        if cached_content:
            # Si ya está en caché, refrescar la expiración y devolver la clave
            cache.set(cache_key, cached_content, timeout=300)  # 5 minutos
            return cache_key
            
        attachment = self.get_attachment(list_id, task_id, attachment_id)
        if attachment.get('@odata.type') != '#microsoft.graph.taskFileAttachment':
            raise Exception("El adjunto no es un archivo (taskFileAttachment)")
        
        content_bytes_b64 = attachment.get('contentBytes')
        if not content_bytes_b64:
            raise Exception("No se encontró contenido en el adjunto")
            
        # Decodificar el contenido antes de guardarlo en caché
        decoded_content = base64.b64decode(content_bytes_b64)
        
        # Guardar el contenido decodificado en caché por 5 minutos (300 segundos)
        cache.set(cache_key, decoded_content, timeout=300)
            
        return cache_key
          
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