from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError
from django.core.cache import caches
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
def health_check(request):
    """
    Endpoint para verificar el estado de salud de la aplicación.
    Verifica conectividad a Base de Datos y Redis.
    """
    health_status = {
        "status": "healthy",
        "checks": {
            "database": "unknown",
            "cache": "unknown"
        }
    }
    status_code = 200

    # Verificar Base de Datos
    try:
        db_conn = connections['default']
        db_conn.cursor()
        health_status["checks"]["database"] = "ok"
    except OperationalError as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
        status_code = 503
        logger.error(f"Health check failed: Database error: {e}")

    # Verificar Cache (Redis)
    try:
        cache = caches['default']
        cache.set('health_check', 'ok', timeout=1)
        if cache.get('health_check') == 'ok':
            health_status["checks"]["cache"] = "ok"
        else:
            health_status["checks"]["cache"] = "error: read/write failed"
            health_status["status"] = "unhealthy"
            status_code = 503
    except Exception as e:
        health_status["checks"]["cache"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
        status_code = 503
        logger.error(f"Health check failed: Cache error: {e}")

    return JsonResponse(health_status, status=status_code)
