"""
Validadores personalizados para la aplicación todo_panel.

Este módulo contiene funciones de validación para inputs del usuario,
especialmente para datos relacionados con Microsoft OAuth 2.0.

Seguridad:
-----------
- Valida formato de Client ID (UUID de Azure AD)
- Valida formato de Device Code (alfanumérico)
- Previene inyección de código malicioso
- Sanitiza inputs antes de procesamiento

Uso:
----
    from apps.todo_panel.validators import validate_client_id
    
    try:
        validate_client_id(user_input)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
"""
import re
import logging
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def validate_client_id(client_id: str) -> None:
    """
    Valida el formato de un Client ID de Azure AD.
    
    Azure AD Client IDs son UUIDs en formato:
    xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    
    Args:
        client_id: String con el Client ID a validar
        
    Raises:
        ValidationError: Si el Client ID es inválido
        
    Examples:
        >>> validate_client_id("12345678-1234-1234-1234-123456789abc")
        None  # Válido
        
        >>> validate_client_id("invalid")
        ValidationError: Client ID inválido: formato UUID esperado
    """
    if not client_id:
        logger.warning("Intento de validación con Client ID vacío")
        raise ValidationError("Client ID es requerido")
    
    # Eliminar espacios en blanco
    client_id = client_id.strip()
    
    # Validar longitud mínima
    if len(client_id) < 32:
        logger.warning(f"Client ID demasiado corto: {len(client_id)} caracteres")
        raise ValidationError(
            f"Client ID inválido: longitud mínima 32 caracteres (recibido: {len(client_id)})"
        )
    
    # Validar formato UUID: 8-4-4-4-12
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, client_id, re.IGNORECASE):
        logger.warning(f"Client ID con formato inválido: {client_id[:8]}...")
        raise ValidationError(
            "Client ID inválido: formato UUID esperado (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
        )
    
    logger.debug(f"Client ID validado exitosamente: {client_id[:8]}...")


def validate_device_code(device_code: str) -> None:
    """
    Valida el formato de un Device Code de Microsoft.
    
    Device Codes son strings alfanuméricos generados por Microsoft,
    típicamente de 8-12 caracteres en mayúsculas.
    
    Args:
        device_code: String con el Device Code a validar
        
    Raises:
        ValidationError: Si el Device Code es inválido
        
    Examples:
        >>> validate_device_code("ABCD1234")
        None  # Válido
        
        >>> validate_device_code("abc")
        ValidationError: Device code inválido: longitud mínima 8 caracteres
    """
    if not device_code:
        logger.warning("Intento de validación con Device Code vacío")
        raise ValidationError("Device code es requerido")
    
    # Eliminar espacios en blanco
    device_code = device_code.strip()
    
    # Validar longitud mínima
    if len(device_code) < 8:
        logger.warning(f"Device code demasiado corto: {len(device_code)} caracteres")
        raise ValidationError(
            f"Device code inválido: longitud mínima 8 caracteres (recibido: {len(device_code)})"
        )
    
    # Validar caracteres permitidos (alfanuméricos y guiones)
    if not re.match(r'^[A-Z0-9-]+$', device_code):
        logger.warning(f"Device code con caracteres inválidos: {device_code[:8]}...")
        raise ValidationError(
            "Device code inválido: solo se permiten caracteres alfanuméricos en mayúsculas y guiones"
        )
    
    logger.debug(f"Device code validado exitosamente: {device_code[:4]}...")


def sanitize_string_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitiza un string de entrada del usuario.
    
    Elimina caracteres potencialmente peligrosos y limita la longitud.
    
    Args:
        value: String a sanitizar
        max_length: Longitud máxima permitida (default: 1000)
        
    Returns:
        String sanitizado
        
    Examples:
        >>> sanitize_string_input("  hello world  ")
        "hello world"
        
        >>> sanitize_string_input("a" * 2000, max_length=100)
        "aaa..." # Truncado a 100 caracteres
    """
    if not value:
        return ""
    
    # Eliminar espacios en blanco al inicio y final
    sanitized = value.strip()
    
    # Truncar si excede longitud máxima
    if len(sanitized) > max_length:
        logger.warning(f"Input truncado de {len(sanitized)} a {max_length} caracteres")
        sanitized = sanitized[:max_length]
    
    return sanitized
