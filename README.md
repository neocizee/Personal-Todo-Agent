# Personal Todo Agent

[![Django](https://img.shields.io/badge/Django-5.1+-092E20?style=flat&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-True-blue.svg)](https://www.docker.com/)
[![Redis](https://img.shields.io/badge/Redis-True-blue.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

> Aplicación web Django para gestionar tareas de **Microsoft To Do** mediante autenticación OAuth 2.0, con almacenamiento seguro de tokens encriptados.

---

## 📋 Descripción

**Personal Todo Agent** es una aplicación web que se conecta a **Microsoft To Do** usando el flujo OAuth 2.0 Device Code para obtener, visualizar y gestionar tus listas de tareas. Los tokens de acceso se almacenan encriptados en base de datos usando PBKDF2 + Fernet.

### 🎯 Propósito

Este proyecto fue creado como **herramienta de aprendizaje** para aplicar conceptos de Ingeniería de Software:
- Arquitectura en capas (Views → Services → Models → DB)
- Patrones de diseño (Service Layer, Middleware, Decorator)
- Principios SOLID
- Seguridad (encriptación, validación, OAuth 2.0)
- Clean Code y documentación


## Características

### 🔐 Autenticación Segura
- **OAuth 2.0 Device Code Flow** (sin secretos en cliente)
- Encriptación de tokens con **PBKDF2-HMAC-SHA256** (100k iteraciones) + **Fernet**
- Renovación automática de access tokens
- Hash SHA-256 de Client IDs para identificación anónima

### 📊 Gestión de Tareas
- Visualización de listas de Microsoft To Do
- Sincronización con Microsoft Graph API
- Interfaz web responsive con Bootstrap

### 🛡️ Seguridad
- Tokens encriptados en base de datos
- Validación de inputs (UUID, Device Code)
- CSRF protection
- Security headers en producción (HSTS, XSS Filter)
- Logging estructurado con rotación de archivos

### 🏥 Monitoreo
- Health check endpoint (`/health/`)
- Request logging middleware
- Logs separados por nivel (INFO, WARNING, ERROR)



## 🏗️ Estructura del Proyecto

```
Personal-Todo-Agent/
├── config/                    # Configuración de Django
│   ├── settings.py           # Variables, seguridad, logging
│   ├── urls.py               # Rutas principales
│   ├── wsgi.py / asgi.py     # Entry points
│
├── apps/
│   ├── core/                 # App base
│   │   └── models.py         # Custom User Model
│   │
│   └── todo_panel/           # App principal
│       ├── views.py          # Login, autenticación, panel
│       ├── models.py         # MicrosoftUser (tokens encriptados)
│       ├── urls.py           # Rutas de la app
│       ├── middleware.py     # Request logging
│       ├── health.py         # Health check
│       ├── validators.py     # Validación de inputs
│       │
│       ├── services/         # Lógica de negocio
│       │   ├── microsoft_auth.py    # OAuth Device Flow
│       │   ├── encryption.py        # PBKDF2 + Fernet
│       │   └── microsoft_client.py  # Microsoft Graph API
│       │
│       └── templates/        # HTML
│           ├── base.html
│           └── todo_panel/
│               ├── login.html
│               └── index.html
│
├── docs/                     # Documentación
├── db.sqlite3                # Base de datos SQLite
├── manage.py                 # Utilidad de Django
└── .env                      # Variables de entorno (no en Git)
```


## Instalación  

### Prerrequisitos
- Docker y Docker Compose
- Cuenta de Microsoft (personal o corporativa)
- Client ID de Azure AD (ver configuración)

### 1. Clonar repositorio
```bash
git clone https://github.com/neocizee/Personal-Todo-Agent.git
cd Personal-Todo-Agent
```

### 2. Configurar variables de entorno
Copia `.env.main.example` a `.env` y configura:
```env
DJANGO_SECRET_KEY=tu-clave-secreta-aqui
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
TENANT_ID=consumers
ENCRYPTION_SALT=tu-salt-aqui
```

### 3. Iniciar la aplicación con Docker Compose
Este comando construirá las imágenes, ejecutará las migraciones de Django y levantará los servicios de Django y Redis.
```bash
docker compose up --build
```

Abre http://localhost:8000/login/

---

## ⚙️ Configuración de Azure AD

### 1. Registrar aplicación en Azure Portal
1. Ir a https://portal.azure.com
2. Azure Active Directory → App registrations → New registration
3. Nombre: "Personal Todo Agent"
4. Supported account types: "Personal Microsoft accounts only"
5. Redirect URI: No necesario (Device Code Flow)

### 2. Configurar permisos
1. API permissions → Add a permission → Microsoft Graph
2. Delegated permissions:
   - `User.Read`
   - `Tasks.ReadWrite`
   - `offline_access`
3. Grant admin consent (si es necesario)

### 3. Habilitar Device Code Flow
1. Authentication → Advanced settings
2. Allow public client flows: **Yes**

### 4. Obtener Client ID
1. Overview → Application (client) ID
2. Copiar el UUID (ej: `12345678-1234-1234-1234-123456789012`)


## 🔧 Uso

### Autenticación
1. Ir a http://127.0.0.1:8000/login/
2. Ingresar tu **Client ID** de Azure AD
3. Copiar el código de dispositivo mostrado
4. Abrir https://microsoft.com/devicelogin
5. Pegar el código y autorizar
6. Serás redirigido al panel de tareas

### Endpoints Disponibles
- `GET /` → Panel de tareas (requiere login)
- `GET /login/` → Página de login
- `GET /logout/` → Cerrar sesión
- `POST /api/auth/initiate/` → Iniciar OAuth
- `POST /api/auth/check-status/` → Verificar estado (polling)
- `GET /health/` → Health check
- `GET /admin/` → Django Admin


## 🛠️ Stack Tecnológico

### Backend
- **Framework:** Django 5.1+
- **Lenguaje:** Python 3.11+
- **Base de Datos:** SQLite (desarrollo) / PostgreSQL (producción)
- **Cache:** Redis (producción)

### Frontend
- **Templating:** Django Templates
- **Estilos:** Bootstrap 5.3
- **JavaScript:** Vanilla JS (Device Flow polling)

### Seguridad
- **Encriptación:** PBKDF2-HMAC-SHA256 + Fernet
- **OAuth:** Microsoft Identity Platform (Device Code Flow)
- **Servidor:** Gunicorn + WhiteNoise (producción)

## 🎓 Conceptos de Ingeniería de Software Aplicados

Este proyecto implementa:
- **Arquitectura en Capas:** Views → Services → Models → DB
- **Service Layer Pattern:** Lógica de negocio separada
- **SOLID Principles:** SRP, OCP, DIP
- **Design Patterns:** Singleton, Middleware, Decorator, Strategy
- **Security by Design:** Encriptación, validación, OAuth
- **12-Factor App:** Configuración externa, stateless
- **Clean Code:** DRY, nombres significativos, docstrings



## 📝 Licencia

Este proyecto está bajo una **Licencia Propietaria** para uso educativo y de aprendizaje.

Ver el archivo [LICENSE](LICENSE) para más detalles.

## Resumen de Licencia
- Se puede ver y estudiar el código
- Se puede usar como referencia de aprendizaje
- Se puede ejecutar localmente para educación
- No se puede usar comercialmente
- No se puede distribuir o vender
- No se puede crear versiones modificadas
- No se puede implementar en producción
- No se puede ofrecer como SaaS

**Para uso comercial, contacta al autor.**


## 👨‍💻 Autor [@neocizee](https://github.com/neocizee)

Este proyecto es una demostración de la aplicación de conceptos avanzados de Ingeniería de Software en un caso de uso real.

**Última actualización:** Diciembre 2025
