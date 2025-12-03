"""
Modelos de Django para Gestión de Usuarios de Microsoft
========================================================

Este módulo define los modelos de base de datos para almacenar
información de usuarios autenticados con Microsoft Identity Platform.

Estrategia de Seguridad:
------------------------
- Client ID hasheado (SHA-256) para identificación única
- Tokens encriptados con Fernet + PBKDF2
- No se almacenan credenciales en texto plano
- Timestamps automáticos para auditoría

Autor: Personal Todo Agent Team
Última modificación: 2025-11-28
"""

from django.db import models


class MicrosoftUser(models.Model):
    """
    Modelo para almacenar usuarios autenticados con Microsoft.
    
    Este modelo NO hereda de AbstractUser porque no usa el sistema
    de autenticación estándar de Django. En su lugar, usa sesiones
    de Django con user_id personalizado.
    
    Estrategia de Identificación:
    ------------------------------
    - client_id_hash: Hash SHA-256 del Client ID (identificador único)
    - encrypted_client_id: Client ID encriptado (para uso en API calls)
    
    ¿Por qué hashear Y encriptar el Client ID?
    - Hash: Para búsqueda rápida y única (índice de DB)
    - Encriptado: Para desencriptar y usar en llamadas a Microsoft API
    
    Campos Encriptados:
    -------------------
    Todos los campos sensibles se encriptan usando:
    - Algoritmo: Fernet (AES-128-CBC + HMAC-SHA256)
    - KDF: PBKDF2-HMAC-SHA256 con 100,000 iteraciones
    - Almacenamiento: BinaryField (bytes)
    
    Relación con Sesiones:
    ----------------------
    request.session['user_id'] = MicrosoftUser.id
    
    Attributes:
        client_id_hash (str): Hash SHA-256 del Client ID (64 caracteres hex)
        encrypted_client_id (bytes): Client ID encriptado con Fernet
        encrypted_access_token (bytes): Access token encriptado
        encrypted_refresh_token (bytes): Refresh token encriptado (opcional)
        created_at (datetime): Timestamp de creación del registro
        last_login (datetime): Timestamp de última actualización (auto)
    
    Ejemplo de Uso:
    ---------------
    >>> import hashlib
    >>> from apps.todo_panel.services.encryption import encrypt_data
    >>> 
    >>> client_id = "12345678-1234-1234-1234-123456789012"
    >>> client_id_hash = hashlib.sha256(client_id.encode()).hexdigest()
    >>> 
    >>> user = MicrosoftUser.objects.create(
    >>>     client_id_hash=client_id_hash,
    >>>     encrypted_client_id=encrypt_data(client_id),
    >>>     encrypted_access_token=encrypt_data(access_token),
    >>>     encrypted_refresh_token=encrypt_data(refresh_token)
    >>> )
    
    Notas de Seguridad:
    -------------------
    - NUNCA almacenar tokens en texto plano
    - NUNCA loguear tokens completos (solo primeros 8 caracteres)
    - Cambiar DJANGO_SECRET_KEY invalida todos los datos encriptados
    - Para rotación de SECRET_KEY, se requiere migración de datos
    
    Mejoras Futuras:
    ----------------
    - Agregar campo 'token_expires_at' para evitar llamadas innecesarias
    - Agregar campo 'scopes' para almacenar permisos otorgados
    - Agregar relación con django.contrib.auth.models.User (opcional)
    - Implementar soft delete en lugar de hard delete
    """
    
    # Identificador único: Hash SHA-256 del Client ID
    # Permite búsqueda rápida sin exponer el Client ID real
    # Longitud: 64 caracteres hexadecimales
    # Ejemplo: "a1b2c3d4e5f6..."
    client_id_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,  # Índice para búsquedas rápidas
        help_text="SHA-256 hash del Client ID de Azure AD"
    )
    
    # Client ID encriptado con Fernet
    # Necesario para hacer llamadas a Microsoft Graph API
    # Se desencripta en MicrosoftClient.__init__()
    encrypted_client_id = models.BinaryField(
        help_text="Client ID encriptado con Fernet + PBKDF2"
    )
    
    # Access Token encriptado con Fernet
    # Expira en ~1 hora, se renueva automáticamente con refresh_token
    # Se desencripta en MicrosoftClient.__init__()
    encrypted_access_token = models.BinaryField(
        help_text="Access token encriptado, expira en ~1 hora"
    )
    
    # Refresh Token encriptado con Fernet (opcional)
    # Usado para renovar access_token sin re-autenticación
    # Puede expirar después de ~90 días de inactividad
    # null=True porque algunos flujos no retornan refresh_token
    encrypted_refresh_token = models.BinaryField(
        null=True,
        blank=True,
        help_text="Refresh token encriptado para renovación automática"
    )
    
    # Timestamp de creación del registro
    # Se establece automáticamente al crear el objeto
    # Útil para auditoría y análisis
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación del usuario"
    )
    
    # Timestamp de última actualización
    # Se actualiza automáticamente en cada save()
    # Útil para rastrear última actividad del usuario
    last_login = models.DateTimeField(
        auto_now=True,
        help_text="Fecha y hora de última actualización (login o refresh)"
    )

    class Meta:
        """Metadata del modelo."""
        
        # Nombre legible en Django Admin
        verbose_name = "Usuario de Microsoft"
        verbose_name_plural = "Usuarios de Microsoft"
        
        # Ordenamiento por defecto: más recientes primero
        ordering = ['-last_login']
        
        # Índices adicionales para optimización de queries
        indexes = [
            # Índice para búsquedas por fecha de creación
            models.Index(fields=['-created_at'], name='idx_created_at'),
            # Índice para búsquedas por última actividad
            models.Index(fields=['-last_login'], name='idx_last_login'),
        ]

    def __str__(self) -> str:
        """
        Representación en string del modelo.
        
        Muestra los primeros 8 caracteres del hash para identificación
        sin exponer información sensible.
        
        Returns:
            str: Representación del usuario
        
        Ejemplo:
            "Usuario a1b2c3d4..."
        """
        return f"Usuario {self.client_id_hash[:8]}..."
    
    def __repr__(self) -> str:
        """
        Representación técnica del modelo para debugging.
        
        Returns:
            str: Representación técnica
        
        Ejemplo:
            "<MicrosoftUser id=1 hash=a1b2c3d4...>"
        """
        return f"<MicrosoftUser id={self.id} hash={self.client_id_hash[:8]}...>"
