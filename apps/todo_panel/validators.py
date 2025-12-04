from django.core.exceptions import ValidationError
import re

def validate_client_id(client_id: str):
    """
    Valida que el Client ID tenga el formato correcto (UUID).
    """
    if not client_id:
        raise ValidationError("Client ID no puede estar vacío.")
    
    # Regex para UUID (8-4-4-4-12 caracteres hex)
    uuid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    
    if not uuid_pattern.match(client_id):
        raise ValidationError("Client ID debe ser un UUID válido (ej: 12345678-1234-1234-1234-123456789012).")

def validate_device_code(device_code: str):
    """
    Valida que el Device Code no esté vacío y tenga una longitud razonable.
    """
    if not device_code:
        raise ValidationError("Device Code no puede estar vacío.")
    
    if len(device_code) > 1024:
        raise ValidationError("Device Code es demasiado largo.")
