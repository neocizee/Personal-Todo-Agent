"""
Módulo de Encriptación de Datos Sensibles
==========================================

Este módulo proporciona funciones para encriptar y desencriptar datos sensibles
utilizando el algoritmo Fernet (AES-128 en modo CBC con HMAC para autenticación).

Uso Principal:
--------------
- Encriptación de tokens de acceso de Microsoft Graph API
- Encriptación de tokens de refresco (refresh tokens)
- Encriptación de Client IDs de usuarios

Seguridad:
----------
- Utiliza Fernet de la librería cryptography (estándar de la industria)
- La clave se deriva de DJANGO_SECRET_KEY
- IMPORTANTE: Cambiar SECRET_KEY invalida todos los datos encriptados
- Los datos encriptados incluyen timestamp y HMAC para prevenir manipulación

Limitaciones Actuales:
----------------------
⚠️ WARNING: La derivación de clave actual usa padding simple, lo cual no es
   óptimo para producción. Se recomienda usar PBKDF2 o similar.

Ejemplo de Uso:
---------------
>>> from apps.todo_panel.services.encryption import encrypt_data, decrypt_data
>>> 
>>> # Encriptar un token
>>> token = "eyJ0eXAiOiJKV1QiLCJhbGc..."
>>> encrypted = encrypt_data(token)
>>> print(type(encrypted))  # <class 'bytes'>
>>> 
>>> # Desencriptar
>>> decrypted = decrypt_data(encrypted)
>>> assert decrypted == token

Autor: Personal Todo Agent Team
Última modificación: 2025-11-28
"""

from cryptography.fernet import Fernet
from django.conf import settings
import base64
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


def get_cipher() -> Fernet:
    """
    Crea y retorna una instancia de Fernet usando la SECRET_KEY de Django.
    
    Proceso de Derivación de Clave (MEJORADO CON PBKDF2):
    -----------------------------------------------------
    1. Obtiene DJANGO_SECRET_KEY desde settings
    2. Usa PBKDF2-HMAC-SHA256 para derivar clave de 32 bytes
    3. Aplica 100,000 iteraciones (estándar OWASP)
    4. Usa salt estático derivado de SECRET_KEY
    5. Codifica en base64 URL-safe
    6. Crea instancia de Fernet
    
    Returns:
        Fernet: Instancia configurada para encriptación/desencriptación
    
    Raises:
        ValueError: Si SECRET_KEY no está configurada
    
    Notas Técnicas:
    ---------------
    - Fernet usa AES-128 en modo CBC con padding PKCS7
    - Incluye HMAC-SHA256 para autenticación del mensaje
    - El ciphertext incluye: versión | timestamp | IV | ciphertext | HMAC
    - Los tokens Fernet expiran después de cierto tiempo (configurable)
    
    ✅ MEJORA DE SEGURIDAD (2025-11-28):
    ------------------------------------
    Implementación de PBKDF2 (Password-Based Key Derivation Function 2):
    
    - Algoritmo: PBKDF2-HMAC-SHA256
    - Iteraciones: 100,000 (recomendación OWASP 2023)
    - Salt: Derivado de SECRET_KEY (determinístico)
    - Longitud: 32 bytes (256 bits)
    
    Ventajas sobre padding simple:
    1. Resistente a ataques de fuerza bruta
    2. Estándar de la industria (NIST SP 800-132)
    3. Derivación criptográficamente segura
    4. Compatible con rotación de SECRET_KEY
    
    IMPORTANTE: Cambiar SECRET_KEY invalida todos los datos encriptados.
    Para migración de SECRET_KEY, se requiere re-encriptación de datos.
    
    Referencias:
    ------------
    - OWASP Password Storage Cheat Sheet
    - NIST SP 800-132: Recommendation for Password-Based Key Derivation
    - RFC 8018: PKCS #5: Password-Based Cryptography Specification
    """
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    
    # Obtener la SECRET_KEY de Django
    secret_key = settings.SECRET_KEY.encode('utf-8')
    
    # Derivar un salt determinístico de la SECRET_KEY
    # Esto permite que la misma SECRET_KEY siempre genere la misma clave de encriptación
    # El salt no necesita ser secreto, solo único y consistente
    import hashlib
    salt = hashlib.sha256(secret_key + b'encryption_salt').digest()[:16]
    
    # Configurar PBKDF2 con parámetros seguros
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),      # Algoritmo de hash: SHA-256
        length=32,                       # Longitud de clave: 32 bytes (256 bits)
        salt=salt,                       # Salt derivado de SECRET_KEY
        iterations=100000,               # 100,000 iteraciones (OWASP 2023)
        backend=default_backend()
    )
    
    # Derivar clave de 32 bytes desde SECRET_KEY
    derived_key = kdf.derive(secret_key)
    
    # Codificar en base64 URL-safe (formato requerido por Fernet)
    key = base64.urlsafe_b64encode(derived_key)
    
    logger.debug("Clave de encriptación derivada exitosamente usando PBKDF2")
    
    # Crear y retornar la instancia de Fernet
    return Fernet(key)


def encrypt_data(data: str) -> bytes:
    """
    Encripta un string y retorna bytes encriptados.
    
    Args:
        data (str): String a encriptar (ej: access token, client ID)
    
    Returns:
        bytes: Datos encriptados en formato Fernet
               Retorna b"" si data está vacío
    
    Proceso:
    --------
    1. Valida que data no esté vacío
    2. Obtiene instancia de Fernet
    3. Convierte string a bytes (UTF-8)
    4. Encripta usando Fernet
    5. Retorna ciphertext
    
    Ejemplo:
    --------
    >>> token = "mi_token_secreto_123"
    >>> encrypted = encrypt_data(token)
    >>> print(len(encrypted))  # Aprox. 100-150 bytes
    >>> print(encrypted[:10])  # b'gAAAAABm...'
    
    Notas:
    ------
    - El resultado siempre será más largo que el input (overhead de Fernet)
    - El resultado es diferente cada vez (IV aleatorio)
    - Es seguro almacenar en BinaryField de Django
    """
    # Validar input vacío
    if not data:
        logger.debug("encrypt_data: Recibido data vacío, retornando bytes vacíos")
        return b""
    
    # Obtener cipher y encriptar
    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(data.encode('utf-8'))
    
    logger.debug(f"encrypt_data: Encriptados {len(data)} caracteres -> {len(encrypted_bytes)} bytes")
    return encrypted_bytes


def decrypt_data(data: bytes) -> str:
    """
    Desencripta bytes y retorna un string.
    
    Args:
        data (bytes): Datos encriptados a desencriptar
                      También acepta memoryview (común en Django BinaryField)
    
    Returns:
        str: String desencriptado
             Retorna "" si data está vacío
    
    Raises:
        cryptography.fernet.InvalidToken: Si los datos están corruptos o la clave es incorrecta
        Exception: Otros errores de desencriptación (se re-lanza para debugging)
    
    Proceso:
    --------
    1. Valida que data no esté vacío
    2. Convierte memoryview a bytes si es necesario (Django BinaryField)
    3. Obtiene instancia de Fernet
    4. Desencripta
    5. Decodifica bytes a string UTF-8
    
    Ejemplo:
    --------
    >>> encrypted = b'gAAAAABm...'
    >>> decrypted = decrypt_data(encrypted)
    >>> print(decrypted)  # "mi_token_secreto_123"
    
    Manejo de Errores:
    ------------------
    - InvalidToken: Datos corruptos o clave incorrecta
    - UnicodeDecodeError: Datos no son UTF-8 válido
    
    Casos Especiales:
    -----------------
    - memoryview: Django BinaryField a veces retorna memoryview en lugar de bytes
    - bytes vacíos: Retorna string vacío sin error
    - None: Retorna string vacío
    """
    # Validar input vacío
    if not data:
        logger.debug("decrypt_data: Recibido data vacío, retornando string vacío")
        return ""
    
    try:
        cipher = get_cipher()
        
        # Django BinaryField puede retornar memoryview en lugar de bytes
        # Convertir a bytes si es necesario
        if isinstance(data, memoryview):
            logger.debug("decrypt_data: Convirtiendo memoryview a bytes")
            data = data.tobytes()
        
        # Caso raro: Si recibimos un string, algo está mal
        # (BinaryField no debería retornar string)
        if isinstance(data, str):
            logger.warning("decrypt_data: Recibido string en lugar de bytes, esto es inusual")
            # No hacemos nada aquí, Fernet.decrypt fallará y se capturará abajo
        
        # Desencriptar y decodificar a string
        decrypted_bytes = cipher.decrypt(data)
        decrypted_str = decrypted_bytes.decode('utf-8')
        
        logger.debug(f"decrypt_data: Desencriptados {len(data)} bytes -> {len(decrypted_str)} caracteres")
        return decrypted_str
        
    except Exception as e:
        # Logging del error para debugging
        logger.error(
            f"Error desencriptando datos: {type(e).__name__}: {str(e)}",
            exc_info=True,  # Incluye stack trace
            extra={
                'data_type': type(data).__name__,
                'data_length': len(data) if data else 0,
            }
        )
        
        # Re-lanzar la excepción para que el llamador pueda manejarla
        # En desarrollo esto ayuda al debugging
        # En producción, el llamador debería manejar esto apropiadamente
        raise e
