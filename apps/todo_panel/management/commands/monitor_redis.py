"""
Comando de Django para monitorear el estado de Redis.

Uso:
    python manage.py monitor_redis
    python manage.py monitor_redis --continuous  # Monitoreo continuo cada 30s
"""

from django.core.management.base import BaseCommand
from apps.todo_panel.services.cache_optimizer import CacheMetrics
import time
import sys


class Command(BaseCommand):
    help = 'Monitorea el estado y métricas de Redis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Monitoreo continuo cada 30 segundos',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Intervalo en segundos para monitoreo continuo (default: 30)',
        )

    def handle(self, *args, **options):
        continuous = options['continuous']
        interval = options['interval']

        self.stdout.write(self.style.SUCCESS('=== Redis Monitoring ===\n'))

        try:
            if continuous:
                self.stdout.write(f'Monitoreo continuo activado (intervalo: {interval}s)')
                self.stdout.write('Presiona Ctrl+C para detener\n')
                
                while True:
                    self._display_metrics()
                    time.sleep(interval)
            else:
                self._display_metrics()
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nMonitoreo detenido por el usuario'))
            sys.exit(0)

    def _display_metrics(self):
        """Muestra las métricas de Redis en formato legible."""
        metrics = CacheMetrics.log_stats()
        
        if not metrics:
            self.stdout.write(self.style.ERROR('Error obteniendo métricas de Redis'))
            return

        # Header
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS(f'  Redis Metrics - {time.strftime("%Y-%m-%d %H:%M:%S")}'))
        self.stdout.write(self.style.SUCCESS('='*60))

        # Memory stats
        self.stdout.write(self.style.HTTP_INFO('\n📊 Memoria:'))
        self.stdout.write(f'  • Uso actual: {metrics.get("memory_used", "N/A")}')
        self.stdout.write(f'  • Pico máximo: {metrics.get("memory_peak", "N/A")}')
        
        frag_ratio = metrics.get('memory_fragmentation', 0)
        if frag_ratio > 1.5:
            frag_style = self.style.WARNING
        else:
            frag_style = self.style.SUCCESS
        self.stdout.write(f'  • Fragmentación: {frag_style(f"{frag_ratio:.2f}")}')

        # Cache performance
        hits = metrics.get('keyspace_hits', 0)
        misses = metrics.get('keyspace_misses', 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0

        self.stdout.write(self.style.HTTP_INFO('\n🎯 Rendimiento de Caché:'))
        self.stdout.write(f'  • Hits: {hits:,}')
        self.stdout.write(f'  • Misses: {misses:,}')
        
        if hit_rate >= 90:
            rate_style = self.style.SUCCESS
        elif hit_rate >= 80:
            rate_style = self.style.WARNING
        else:
            rate_style = self.style.ERROR
        self.stdout.write(f'  • Hit Rate: {rate_style(f"{hit_rate:.2f}%")}')

        # Evictions
        evicted = metrics.get('evicted_keys', 0)
        if evicted > 0:
            self.stdout.write(self.style.HTTP_INFO('\n⚠️  Eviction:'))
            self.stdout.write(self.style.WARNING(f'  • Claves evictadas: {evicted:,}'))

        # Recommendations
        self._show_recommendations(metrics, hit_rate, frag_ratio)

        self.stdout.write(self.style.SUCCESS('\n' + '='*60 + '\n'))

    def _show_recommendations(self, metrics, hit_rate, frag_ratio):
        """Muestra recomendaciones basadas en las métricas."""
        recommendations = []

        if hit_rate < 80:
            recommendations.append('⚠️  Hit rate bajo - Considera aumentar TTL o revisar patrones de acceso')
        
        if frag_ratio > 1.5:
            recommendations.append('⚠️  Alta fragmentación - Considera reiniciar Redis o usar MEMORY PURGE')
        
        evicted = metrics.get('evicted_keys', 0)
        if evicted > 1000:
            recommendations.append('⚠️  Muchas evictions - Aumenta maxmemory o reduce TTL')

        if recommendations:
            self.stdout.write(self.style.HTTP_INFO('\n💡 Recomendaciones:'))
            for rec in recommendations:
                self.stdout.write(f'  {rec}')
