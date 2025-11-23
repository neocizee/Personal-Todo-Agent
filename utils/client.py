import os
import requests
import base64
from typing import Dict, List, Optional
from datetime import datetime

class MicrosoftTodoClient:
    """Cliente para interactuar con Microsoft To Do API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def get_attachment(self, list_id: str, task_id: str, attachment_id: str) -> Dict:
        """Obtiene los detalles completos de un adjunto, incluyendo contentBytes"""
        url = f"{self.base_url}/me/todo/lists/{list_id}/tasks/{task_id}/attachments/{attachment_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Error al obtener adjunto: {response.status_code} - {response.text}")

    def save_attachment(self, list_id: str, task_id: str, attachment_id: str, output_dir: str = ".") -> str:
        """Descarga y guarda un adjunto en el directorio especificado"""
        attachment = self.get_attachment(list_id, task_id, attachment_id)
        if attachment.get('@odata.type') != '#microsoft.graph.taskFileAttachment':
            raise Exception("El adjunto no es un archivo (taskFileAttachment)")
        
        content_bytes = attachment.get('contentBytes')
        if not content_bytes:
            raise Exception("No se encontró contenido en el adjunto")
            
        filename = attachment.get('name', 'untitled')
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(content_bytes))
            
        return filepath

    def get_lists(self) -> List[Dict]:
        """
        Obtiene todas las listas de tareas del usuario.
        
        Returns:
            Lista de diccionarios con información de las listas
        """
        # Soporte para paginación y obtener todas las listas (máximo $top=100 por página)
        url = f"{self.base_url}/me/todo/lists?$top=100"
        lists = []
        while url:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                lists.extend(data.get('value', []))
                url = data.get('@odata.nextLink')  # Si hay más páginas, continuar
            else:
                raise Exception(f"Error al obtener listas: {response.status_code} - {response.text}")
        return lists

    def get_list_by_name(self, list_name: str) -> Optional[Dict]:
        """
        Busca una lista por su nombre.
        
        Args:
            list_name: Nombre de la lista a buscar
            
        Returns:
            Diccionario con la información de la lista o None si no se encuentra
        """
        lists = self.get_lists()
        for task_list in lists:
            if task_list['displayName'].lower() == list_name.lower():
                return task_list
        return None

    def get_tasks(self, list_id: str) -> List[Dict]:
        """
        Obtiene todas las tareas de una lista específica, incluyendo subtareas,
        recursos vinculados y adjuntos.
        
        Args:
            list_id: ID de la lista de tareas
            
        Returns:
            Lista de diccionarios con información de las tareas
        """
        # Obtener todas las tareas de la lista (paginación)
        tasks = []
        # Se agrega $expand para obtener checklistItems, linkedResources y attachments
        # Nota: attachments a veces no se expande correctamente en la vista de lista,
        # por lo que se verificará y obtendrá individualmente si es necesario.
        url = f"{self.base_url}/me/todo/lists/{list_id}/tasks?$top=100&$expand=checklistItems,linkedResources,attachments"
        while url:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                tasks_page = data.get('value', [])
                if not tasks_page:
                    break  # No hay más tareas
                
                # Verificar y obtener adjuntos si faltan
                for task in tasks_page:
                    if task.get('hasAttachments') and 'attachments' not in task:
                        try:
                            att_url = f"{self.base_url}/me/todo/lists/{list_id}/tasks/{task['id']}/attachments"
                            att_resp = requests.get(att_url, headers=self.headers)
                            if att_resp.status_code == 200:
                                task['attachments'] = att_resp.json().get('value', [])
                        except Exception as e:
                            print(f"Error al obtener adjuntos para tarea {task.get('id')}: {e}")

                tasks.extend(tasks_page)
                url = data.get('@odata.nextLink')  # Si hay más páginas, continuar
            else:
                raise Exception(f"Error al obtener tareas: {response.status_code} - {response.text}")
        return tasks

    def analyze_list(self, list_name: str) -> Dict:
        """
        Analiza una lista específica y retorna estadísticas.
        
        Args:
            list_name: Nombre de la lista a analizar
            
        Returns:
            Diccionario con análisis de la lista
        """
        # Buscar la lista
        task_list = self.get_list_by_name(list_name)
        if not task_list:
            raise Exception(f"No se encontró la lista: {list_name}")
        
        # Obtener tareas
        tasks = self.get_tasks(task_list['id'])
        
        # Analizar tareas
        analysis = {
            'list_name': task_list['displayName'],
            'list_id': task_list['id'],
            'total_tasks': len(tasks),
            'completed_tasks': 0,
            'pending_tasks': 0,
            'tasks_with_due_date': 0,
            'overdue_tasks': 0,
            'tasks_by_importance': {
                'high': 0,
                'normal': 0,
                'low': 0
            },
            'tasks': []
        }
        
        now = datetime.now()
        
        for task in tasks:
            # Estado de completado
            if task['status'] == 'completed':
                analysis['completed_tasks'] += 1
            else:
                analysis['pending_tasks'] += 1
            
            # Fecha de vencimiento
            if task.get('dueDateTime'):
                analysis['tasks_with_due_date'] += 1
                due_date = datetime.fromisoformat(task['dueDateTime']['dateTime'].replace('Z', '+00:00'))
                if due_date < now and task['status'] != 'completed':
                    analysis['overdue_tasks'] += 1
            
            # Importancia
            importance = task.get('importance', 'normal')
            if importance in analysis['tasks_by_importance']:
                analysis['tasks_by_importance'][importance] += 1
            
            # Agregar tarea simplificada al análisis
            task_info = {
                'id': task['id'],
                'title': task['title'],
                'status': task['status'],
                'importance': task.get('importance', 'normal'),
                'created': task.get('createdDateTime'),
                'due_date': task.get('dueDateTime', {}).get('dateTime') if task.get('dueDateTime') else None,
                'completed_date': task.get('completedDateTime', {}).get('dateTime') if task.get('completedDateTime') else None,
                'body': task.get('body', {}).get('content', ''),
                'checklist_items': task.get('checklistItems', []),
                'linked_resources': task.get('linkedResources', []),
                'attachments': task.get('attachments', [])
            }
            analysis['tasks'].append(task_info)
        
        return analysis
    
    def print_analysis(self, analysis: Dict):
        """
        Imprime un análisis formateado de una lista.
        
        Args:
            analysis: Diccionario con el análisis de la lista
        """
        
        print(f"\n{'=' * 60}")
        print("LISTA DE TAREAS:")
        print("=" * 60)
        
        for i, task in enumerate(analysis['tasks'], 1):
            status_icon = "✓" if task['status'] == 'completed' else "○"
            importance_icon = "!" if task['importance'] == 'high' else ""
            
            print(f"\n{i}. [{status_icon}] {importance_icon}{task['title']}")
            print(f"   Estado: {task['status']}")
            print(f"   Importancia: {task['importance']}")
            if task['due_date']:
                print(f"   Fecha de vencimiento: {task['due_date']}")
            if task['completed_date']:
                print(f"   Completada el: {task['completed_date']}")
            
            # Mostrar subtareas
            if task['checklist_items']:
                print(f"   Subtareas ({len(task['checklist_items'])}):")
                for item in task['checklist_items']:
                    check_icon = "✓" if item.get('isChecked') else "○"
                    print(f"     - [{check_icon}] {item.get('displayName')}")

            # Mostrar recursos vinculados
            if task['linked_resources']:
                print(f"   Recursos vinculados ({len(task['linked_resources'])}):")
                for resource in task['linked_resources']:
                    print(f"     - {resource.get('displayName')} ({resource.get('webUrl')})")

            # Mostrar adjuntos
            if task['attachments']:
                print(f"   Adjuntos ({len(task['attachments'])}):")
                for attachment in task['attachments']:
                    print(f"     - {attachment.get('name')} ({attachment.get('contentType')})")

            if task['body']:
                print(f"   Notas: {task['body'][:100]}...")

def analyze_list_via_client(access_token: str, list_name: str) -> Dict:
    """Helper function to analyze a list using the client"""
    client = MicrosoftTodoClient(access_token)
    return client.analyze_list(list_name)
