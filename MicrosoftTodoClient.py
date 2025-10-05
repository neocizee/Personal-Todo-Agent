"""
Script para conectar con Microsoft To Do API y analizar tareas de una lista específica.
Versión con soporte para archivo de configuración .env
"""
import requests
import json
import os
from typing import Optional, List, Dict
from datetime import datetime


class MicrosoftTodoClient:
    """Cliente para interactuar con Microsoft To Do API a través de Microsoft Graph."""
    
    def __init__(self, access_token: str):
        """
        Inicializa el cliente con un token de acceso.
        
        Args:
            access_token: Token de acceso de Azure AD
        """
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_task_lists(self) -> List[Dict]:
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

    def get_tasks_from_list(self, list_id: str) -> List[Dict]:
        """
        Obtiene todas las tareas de una lista específica.
        
        Args:
            list_id: ID de la lista de tareas
            
        Returns:
            Lista de diccionarios con información de las tareas
        """
        # Obtener todas las tareas de la lista (paginación)
        tasks = []
        url = f"{self.base_url}/me/todo/lists/{list_id}/tasks?$top=100"
        while url:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                tasks_page = data.get('value', [])
                if not tasks_page:
                    break  # No hay más tareas
                tasks.extend(tasks_page)
                url = data.get('@odata.nextLink')  # Si hay más páginas, continuar
            else:
                raise Exception(f"Error al obtener tareas: {response.status_code} - {response.text}")
        return tasks

    def find_list_by_name(self, list_name: str) -> Optional[Dict]:
        """
        Busca una lista por su nombre.
        
        Args:
            list_name: Nombre de la lista a buscar
            
        Returns:
            Diccionario con la información de la lista o None si no se encuentra
        """
        lists = self.get_task_lists()
        for task_list in lists:
            if task_list['displayName'].lower() == list_name.lower():
                return task_list
        return None
    
    def analyze_list(self, list_name: str) -> Dict:
        """
        Analiza una lista específica y retorna estadísticas.
        
        Args:
            list_name: Nombre de la lista a analizar
            
        Returns:
            Diccionario con análisis de la lista
        """
        # Buscar la lista
        task_list = self.find_list_by_name(list_name)
        if not task_list:
            raise Exception(f"No se encontró la lista: {list_name}")
        
        # Obtener tareas
        tasks = self.get_tasks_from_list(task_list['id'])
        
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
                'body': task.get('body', {}).get('content', '')
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
            if task['body']:
                print(f"   Notas: {task['body'][:100]}...")


def load_env_file(filename: str = 'config.env') -> Dict[str, str]:
    """
    Carga variables de entorno desde un archivo .env
    
    Args:
        filename: Nombre del archivo .env
        
    Returns:
        Diccionario con las variables de entorno
    """
    env_vars = {}
    
    if not os.path.exists(filename):
        return env_vars
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Ignorar líneas vacías y comentarios
            if not line or line.startswith('#'):
                continue
            
            # Separar clave=valor
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def get_access_token_device_code(client_id: str, tenant_id: str = "common") -> str:
    """
    Obtiene un token de acceso usando el flujo de Device Code.

    Args:
        client_id: Application (client) ID de Azure AD
        tenant_id: Tenant ID (por defecto 'common' para cuentas personales)

    Returns:
        Token de acceso
    """
    # Para cuentas personales de Microsoft, usar 'consumers' en lugar de 'common'
    if tenant_id == "common":
        tenant_id = "consumers"

    # Solicitar código de dispositivo
    device_code_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
    device_code_data = {
        "client_id": client_id,
        "scope": "https://graph.microsoft.com/Tasks.ReadWrite offline_access"
    }
    
    response = requests.post(device_code_url, data=device_code_data)
    device_code_response = response.json()
    
    if 'error' in device_code_response:
        raise Exception(f"Error al obtener código de dispositivo: {device_code_response}")
    
    print(f"\n{device_code_response['message']}")
    print(f"Código: {device_code_response['user_code']}")
    print("\nPresiona Enter después de completar la autenticación...")
    input()
    
    # Solicitar token
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": client_id,
        "device_code": device_code_response['device_code']
    }
    
    response = requests.post(token_url, data=token_data)
    token_response = response.json()
    
    if 'error' in token_response:
        raise Exception(f"Error al obtener token: {token_response}")
    
    return token_response['access_token']
        
