import json
import os
import pandas as pd
import re
from typing import List, Dict, Union

def json_to_markdown(list_name: str, json_path: str, output_md_path: str) -> int:
    """
    Convierte un archivo JSON de tareas exportadas a un formato Markdown legible.
    
    Args:
        list_name: Nombre de la lista de tareas.
        json_path: Ruta al archivo JSON fuente.
        output_md_path: Ruta donde se guardará el archivo Markdown.
        
    Returns:
        int: Cantidad de tareas procesadas.
    """
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"No se encontró el archivo JSON: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)

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
        md_content += f"- **Estado:** Pendiente\n"
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
            # Limpiar y formatear la descripción
            desc = task['descripcion']
            
            # Procesamiento línea por línea para respetar la estructura visual
            lines = task['descripcion'].split('\r\n')
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
                # Si la línea tiene contenido, agregamos dos espacios al final
                if line.strip():
                    processed_lines.append(line + "  ")
                else:
                    processed_lines.append("") # Mantener líneas vacías para separación de párrafos
            
            desc = '\n'.join(processed_lines)
            
            desc = desc.strip()
            if desc:
                md_content += f"\n**Descripcion:**\n\n{desc}\n"

        # Adjuntos
        attachment_paths = task.get('attachment_path')
        if attachment_paths:
            md_content += "\n**📎 Adjuntos:**\n"
            
            # Normalizar a lista para manejar ambos casos (str o list)
            if isinstance(attachment_paths, str):
                attachment_paths = [attachment_paths]
                
            if isinstance(attachment_paths, list):
                for path in attachment_paths:
                    filename = os.path.basename(path)
                    # Detectar si es imagen para mostrarla embebida
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                        # Usar tag HTML para controlar el tamaño (width="400")
                        md_content += f'<img src="{path}" width="400" alt="{filename}">\n'
                    else:
                        md_content += f"- [{filename}]({path})\n"

        md_content += "\n---\n\n"

    # Guardar archivo
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    return len(tasks)
