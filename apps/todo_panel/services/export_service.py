"""
Servicio de Exportación de Tareas con Controles de Seguridad
=============================================================

Este módulo maneja la exportación de tareas a JSON/Markdown con ZIP,
implementando controles de seguridad según OWASP:

- Rate limiting por usuario
- Límites de tamaño de exportación
- Validación de recursos
- Auditoría de exportaciones

Referencias OWASP:
- A04:2021 – Insecure Design
- A05:2021 – Security Misconfiguration
"""

import zipfile
import io
import json
import logging
import re
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from urllib.parse import quote

import pandas as pd
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class ExportLimitExceeded(Exception):
    """Excepción cuando se exceden los límites de exportación."""
    pass


class ExportService:
    """
    Servicio centralizado para exportación de tareas con controles de seguridad.
    
    Límites configurables:
    - MAX_EXPORTS_PER_HOUR: Exportaciones máximas por usuario por hora
    - MAX_TASKS_PER_EXPORT: Tareas máximas por exportación
    - MAX_ATTACHMENT_SIZE: Tamaño máximo de adjunto individual (bytes)
    - MAX_TOTAL_EXPORT_SIZE: Tamaño máximo total del ZIP (bytes)
    """
    
    # Configuración de límites (OWASP A04: Insecure Design)
    MAX_EXPORTS_PER_HOUR = getattr(settings, 'MAX_EXPORTS_PER_HOUR', 10)
    MAX_TASKS_PER_EXPORT = getattr(settings, 'MAX_TASKS_PER_EXPORT', 500)
    MAX_ATTACHMENT_SIZE = getattr(settings, 'MAX_ATTACHMENT_SIZE', 10 * 1024 * 1024)  # 10MB
    MAX_TOTAL_EXPORT_SIZE = getattr(settings, 'MAX_TOTAL_EXPORT_SIZE', 50 * 1024 * 1024)  # 50MB
    
    def __init__(self, user_id: int, client):
        self.user_id = user_id
        self.client = client
        self.total_size = 0
        
    def check_rate_limit(self) -> None:
        """
        Verifica el rate limit de exportaciones por usuario.
        Usa Redis para tracking distribuido.
        
        Raises:
            ExportLimitExceeded: Si se excede el límite de exportaciones.
        """
        cache_key = f"export_rate_limit:{self.user_id}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= self.MAX_EXPORTS_PER_HOUR:
            logger.warning(
                f"Rate limit excedido para usuario {self.user_id}. "
                f"Intentos: {current_count}/{self.MAX_EXPORTS_PER_HOUR}"
            )
            raise ExportLimitExceeded(
                f"Has excedido el límite de {self.MAX_EXPORTS_PER_HOUR} exportaciones por hora. "
                "Por favor, intenta más tarde."
            )
        
        # Incrementar contador con TTL de 1 hora
        cache.set(cache_key, current_count + 1, timeout=3600)
        logger.info(f"Export rate limit check passed: {current_count + 1}/{self.MAX_EXPORTS_PER_HOUR}")
    
    def validate_export_size(self, tasks: List[Dict]) -> None:
        """
        Valida que la exportación no exceda los límites de tamaño.
        
        Args:
            tasks: Lista de tareas a exportar
            
        Raises:
            ExportLimitExceeded: Si se exceden los límites.
        """
        if len(tasks) > self.MAX_TASKS_PER_EXPORT:
            raise ExportLimitExceeded(
                f"La lista contiene {len(tasks)} tareas. "
                f"El límite es {self.MAX_TASKS_PER_EXPORT} por exportación."
            )
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitiza nombres de archivo para prevenir path traversal.
        
        OWASP: Prevención de Path Traversal (CWE-22)
        """
        # Remover caracteres peligrosos
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
        # Limitar longitud
        filename = filename[:255]
        # Prevenir nombres especiales de Windows
        reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                         'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        name_without_ext = filename.rsplit('.', 1)[0].upper()
        if name_without_ext in reserved_names:
            filename = f"file_{filename}"
        
        return filename.strip() or "unnamed_file"
    
    def process_attachment(
        self, 
        zip_file: zipfile.ZipFile, 
        attachment: Dict, 
        list_id: str, 
        task_id: str,
        counter: int
    ) -> Optional[str]:
        """
        Procesa un adjunto individual con validaciones de seguridad.
        
        Returns:
            str: Ruta relativa del adjunto en el ZIP, o None si falla
        """
        try:
            cache_key = f"microsoft_attachment:{list_id}:{task_id}:{attachment['id']}"
            file_content = cache.get(cache_key)
            
            if not file_content:
                logger.warning(f"Adjunto no encontrado en caché: {attachment.get('name')}")
                return None
            
            # Validar tamaño del adjunto
            attachment_size = len(file_content)
            if attachment_size > self.MAX_ATTACHMENT_SIZE:
                logger.warning(
                    f"Adjunto {attachment.get('name')} excede el límite: "
                    f"{attachment_size} > {self.MAX_ATTACHMENT_SIZE}"
                )
                return None
            
            # Validar tamaño total
            if self.total_size + attachment_size > self.MAX_TOTAL_EXPORT_SIZE:
                logger.warning(
                    f"Tamaño total de exportación excedería el límite: "
                    f"{self.total_size + attachment_size} > {self.MAX_TOTAL_EXPORT_SIZE}"
                )
                return None
            
            # Sanitizar nombre de archivo
            filename = self.sanitize_filename(
                attachment.get('name', f'attachment_{counter}.bin')
            )
            
            # Guardar en ZIP
            zip_path = f"attachments/{filename}"
            zip_file.writestr(zip_path, file_content)
            
            self.total_size += attachment_size
            logger.info(f"Adjunto agregado: {zip_path} ({attachment_size} bytes)")
            
            return zip_path
            
        except Exception as e:
            logger.error(f"Error procesando adjunto {attachment.get('name')}: {e}", exc_info=True)
            return None
    
    def create_export(
        self, 
        list_id: str, 
        list_name: str, 
        export_format: str = 'json'
    ) -> Tuple[bytes, str]:
        """
        Crea la exportación completa con todas las validaciones.
        
        Args:
            list_id: ID de la lista a exportar
            list_name: Nombre de la lista
            export_format: 'json' o 'markdown'
            
        Returns:
            Tuple[bytes, str]: (contenido del ZIP, nombre del archivo)
            
        Raises:
            ExportLimitExceeded: Si se exceden límites
        """
        # 1. Verificar rate limit
        self.check_rate_limit()
        
        # 2. Obtener tareas
        tareas = self.client.get_tasks_by_list_id(list_id, force_refresh=True)
        if not tareas:
            raise ValueError("No hay tareas para exportar")
        
        # 3. Validar tamaño
        self.validate_export_size(tareas)
        
        # 4. Crear ZIP
        zip_buffer = io.BytesIO()
        processed_tasks = []
        attachment_counter = 0
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for tarea in tareas:
                task_data = self._process_task(tarea, zip_file, list_id, attachment_counter)
                processed_tasks.append(task_data)
                attachment_counter += len(task_data.get('attachment_path', []))
            
            # Generar contenido
            if export_format == 'markdown':
                content = self._generate_markdown(list_name, processed_tasks)
                extension = '.md'
            else:
                content = self._generate_json(list_name, processed_tasks)
                extension = '.json'
            
            filename = f"{self.sanitize_filename(list_name)}{extension}"
            zip_file.writestr(filename, content.encode('utf-8'))
            
            # README si no hay adjuntos
            if attachment_counter == 0:
                zip_file.writestr(
                    'attachments/README.txt', 
                    'No hay adjuntos en esta lista de tareas.'
                )
        
        # 5. Auditoría
        self._log_export_audit(list_name, export_format, len(tareas), attachment_counter)
        
        zip_buffer.seek(0)
        zip_filename = f"{self.sanitize_filename(list_name)}_export_{extension.lstrip('.')}.zip"
        
        return zip_buffer.getvalue(), zip_filename
    
    def _process_task(
        self, 
        tarea: Dict, 
        zip_file: zipfile.ZipFile, 
        list_id: str,
        counter: int
    ) -> Dict:
        """Procesa una tarea individual."""
        # Formatear fechas con manejo de errores
        fecha_limite = self._format_date(tarea.get('dueDateTime'))
        fecha_recordatorio = self._format_date(tarea.get('reminderDateTime'))
        
        # Procesar subtareas
        subtareas_list = []
        if tarea.get('checklistItems'):
            for item in tarea['checklistItems']:
                check = "[x]" if item.get('isChecked') else "[ ]"
                subtareas_list.append(f"{check} {item.get('displayName', '')}")
        
        # Procesar adjuntos
        attachment_paths = []
        if tarea.get('hasAttachments') and tarea.get('attachments'):
            for attachment in tarea['attachments']:
                zip_path = self.process_attachment(
                    zip_file, attachment, list_id, tarea['id'], counter
                )
                if zip_path:
                    attachment_paths.append(zip_path)
                    counter += 1
        
        return {
            'titulo': tarea.get('title', 'Sin título'),
            'importancia': tarea.get('importance', 'normal'),
            'status': tarea.get('status', 'notStarted'),
            'fecha_limite': fecha_limite,
            'fecha_recordatorio': fecha_recordatorio,
            'subtareas': subtareas_list,
            'descripcion': tarea.get('body', {}).get('content', ''),
            'attachment_path': attachment_paths
        }
    
    def _format_date(self, date_obj: Optional[Dict]) -> Optional[str]:
        """Formatea fechas con manejo de errores."""
        if not date_obj:
            return None
        
        dt_str = date_obj.get('dateTime')
        if not dt_str:
            return None
        
        try:
            return pd.to_datetime(dt_str).tz_localize('UTC').tz_convert(
                'America/Argentina/Buenos_Aires'
            ).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning(f"Error formateando fecha: {e}")
            return None
    
    def _generate_markdown(self, list_name: str, tasks: List[Dict]) -> str:
        """
        Genera contenido Markdown formateado a partir de una lista de tareas.
        Basado en la lógica de json_to_markdown del prototipo.
        """
        # Ordenar tareas: primero las de importancia 'high'
        tasks.sort(key=lambda x: 0 if x.get('importancia') == 'high' else 1)

        md_content = f"# Lista de Tareas: {list_name}\n\n"
        md_content += f"**Total de tareas:** {len(tasks)}\n"
        md_content += f"**Fecha de exportación:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        md_content += "---\n\n"

        for task in tasks:
            # Título e Importancia
            icon = "🔴" if task.get('importancia') == 'high' else "🔵"
            title = task.get('titulo', 'Sin título')
            md_content += f"## {icon} {title}\n\n"
            
            # Metadatos
            status = task.get('status', 'notStarted')
            status_text = "Completada" if status == 'completed' else "Pendiente"
            md_content += f"- **Estado:** {status_text}\n"
            
            if task.get('fecha_limite'):
                md_content += f"- **📅 Vencimiento:** {task['fecha_limite']}\n"
            if task.get('fecha_recordatorio'):
                md_content += f"- **⏰ Recordatorio:** {task['fecha_recordatorio']}\n"
            
            # Subtareas (Checklist)
            if task.get('subtareas'):
                md_content += "\n**Subtareas:**\n"
                for sub in task['subtareas']:
                    md_content += f"- {sub}\n"

            # Descripción
            if task.get('descripcion'):
                desc = task['descripcion']
                
                # Procesamiento línea por línea para respetar la estructura visual
                lines = desc.split('\r\n')
                processed_lines = []
                
                for line in lines:
                    # 1. Detectar Headers por caracteres invisibles (patrón de Microsoft To Do)
                    if '\u200b\u200b' in line:
                        # Asumimos Subtítulo (H4)
                        line = "#### " + line.replace('\u200b', '').strip()
                    elif '\u200b' in line:
                        # Asumimos Título (H3)
                        line = "### " + line.replace('\u200b', '').strip()
                    
                    # 2. Limpiar caracteres invisibles restantes
                    line = line.replace('\u200b', '')
                    
                    # 3. Formatear links
                    # Caso 1: Texto pegado al link tipo "link<http://...>" -> "[link](http://...)"
                    line = re.sub(r'([^\s<]+)<((?:http|https)://[^>]+)>', r'[\1](\2)', line)
                    # Caso 2: Link solo "<http://...>" -> "[http://...](http://...)"
                    line = re.sub(r'<((?:http|https)://[^>]+)>', r'[\1](\1)', line)
                    
                    # 4. Asegurar saltos de línea duros
                    if line.strip():
                        processed_lines.append(line + "  ")
                    else:
                        processed_lines.append("")
                
                desc = '\n'.join(processed_lines).strip()
                if desc:
                    md_content += f"\n**Descripción:**\n\n{desc}\n"

            # Adjuntos
            if task.get('attachment_path') and task['attachment_path']:
                md_content += "\n**📎 Adjuntos:**\n"
                for path in task['attachment_path']:
                    filename = os.path.basename(path)
                    # URL-encode el path para manejar espacios y caracteres especiales
                    # Usar quote con safe='/' para mantener las barras
                    encoded_path = quote(path, safe='/')
                    
                    # Detectar si es imagen para mostrarla embebida
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                        # Usar tag HTML para controlar el tamaño (width="400")
                        md_content += f'<img src="{encoded_path}" width="400" alt="{filename}">\n'
                    else:
                        # Usar formato Markdown con path URL-encoded
                        md_content += f"- [{filename}]({encoded_path})\n"

            md_content += "\n---\n\n"
        
        return md_content
    
    def _generate_json(self, list_name: str, tasks: List[Dict]) -> str:
        """Genera contenido JSON."""
        export_data = {
            'list_name': list_name,
            'exported_at': pd.Timestamp.now().isoformat(),
            'tasks': tasks
        }
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def _log_export_audit(
        self, 
        list_name: str, 
        format_type: str, 
        task_count: int, 
        attachment_count: int
    ) -> None:
        """Registra auditoría de exportación."""
        logger.info(
            f"EXPORT_AUDIT: user_id={self.user_id}, list={list_name}, "
            f"format={format_type}, tasks={task_count}, "
            f"attachments={attachment_count}, size={self.total_size} bytes"
        )
