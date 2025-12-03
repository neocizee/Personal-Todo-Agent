"""
Middleware personalizado para la aplicación todo_panel.

Este módulo contiene middleware que se ejecuta en cada request/response,
proporcionando funcionalidad cross-cutting como logging y monitoreo.

Middleware incluido:
-------------------
- RequestLoggingMiddleware: Logging de todas las peticiones HTTP con métricas

Autor: Personal Todo Agent Team
Última modificación: 2025-11-29
"""
import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware para logging automático de requests HTTP.
    
    Registra información sobre cada request incluyendo:
    - Método HTTP (GET, POST, etc.)
    - Path de la URL
    - Status code de la respuesta
    - Duración de la petición en milisegundos
    - User ID de la sesión (si existe)
    - IP del cliente (considerando proxies)
    
    El logging se realiza en nivel INFO para requests exitosos (2xx, 3xx)
    y WARNING para errores del cliente/servidor (4xx, 5xx).
    
    Uso:
    ----
    Agregar a MIDDLEWARE en settings.py:
        MIDDLEWARE = [
            ...
            'apps.todo_panel.middleware.RequestLoggingMiddleware',
        ]
    
    Examples:
    ---------
    Log output típico:
        INFO GET /api/auth/check/ status_code=200 duration_ms=45.23 user_id=1 ip=192.168.1.100
        WARNING POST /api/auth/initiate/ status_code=400 duration_ms=12.45 user_id=None ip=10.0.0.5
    """
    
    def process_request(self, request):
        """
        Se ejecuta antes de que Django procese la vista.
        
        Guarda el timestamp de inicio del request para calcular
        la duración total después.
        
        Args:
            request: HttpRequest object
            
        Returns:
            None (permite que el request continúe)
        """
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """
        Se ejecuta después de que la vista retorna una respuesta.
        
        Calcula la duración del request y registra información completa
        incluyendo métricas de performance.
        
        Args:
            request: HttpRequest object
            response: HttpResponse object
            
        Returns:
            HttpResponse object (sin modificar)
        """
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            duration_ms = round(duration * 1000, 2)
            
            # Determinar nivel de log basado en status code
            log_level = logging.INFO
            if response.status_code >= 400:
                log_level = logging.WARNING
            if response.status_code >= 500:
                log_level = logging.ERROR
            
            # Extraer información del request
            user_id = request.session.get('user_id', None)
            client_ip = self.get_client_ip(request)
            
            # Logging estructurado con extra fields
            logger.log(
                log_level,
                f"{request.method} {request.path}",
                extra={
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                    'user_id': user_id,
                    'ip': client_ip,
                    'method': request.method,
                    'path': request.path,
                }
            )
        
        return response
    
    @staticmethod
    def get_client_ip(request):
        """
        Obtiene la IP real del cliente considerando proxies.
        
        Verifica el header X-Forwarded-For que es establecido por
        proxies y load balancers. Si no existe, usa REMOTE_ADDR.
        
        Args:
            request: HttpRequest object
            
        Returns:
            str: Dirección IP del cliente
            
        Notes:
            En producción con load balancers, X-Forwarded-For puede
            contener múltiples IPs separadas por comas. Tomamos la primera
            que es la IP original del cliente.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For puede tener múltiples IPs: "client, proxy1, proxy2"
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
