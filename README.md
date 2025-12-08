# 📝 Personal Todo Agent

[![Django](https://img.shields.io/badge/Django-4.2+-092E20?style=flat&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

> **Aplicación web Django para gestionar tareas de Microsoft To Do con autenticación OAuth 2.0, caché con Redis, exportación avanzada y controles de seguridad OWASP.**

---

## 🎯 Descripción

**Personal Todo Agent** es una aplicación web educativa que demuestra la integración de Microsoft Graph API con Django, implementando:

- ✅ **OAuth 2.0 Device Code Flow** para autenticación segura
- ✅ **Encriptación de tokens** con PBKDF2 + Fernet
- ✅ **Caché con Redis** para optimizar llamadas a la API
- ✅ **Exportación de tareas** a JSON/Markdown con adjuntos
- ✅ **Rate limiting y validación** de recursos (OWASP)
- ✅ **Dockerización completa** con mejores prácticas de seguridad
- ✅ **Frontend moderno** con Tailwind CSS
- ✅ **Arquitectura en capas** (Views → Services → Models)

### 🎓 Propósito Educativo

Este proyecto fue desarrollado como parte de mi aprendizaje en:
- Integración de APIs externas (Microsoft Graph)
- Implementación de OAuth 2.0 y seguridad web
- Arquitectura de software escalable y mantenible
- Optimización de performance con caché
- Dockerización y despliegue

---

## 🚀 Inicio Rápido

### Prerequisitos

- Docker Desktop instalado y corriendo
- Cuenta de Microsoft (personal o trabajo)
- Aplicación registrada en [Azure Portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)

### Instalación con Docker (Recomendado)

```bash
# 1. Clonar el repositorio
git clone https://github.com/neocizee/Personal-Todo-Agent.git
cd Personal-Todo-Agent

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 3. Construir y levantar servicios
docker-compose up --build -d

# 4. Acceder a la aplicación
# http://localhost:8000
```

---

## 🏗️ Arquitectura

### Stack Tecnológico

**Backend:**
- Django 4.2+ (Python 3.11)
- PostgreSQL 15 (Producción/Staging)
- SQLite (Desarrollo local)
- Redis 7 (Caché)
- Gunicorn (WSGI Server)

**Frontend:**
- Tailwind CSS 3.4
- Vanilla JavaScript (ES6+)
- Django Templates

**Infraestructura:**
- Docker & Docker Compose
- Nginx (recomendado para producción)

### Estructura del Proyecto

```
Personal-Todo-Agent/
├── apps/
│   ├── core/                   # Autenticación base
│   └── todo_panel/             # App principal
│       ├── services/           # Lógica de negocio
│       │   ├── encryption.py          # Encriptación de tokens
│       │   ├── microsoft_auth.py      # OAuth 2.0 Device Flow
│       │   ├── microsoft_client.py    # Cliente API + Caché
│       │   └── export_service.py      # Exportación con seguridad
│       ├── templates/
│       ├── models.py
│       └── views.py
├── config/                     # Configuración Django
├── static/                     # Archivos estáticos
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## ✨ Funcionalidades

### 🔐 Autenticación OAuth 2.0

1. Ingresa tu **Client ID** de Azure AD
2. Se genera un código de dispositivo (copiado automáticamente)
3. Autoriza en la ventana emergente de Microsoft
4. Tokens encriptados y almacenados de forma segura
5. Renovación automática de tokens

### 📊 Gestión de Tareas

- Visualización de listas de Microsoft To Do
- Caché inteligente con Redis (5 minutos TTL)
- Actualización automática al refrescar
- Vista detallada de tareas con:
  - Subtareas (checklist items)
  - Fechas de vencimiento y recordatorios
  - Adjuntos (imágenes, documentos, etc.)

### 📦 Exportación Avanzada

**Formatos disponibles:**
- **JSON**: Estructura completa de datos
- **Markdown**: Documento legible y formateado

**Características:**
- Exportación en formato ZIP
- Carpeta `attachments/` con todos los archivos adjuntos
- Imágenes embebidas en Markdown
- Links URL-encoded (soporta espacios y caracteres especiales)
- Formato mejorado con iconos y metadatos

**Controles de seguridad:**
- Rate limiting: 10 exportaciones/hora por usuario
- Límite de 500 tareas por exportación
- Máximo 10MB por adjunto individual
- Máximo 50MB total del ZIP
- Sanitización de nombres de archivo
- Auditoría completa en logs

---

## 🔐 Seguridad

### Características de Seguridad

**Encriptación:**
- Algoritmo: PBKDF2-HMAC-SHA256 + Fernet (AES-128)
- 100,000 iteraciones
- Tokens y Client IDs encriptados en base de datos

**OAuth 2.0:**
- Device Code Flow (sin secretos del cliente)
- Tokens de acceso y refresh encriptados
- Renovación automática de tokens

**Rate Limiting:**
- Basado en Redis (distribuido)
- Límites configurables por endpoint
- Respuesta HTTP 429 cuando se excede

**Validación de Recursos:**
- Límites de tamaño de archivos
- Validación de tipos de contenido
- Prevención de Path Traversal (CWE-22)

**Docker:**
- Usuario no privilegiado (`todoagent` UID 1000)
- Capabilities mínimas (Principle of Least Privilege)
- `no-new-privileges:true`
- Filesystem con flags de seguridad

### OWASP Top 10 2021

✅ **A01 - Broken Access Control:** `@login_required` decorators  
✅ **A04 - Insecure Design:** Límites de recursos y validación  
✅ **A05 - Security Misconfiguration:** Rate limiting configurado  
✅ **A09 - Security Logging:** Auditoría completa de exportaciones  

---

## ⚙️ Configuración

### Variables de Entorno

```env
# Django
DJANGO_SECRET_KEY=tu-secret-key-aqui
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Base de Datos
DB_ENGINE=django.db.backends.postgresql
DB_NAME=todo_agent_staging
DB_USER=postgres
DB_PASSWORD=tu-password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/1

# Microsoft OAuth
TENANT_ID=consumers
ENCRYPTION_SALT=tu-salt-aleatorio-aqui

# Límites de Exportación (Opcional)
MAX_EXPORTS_PER_HOUR=10
MAX_TASKS_PER_EXPORT=500
MAX_ATTACHMENT_SIZE=10485760  # 10MB
MAX_TOTAL_EXPORT_SIZE=52428800  # 50MB
```

### Configurar Azure AD

1. Ve a [Azure Portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Crea una nueva aplicación
3. En "Authentication" → "Mobile and desktop applications"
4. Agrega: `https://login.microsoftonline.com/common/oauth2/nativeclient`
5. En "API permissions" → "Microsoft Graph" → "Delegated permissions"
6. Agrega: `Tasks.ReadWrite`, `User.Read`
7. Copia el **Application (client) ID**

---

## 🐳 Docker

### Comandos Útiles

```bash
# Construir y levantar
docker-compose up --build -d

# Ver logs
docker-compose logs -f web

# Ejecutar migraciones
docker-compose exec web python manage.py migrate

# Detener servicios
docker-compose down
```

### Entornos

**Staging:**
```env
SERVER_ENV=staging
DJANGO_DEBUG=True
```

**Production:**
```env
SERVER_ENV=main
DJANGO_DEBUG=False
```

---

## 📊 Conceptos de Ingeniería de Software

### Patrones de Diseño

- **Service Layer Pattern** - Lógica de negocio en `services/`
- **Repository Pattern** - Abstracción de acceso a datos
- **Dependency Injection** - Via Django's DI container

### Principios SOLID

- **Single Responsibility** - Cada clase tiene una responsabilidad única
- **Open/Closed** - Extensible sin modificar código existente
- **Dependency Inversion** - Dependencias de abstracciones

### Arquitectura

- **Layered Architecture** - Views → Services → Models → DB
- **Separation of Concerns** - Lógica separada por responsabilidad
- **Cache-Aside Pattern** - Optimización con Redis

### Seguridad

- **Defense in Depth** - Múltiples capas de seguridad
- **Principle of Least Privilege** - Permisos mínimos necesarios
- **Encryption at Rest** - Datos sensibles encriptados
- **Rate Limiting** - Prevención de abuso

---

## 🤝 Contribución

Este es un proyecto personal educativo. Si deseas contribuir:

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📄 Licencia

**Licencia Propietaria** - Solo para uso educativo y de aprendizaje.

Este proyecto es de código abierto para fines educativos, pero no está permitido su uso comercial sin autorización explícita.

---

## 👤 Autor

**Manuel** - [@neocizee](https://github.com/neocizee)

**⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub!**

---

**Última actualización:** 2025-12-08
