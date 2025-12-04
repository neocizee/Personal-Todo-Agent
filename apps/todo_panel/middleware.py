import time
import logging
import json

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    """
    Middleware para loguear detalles de cada request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        
        # Procesar request
        response = self.get_response(request)
        
        # Calcular duración
        duration = (time.time() - start_time) * 1000
        
        # Obtener IP del cliente
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        # Obtener User ID si existe
        user_id = request.session.get('user_id', 'anonymous')
        
        # Loguear detalles
        log_data = {
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration_ms': round(duration, 2),
            'ip': ip,
            'user_id': user_id
        }
        
        if response.status_code >= 500:
            logger.error(f"Request failed: {json.dumps(log_data)}")
        elif response.status_code >= 400:
            logger.warning(f"Request warning: {json.dumps(log_data)}")
        else:
            logger.info(f"Request success: {json.dumps(log_data)}")
            
        return response
