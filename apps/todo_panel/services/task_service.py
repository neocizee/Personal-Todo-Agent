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
            
            # Inicializar Delta Link para futuras sincronizaciones incrementales
            # Hacemos una llamada delta rápida para obtener el token actual
            try:
                # Esto retornará las tareas actuales (redundante) pero nos da el deltaLink
                # O podemos llamar con $deltaToken=latest si soportado, pero Graph standard es iterar.
                # Como acabamos de traer todo, lo mejor es asumir que delta_link lo obtendremos
                # la PRIMERA vez que se llame a sync_tasks_incremental (va a fallar pq no tiene link,
                # pero pedirá uno nuevo y si no hay cambios, listo).
                # Mejor aún: dejemos que sync_tasks_incremental maneje la inicialización lazy.
                pass
            except Exception as e:
                logger.warning(f"Could not initialize delta link: {e}")
            
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

    def sync_tasks_incremental(self, list_id):
        """
        Sincronización inteligente usando delta query.
        Si hay cambios, actualiza el caché y retorna True.
        Si no hay cambios, retorna False.
        """
        main_cache_key = f"tasks_{self.user.id}_{list_id}"
        delta_link_key = f"delta_link_{self.user.id}_{list_id}"
        
        # 1. Obtener tareas y delta link previos
        cached_current_tasks = CacheOptimizer.get_compressed(main_cache_key)
        delta_link = cache.get(delta_link_key)
        
        if not cached_current_tasks:
            logger.info("No cache for incremental sync, skipping.")
            return False

        try:
            # 2. Obtener cambios desde Graph API
            changes, next_link = self.client.get_tasks_delta(list_id, delta_link)
            
            if not changes and not delta_link:
                # Si es la primera vez (no delta link) y no hay cambios (raro), no hacemos nada
                # Pero si estamos arrancando delta query, necesitamos el next_link para la próxima
                if next_link:
                    cache.set(delta_link_key, next_link, timeout=None) # Persistente
                return False
                
            if not changes:
                # Solo actualizar el link si cambió (heartbeat)
                if next_link and next_link != delta_link:
                     cache.set(delta_link_key, next_link, timeout=None)
                return False
            
            logger.info(f"Incremental Sync: {len(changes)} changes detected.")
            
            # 3. Aplicar cambios (Patching)
            # Convertir lista actual a dict {id: task}
            task_map = {t['id']: t for t in cached_current_tasks}
            
            for change in changes:
                change_id = change['id']
                
                # Check for deletion
                if '@removed' in change:
                    if change_id in task_map:
                        del task_map[change_id]
                else:
                    # Update or Insert
                    # El delta puede traer parciales, pero en Graph Tasks suele traer objeto completo
                    # Si trae parcial, deberíamos hacer merge. Asumimos completo update por ahora.
                    task_map[change_id] = change
            
            # 4. Reconstruir lista y guardar
            updated_tasks = list(task_map.values())
            
            # Guardar comprimido
            CacheOptimizer.set_compressed(main_cache_key, updated_tasks, timeout=300)
            
            # Guardar nuevo delta link para la próxima
            if next_link:
                cache.set(delta_link_key, next_link, timeout=None)
                
            return True
            
        except Exception as e:
            logger.error(f"Error in incremental sync: {e}")
            return False

    def get_sync_progress(self, list_id):
        """Obtiene el progreso actual de la sincronización."""
        cache_key = f"sync_progress:{self.user.id}:{list_id}"
        return cache.get(cache_key)
