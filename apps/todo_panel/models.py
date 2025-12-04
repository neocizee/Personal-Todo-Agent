from django.db import models

class MicrosoftUser(models.Model):
    """
    Modelo para almacenar usuarios autenticados con Microsoft.
    
    Almacena tokens encriptados y un hash del client_id para búsquedas.
    No almacena información personal identificable (PII) en texto plano.
    """
    # Hash SHA-256 del Client ID para búsquedas rápidas y anónimas
    client_id_hash = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Datos sensibles encriptados (Fernet)
    encrypted_client_id = models.BinaryField()
    encrypted_access_token = models.BinaryField()
    encrypted_refresh_token = models.BinaryField(null=True, blank=True)
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Microsoft User"
        verbose_name_plural = "Microsoft Users"
        indexes = [
            models.Index(fields=['last_login']),
        ]

    def __str__(self):
        return f"MicrosoftUser(hash={self.client_id_hash[:8]}...)"
