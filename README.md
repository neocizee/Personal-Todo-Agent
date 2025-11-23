## Microsoft To Do Analyzer

Analizador ligero en Python que se conecta a Microsoft Graph (Microsoft To Do) para obtener listas y tareas, generar estadísticas básicas y exportarlas a JSON. En esta fase inicial el foco está en una base sólida, simple y escalable.

### ¿Qué hace ahora?
- Autenticación OAuth 2.0 mediante Device Code Flow (sin secretos en cliente).
- Descarga paginada de listas y tareas del usuario.
- Análisis básico por lista: totales, completadas vs pendientes, con vencimiento, vencidas, importancia (alta/normal/baja).
- Exportación del análisis en estructura JSON lista para consumo posterior.
- Impresión formateada en consola.

### Lógica de negocio actual (utils/)
`utils/client.py`: Contiene la clase `MicrosoftTodoClient`.
- `init(access_token)`: Constructor. Configura headers y URL base.
- `get_lists()`: Obtiene todas las carpetas/listas de tareas.
- `get_tasks(list_id)`: Obtiene tareas de una lista específica.
- `analyze_list(list_name)`: Orquestador que calcula estadísticas.

`utils/auth.py`: Manejo de autenticación.
- `get_access_token_device_code()`: Obtiene token usando Device Code Flow.
- Maneja caché de tokens y refresco automático.

`utils/config.py`:
- `load_env_file()`: Carga configuración desde `config.env`.

`utils/converts.py`:
- `json_to_markdown()`: Convierte exportaciones JSON a reportes Markdown legibles.

## Estado del proyecto
Primera versión funcional enfocada en extracción y análisis básico de tareas en Microsoft To Do.

## Requisitos
- Python 3.8+
- Cuenta de Microsoft (se recomienda personal para pruebas)

## Instalación
```bash
pip install -r requirements.txt
```

## Configuración (Azure AD / Entra ID)
1) Registra una app pública (sin secreto) en Azure Portal.
2) Permisos delegados en Microsoft Graph: `Tasks.Read` (o `Tasks.ReadWrite` si planeas extenderlo).
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

## Uso
Para ejecutar el analizador:
```bash
python main.py
```

## Resumen de Capacidades (Microsoft Graph API - To Do)
La API de Microsoft To Do (v1.0) se estructura en torno a estos recursos principales:

todoTaskList (Listas):
- Son los contenedores de tus tareas.
- Puedes: Listar (GET), Crear (POST), Leer una específica (GET {id}), Actualizar nombre (PATCH) y Eliminar (DELETE).
- Nota: Las listas predeterminadas ("Tasks", "Flagged Emails") no se pueden borrar.

todoTask (Tareas):
- Son los elementos individuales dentro de una lista.
- Propiedades clave: title, status (notStarted, completed), importance (low, normal, high), dueDateTime (vencimiento), body (notas/descripción), createdDateTime.
- Puedes: Listar tareas de una lista, Crear, Leer detalle, Actualizar y Eliminar.

checklistItem (Pasos/Subtareas):
- Son los pasos más pequeños dentro de una tarea (la "lista de comprobación").
- Puedes gestionarlos individualmente (CRUD) dentro de una tarea.

linkedResource (Enlaces):
- Enlaces web de una tarea (conexión con emails o documentos externos).

attachment (Archivos):
- Cuando pides el detalle de un adjunto, la API te devuelve una propiedad llamada contentBytes.
- Este campo contiene el archivo codificado en Base64.
- Para usarlo: Simplemente decodificar ese Base64 y guardarlo como archivo (ej. imagen.jpg).

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
