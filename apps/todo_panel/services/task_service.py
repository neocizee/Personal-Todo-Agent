import threading
import logging
from django.core.cache import cache
from .microsoft_client import MicrosoftClient
from .cache_optimizer import CacheOptimizer, RateLimiter
import pandas as pd

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self, user):
        self.user = user
        self.client = MicrosoftClient(user)

    def sync_tasks_background(self, list_id):
        """Inicia la sincronización en segundo plano."""
        thread = threading.Thread(target=self._sync_process, args=(list_id,))
        thread.daemon = True
        thread.start()

    def _sync_process(self, list_id):
        """
        Proceso de sincronización de tareas con compresión.
        Actualiza el progreso en Redis y guarda el resultado final comprimido.
        """
        cache_key = f"sync_progress:{self.user.id}:{list_id}"
        main_cache_key = f"tasks_{self.user.id}_{list_id}"
        
        try:
            # Estado inicial
            cache.set(cache_key, {'state': 'starting', 'count': 0, 'total': 0}, timeout=600)
            
            # Primero, obtener el conteo total de tareas (sin expand para ser rápido)
            total_count = self._get_total_task_count(list_id)
            
            cache.set(cache_key, {
                'state': 'fetching', 
                'count': 0,
                'total': total_count,
                'message': f'Cargando tareas (0/{total_count})...'
            }, timeout=600)
            
            tasks = []
            count = 0
            
            # Iterar sobre las páginas
            for page in self.client.fetch_tasks_pages(list_id):
                tasks.extend(page)
                count += len(page)
                
                # Actualizar progreso con total
                cache.set(cache_key, {
                    'state': 'fetching', 
                    'count': count,
                    'total': total_count,
                    'message': f'Cargando tareas ({count}/{total_count})...'
                }, timeout=600)
            
            # Guardar lista completa en caché COMPRIMIDA (ahorro ~60-70% memoria)
            CacheOptimizer.set_compressed(main_cache_key, tasks, timeout=300)
            logger.info(f"Tasks saved with compression for list {list_id}")
            
            # Finalizado
            cache.set(cache_key, {
                'state': 'completed', 
                'count': count,
                'total': total_count,
                'message': f'Carga completada ({count} tareas)'
            }, timeout=600)
            
            logger.info(f"Sincronización completada para lista {list_id}: {count} tareas")
            
        except Exception as e:
            logger.error(f"Error en sincronización de tareas: {e}", exc_info=True)
            cache.set(cache_key, {
                'state': 'error', 
                'error': str(e),
                'message': 'Error al cargar tareas'
            }, timeout=600)
    
    def _get_total_task_count(self, list_id):
        """Obtiene el conteo total de tareas sin expandir datos (más rápido)."""
        try:
            url = f"{self.client.BASE_URL}/me/todo/lists/{list_id}/tasks?$top=1&$count=true"
            response = self.client._make_request(url)
            if response and '@odata.count' in response:
                return response['@odata.count']
            # Fallback: contar manualmente
            return self._count_tasks_manually(list_id)
        except:
            return 0
    
    def _count_tasks_manually(self, list_id):
        """Cuenta tareas manualmente si @odata.count no está disponible."""
        count = 0
        url = f"{self.client.BASE_URL}/me/todo/lists/{list_id}/tasks?$top=100&$select=id"
        while url:
            response = self.client._make_request(url)
            if response:
                count += len(response.get('value', []))
                url = response.get('@odata.nextLink')
            else:
                break
        return count

    def get_sync_progress(self, list_id):
        """Obtiene el progreso actual de la sincronización."""
        cache_key = f"sync_progress:{self.user.id}:{list_id}"
        return cache.get(cache_key)
