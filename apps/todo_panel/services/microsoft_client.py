"""
Cliente HTTP para Microsoft Graph API
======================================

Este módulo implementa un cliente HTTP para interactuar con Microsoft Graph API,
específicamente con el servicio de Microsoft To Do.

Características Principales:
-----------------------------
- Renovación automática de tokens expirados
- Encriptación/desencriptación transparente de credenciales
- Persistencia automática de tokens renovados
- Manejo de errores HTTP

Patrón de Diseño:
-----------------
Implementa el patrón "Transparent Token Refresh":
1. Cliente intenta hacer request
2. Si recibe 401 (Unauthorized), renueva token automáticamente
3. Reintenta request con nuevo token
4. Actualiza tokens en base de datos

Uso:
----
>>> from apps.todo_panel.models import MicrosoftUser
>>> user = MicrosoftUser.objects.get(id=1)
>>> client = MicrosoftClient(user)
>>> lists = client.get_tasks()

Autor: Personal Todo Agent Team
Última modificación: 2025-11-28
"""

import requests
import logging
from typing import Dict, Optional, Any
from .encryption import encrypt_data, decrypt_data
from .microsoft_auth import refresh_access_token

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


class MicrosoftClient:
    """
    Cliente HTTP para Microsoft Graph API con renovación automática de tokens.
    
    Este cliente maneja automáticamente:
    - Desencriptación de credenciales almacenadas
    - Renovación de access tokens expirados
    - Persistencia de nuevos tokens en base de datos
    - Logging de operaciones
    
    Attributes:
        user (MicrosoftUser): Instancia del modelo de usuario
        base_url (str): URL base de Microsoft Graph API
        client_id (str): Client ID desencriptado
        access_token (str): Access token desencriptado
        refresh_token (str | None): Refresh token desencriptado (opcional)
    
    Ejemplo:
        >>> user = MicrosoftUser.objects.get(id=1)
        >>> client = MicrosoftClient(user)
        >>> 
        >>> # El cliente maneja automáticamente la renovación de tokens
        >>> response = client.request('GET', 'me/todo/lists')
        >>> if response.status_code == 200:
        >>>     lists = response.json()
    """
    
    def __init__(self, user):
        """
        Inicializa el cliente desencriptando las credenciales del usuario.
        
        Args:
            user (MicrosoftUser): Instancia del modelo MicrosoftUser con credenciales encriptadas
        
        Raises:
            cryptography.fernet.InvalidToken: Si las credenciales están corruptas
            Exception: Otros errores de desencriptación
        
        Proceso:
        --------
        1. Guarda referencia al objeto user
        2. Desencripta client_id
        3. Desencripta access_token
        4. Desencripta refresh_token (si existe)
        5. Configura URL base de Microsoft Graph
        
        Notas:
        ------
        - Si la desencriptación falla, el error se propaga al llamador
        - El refresh_token puede ser None si no se solicitó offline_access
        - Todos los tokens se mantienen en memoria durante la vida del objeto
        """
        self.user = user
        self.base_url = "https://graph.microsoft.com/v1.0"
        
        try:
            logger.info(f"Inicializando MicrosoftClient para usuario {user.id}")
            
            # Desencriptar Client ID
            self.client_id = decrypt_data(user.encrypted_client_id)
            logger.debug("Client ID desencriptado exitosamente")
            
            # Desencriptar Access Token
            self.access_token = decrypt_data(user.encrypted_access_token)
            logger.debug("Access Token desencriptado exitosamente")
            
            # Desencriptar Refresh Token (opcional)
            if user.encrypted_refresh_token:
                self.refresh_token = decrypt_data(user.encrypted_refresh_token)
                logger.debug("Refresh Token desencriptado exitosamente")
            else:
                self.refresh_token = None
                logger.warning(
                    "No hay Refresh Token disponible. "
                    "La renovación automática no funcionará si el token expira."
                )
            
            logger.info(f"MicrosoftClient inicializado exitosamente para usuario {user.id}")
                
        except Exception as e:
            logger.error(
                f"Error fatal inicializando MicrosoftClient: {type(e).__name__}: {str(e)}",
                exc_info=True,
                extra={'user_id': user.id}
            )
            raise e

    def _update_tokens(self, new_tokens: Dict[str, Any]) -> None:
        """
        Actualiza los tokens en el objeto usuario y en la instancia actual.
        
        Este método es llamado internamente cuando se renuevan los tokens.
        Actualiza tanto la instancia en memoria como la base de datos.
        
        Args:
            new_tokens (Dict): Diccionario con nuevos tokens de Microsoft
                              Debe contener al menos 'access_token'
                              Puede contener 'refresh_token' (opcional)
        
        Proceso:
        --------
        1. Actualiza access_token en memoria
        2. Encripta y guarda access_token en user.encrypted_access_token
        3. Si hay refresh_token, actualiza en memoria
        4. Si hay refresh_token, encripta y guarda en user.encrypted_refresh_token
        5. Persiste cambios en base de datos (user.save())
        
        Notas:
        ------
        - Microsoft puede o no retornar un nuevo refresh_token
        - Si no retorna refresh_token, se mantiene el anterior
        - Los tokens se encriptan antes de guardarse en DB
        - El método es atómico: si falla save(), se lanza excepción
        
        Ejemplo:
        --------
        >>> new_tokens = {
        >>>     'access_token': 'eyJ0eXAiOiJKV1Qi...',
        >>>     'refresh_token': 'M.R3_BAY.-CW1CCr...',
        >>>     'expires_in': 3600
        >>> }
        >>> client._update_tokens(new_tokens)
        """
        logger.debug("Actualizando tokens en base de datos")
        
        # Actualizar Access Token (siempre presente)
        if 'access_token' in new_tokens:
            self.access_token = new_tokens['access_token']
            self.user.encrypted_access_token = encrypt_data(self.access_token)
            logger.debug("Access token actualizado")
        
        # Actualizar Refresh Token (opcional)
        if 'refresh_token' in new_tokens:
            self.refresh_token = new_tokens['refresh_token']
            self.user.encrypted_refresh_token = encrypt_data(self.refresh_token)
            logger.debug("Refresh token actualizado")
        else:
            logger.debug("No se recibió nuevo refresh token, manteniendo el anterior")
        
        # Persistir en base de datos
        try:
            self.user.save()
            logger.info(f"Tokens actualizados exitosamente en DB para usuario {self.user.id}")
        except Exception as e:
            logger.error(
                f"Error guardando tokens en DB: {str(e)}",
                exc_info=True,
                extra={'user_id': self.user.id}
            )
            raise

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Wrapper para requests que maneja automáticamente la renovación del token.
        
        Este es el método principal para hacer peticiones a Microsoft Graph API.
        Implementa el patrón "Transparent Token Refresh" para manejar tokens expirados.
        
        Args:
            method (str): Método HTTP ('GET', 'POST', 'PATCH', 'DELETE', etc.)
            endpoint (str): Endpoint relativo (ej: 'me/todo/lists')
            **kwargs: Argumentos adicionales para requests.request()
                     - headers: Se fusionan con Authorization header
                     - timeout: Recomendado especificar (default de requests: None)
                     - json: Para enviar JSON en body
                     - data: Para enviar form data
        
        Returns:
            requests.Response: Objeto Response de requests
        
        Proceso:
        --------
        1. Construye URL completa (base_url + endpoint)
        2. Agrega Authorization header con access_token
        3. Realiza petición HTTP
        4. Si recibe 401 (Unauthorized):
           a. Intenta renovar token con refresh_token
           b. Si renueva exitosamente, actualiza tokens en DB
           c. Reintenta petición original con nuevo token
        5. Retorna Response
        
        Casos de Error:
        ---------------
        - 401 sin refresh_token: Retorna 401 (usuario debe re-autenticarse)
        - 401 con refresh_token inválido: Retorna 401 (usuario debe re-autenticarse)
        - Otros códigos HTTP: Se retornan sin modificar
        - Errores de red: Se propagan al llamador
        
        Ejemplo:
        --------
        >>> # GET simple
        >>> response = client.request('GET', 'me/todo/lists')
        >>> 
        >>> # POST con JSON
        >>> response = client.request(
        >>>     'POST',
        >>>     'me/todo/lists',
        >>>     json={'displayName': 'Nueva Lista'},
        >>>     timeout=10
        >>> )
        >>> 
        >>> # PATCH con headers personalizados
        >>> response = client.request(
        >>>     'PATCH',
        >>>     f'me/todo/lists/{list_id}',
        >>>     json={'displayName': 'Nombre Actualizado'},
        >>>     headers={'If-Match': etag},
        >>>     timeout=10
        >>> )
        
        Notas de Seguridad:
        -------------------
        - El access_token nunca se loguea (información sensible)
        - Los tokens renovados se encriptan antes de guardarse
        - Si la renovación falla, el usuario debe re-autenticarse
        
        Notas de Performance:
        ---------------------
        - La renovación de token agrega ~1-2 segundos de latencia
        - Solo ocurre cuando el token expira (~1 hora)
        - El retry es automático y transparente para el llamador
        """
        # Construir URL completa
        url = f"{self.base_url}/{endpoint}"
        
        # Preparar headers con Authorization
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {self.access_token}'
        kwargs['headers'] = headers
        
        logger.debug(f"Realizando {method} request a {endpoint}")

        # Realizar petición inicial
        response = requests.request(method, url, **kwargs)
        
        # Caso 1: Request exitoso (cualquier código que no sea 401)
        if response.status_code != 401:
            logger.debug(f"Request exitoso: {response.status_code}")
            return response

        # Caso 2: Token expirado (401 Unauthorized)
        logger.warning(f"Recibido 401 Unauthorized, token probablemente expirado")
        
        # Verificar si tenemos refresh_token
        if not self.refresh_token:
            logger.error(
                "No hay refresh_token disponible. Usuario debe re-autenticarse.",
                extra={'user_id': self.user.id}
            )
            return response  # Retornar 401 original
        
        # Intentar renovar token
        logger.info("Intentando renovar access token...")
        new_tokens = refresh_access_token(self.client_id, self.refresh_token)
        
        # Caso 2a: Renovación exitosa
        if new_tokens:
            logger.info("Token renovado exitosamente, reintentando request")
            self._update_tokens(new_tokens)
            
            # Reintentar la petición original con el nuevo token
            headers['Authorization'] = f'Bearer {self.access_token}'
            retry_response = requests.request(method, url, **kwargs)
            
            logger.debug(f"Retry exitoso: {retry_response.status_code}")
            return retry_response
        
        # Caso 2b: Renovación fallida
        else:
            logger.error(
                "No se pudo renovar el token. Usuario debe re-autenticarse.",
                extra={'user_id': self.user.id}
            )
            return response  # Retornar 401 original

    def get_tasks(self) -> Optional[Dict]:
        """
        Obtiene las listas de tareas del usuario desde Microsoft To Do.
        
        Este es un método de conveniencia que encapsula una petición GET
        al endpoint de listas de tareas.
        
        Returns:
            Dict | None: Diccionario con las listas de tareas si exitoso
                        {
                            '@odata.context': '...',
                            'value': [
                                {
                                    'id': 'AAMkAD...',
                                    'displayName': 'Tasks',
                                    'isOwner': True,
                                    'isShared': False,
                                    'wellknownListName': 'defaultList'
                                },
                                ...
                            ]
                        }
                        
                        None si hay error
        
        Ejemplo:
        --------
        >>> client = MicrosoftClient(user)
        >>> result = client.get_tasks()
        >>> 
        >>> if result:
        >>>     for task_list in result.get('value', []):
        >>>         print(f"Lista: {task_list['displayName']}")
        >>> else:
        >>>     print("Error obteniendo listas")
        
        Notas:
        ------
        - Endpoint: GET /me/todo/lists
        - Requiere scope: tasks.read o tasks.readwrite
        - La renovación de token es automática si es necesario
        - Retorna None en caso de error (verificar logs para detalles)
        """
        logger.debug("Obteniendo listas de tareas")
        response = self.request('GET', 'me/todo/lists')
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Obtenidas {len(data.get('value', []))} listas de tareas")
            return data
        else:
            logger.error(
                f"Error obteniendo listas: {response.status_code}",
                extra={
                    'status_code': response.status_code,
                    'response_text': response.text[:200]  # Primeros 200 chars
                }
            )
            return None
