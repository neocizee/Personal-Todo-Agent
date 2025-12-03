"""
Health Check Endpoint para Monitoreo.

Este módulo proporciona un endpoint HTTP para verificar el estado
de salud de la aplicación y sus dependencias.

Endpoint:
---------
GET /health/ - Verifica estado de DB, Redis y aplicación

Autor: Personal Todo Agent Team
Última modificación: 2025-11-29
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Health check endpoint para monitoreo de la aplicación.
    
    Verifica el estado de:
    - Conexión a base de datos PostgreSQL
    - Conexión a Redis (cache)
    - Estado general de la aplicación
    
    Este endpoint es útil para:
    - Load balancers (para routing de tráfico)
    - Sistemas de monitoreo (Kubernetes liveness/readiness probes)
    - Alertas automáticas de downtime
    
    Args:
        request: HttpRequest object
        
    Returns:
        JsonResponse con status 200 si todo está bien,
        o status 503 si hay problemas
        
    Response Format:
    ----------------
    Success (200 OK):
        {
            "status": "healthy",
            "checks": {
                "database": "ok",
                "cache": "ok"
            }
        }
    
    Failure (503 Service Unavailable):
        {
            "status": "unhealthy",
            "checks": {
                "database": "error",
                "cache": "ok"
            }
        }
    
    Examples:
    ---------
    Uso con curl:
        $ curl http://localhost:8000/health/
        {"status": "healthy", "checks": {"database": "ok", "cache": "ok"}}
    
    Uso en Kubernetes:
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
    """
    health_status = {
        'status': 'healthy',
        'checks': {}
    }
    
    # =========================================================================
    # Check 1: Database Connection
    # =========================================================================
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                health_status['checks']['database'] = 'ok'
            else:
                raise Exception("Database query returned unexpected result")
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        health_status['checks']['database'] = 'error'
        health_status['status'] = 'unhealthy'
    
    # =========================================================================
    # Check 2: Redis Cache Connection
    # =========================================================================
    try:
        # Intentar escribir y leer del cache
        cache.set('health_check', 'ok', 10)
        cached_value = cache.get('health_check')
        
        if cached_value == 'ok':
            health_status['checks']['cache'] = 'ok'
        else:
            raise Exception("Cache read/write failed")
    except Exception as e:
        logger.error(f"Redis health check failed: {e}", exc_info=True)
        health_status['checks']['cache'] = 'error'
        health_status['status'] = 'unhealthy'
    
    # =========================================================================
    # Determinar status code HTTP
    # =========================================================================
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    # Log del resultado
    if status_code == 200:
        logger.debug("Health check passed")
    else:
        logger.warning(f"Health check failed: {health_status}")
    
    return JsonResponse(health_status, status=status_code)
