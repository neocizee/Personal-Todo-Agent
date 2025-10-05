## Microsoft To Do Analyzer

Analizador ligero en Python que se conecta a Microsoft Graph (Microsoft To Do) para obtener listas y tareas, generar estadísticas básicas y exportarlas a JSON. En esta fase inicial el foco está en una base sólida, simple y escalable.

### ¿Qué hace ahora?
- Autenticación OAuth 2.0 mediante Device Code Flow (sin secretos en cliente).
- Descarga paginada de listas y tareas del usuario.
- Análisis básico por lista: totales, completadas vs pendientes, con vencimiento, vencidas, importancia (alta/normal/baja).
- Exportación del análisis en estructura JSON lista para consumo posterior.
- Impresión formateada en consola.

### Lógica de negocio actual (MicrosoftTodoClient.py)
- `get_task_lists()`: obtiene todas las listas (con paginación vía `@odata.nextLink`).
- `get_tasks_from_list(list_id)`: obtiene todas las tareas de una lista (paginación incluida).
- `find_list_by_name(list_name)`: busca lista por nombre.
- `analyze_list(list_name)`: construye el resumen estadístico y lista de tareas normalizada.
- `print_analysis(analysis)`: salida legible en terminal.
- Soporte de autenticación: `get_access_token_device_code(client_id, tenant_id)` con alcance `Tasks.ReadWrite`.
- Soporte de configuración: `load_env_file()` para `config.env`.

## Estado del proyecto
Primera versión funcional enfocada en extracción y análisis básico. Ideal para un primer commit claro, testeable y fácil de extender.

## Requisitos
- Python 3.8+
- Cuenta de Microsoft (se recomienda personal para pruebas)

## Instalación
```bash
pip install -r requirements.txt
```

## Configuración (Azure AD / Entra ID)
1) Registra una app pública (sin secreto) en Azure Portal.
2) Permisos delegados en Microsoft Graph: `Tasks.ReadWrite`.
3) Authentication → Allow public client flows = Yes.
4) Obtén el Application (client) ID.

Crea `config.env` en el directorio del proyecto:
```
CLIENT_ID=TU_CLIENT_ID
TENANT_ID=consumers
DEFAULT_LIST_NAME=Tasks
```

También puedes usar la guía interactiva:
```bash
python setup_guide.py
```

## Uso básico
Ejemplo mínimo (autenticación por código de dispositivo y análisis de una lista):
```python
from MicrosoftTodoClient import MicrosoftTodoClient, get_access_token_device_code, load_env_file

env = load_env_file('config.env')
token = get_access_token_device_code(env['CLIENT_ID'], env.get('TENANT_ID', 'consumers'))
client = MicrosoftTodoClient(token)

analysis = client.analyze_list(env.get('DEFAULT_LIST_NAME', 'Tasks'))
client.print_analysis(analysis)

# Guardar a JSON si se desea
import json
with open('todo_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)
```

## Estructura JSON resultante (resumen)
```json
{
  "list_name": "Mi Lista",
  "list_id": "...",
  "total_tasks": 305,
  "completed_tasks": 64,
  "pending_tasks": 241,
  "tasks_with_due_date": 0,
  "overdue_tasks": 0,
  "tasks_by_importance": { "high": 0, "normal": 305, "low": 0 },
  "tasks": [ { "id": "...", "title": "...", "status": "notStarted", "importance": "normal", "created": "...", "due_date": null, "completed_date": null, "body": "" } ]
}
```

## Buenas prácticas y objetivos de escalabilidad
- API client delgado y testeable (métodos pequeños, responsabilidades claras).
- Paginación soportada desde el día 0.
- Estructura JSON estable como contrato para futuras integraciones (ETL, dashboards, etc.).
- Configuración fuera del código (`config.env`).
- Dependencias mínimas.

## Seguridad
- Sin secretos persistidos en cliente.
- Tokens de acceso temporales (Device Code Flow).
- No compartas tu `CLIENT_ID` si es de uso personal.

## Licencia y contribución
Repositorio abierto a mejoras. PRs bienvenidos (tests y lint incluidos en futuros commits).
