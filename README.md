# 📝 Personal Todo Agent

[![Django](https://img.shields.io/badge/Django-4.2+-092E20?style=flat&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

> **Aplicación web Django para gestionar tareas de Microsoft To Do con autenticación OAuth 2.0 Device Code Flow, caché con Redis y frontend moderno con Tailwind CSS.**

---

## 🎯 Descripción

**Personal Todo Agent** es una aplicación web educativa que demuestra la integración de Microsoft Graph API con Django, implementando:

- ✅ **OAuth 2.0 Device Code Flow** para autenticación segura
- ✅ **Encriptación de tokens** con PBKDF2 + Fernet
- ✅ **Caché con Redis** para optimizar llamadas a la API
- ✅ **Dockerización completa** con mejores prácticas de seguridad
- ✅ **Frontend moderno** con Tailwind CSS
- ✅ **Arquitectura en capas** (Views → Services → Models)

### 🎓 Propósito Educativo

Este proyecto fue desarrollado como parte de mi aprendizaje en:
- Integración de APIs externas (Microsoft Graph)
- Implementación de OAuth 2.0
- Arquitectura de software escalable
- Seguridad en aplicaciones web
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

### Instalación Local (Desarrollo)

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt
npm install

# 3. Configurar .env
cp .env.example .env

# 4. Aplicar migraciones
python manage.py migrate

# 5. Compilar Tailwind CSS
npm run build

# 6. Iniciar servidor
python manage.py runserver
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
│       │   ├── encryption.py
│       │   ├── microsoft_auth.py
│       │   └── microsoft_client.py
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

**Docker:**
- Usuario no privilegiado (`todoagent` UID 1000)
- Capabilities mínimas (Principle of Least Privilege)
- `no-new-privileges:true`
- Filesystem con flags de seguridad

Ver [SECURITY.md](SECURITY.md) para más detalles.

---

## ⚙️ Configuración

### Variables de Entorno

Copia `.env.example` a `.env` y configura:

```env
# Entorno (staging | main)
SERVER_ENV=staging

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

# Servidor
WEB_PORT=8000
```

### Configurar Azure AD

1. Ve a [Azure Portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Crea una nueva aplicación
3. En "Authentication" → "Platform configurations" → "Mobile and desktop applications"
4. Agrega la URL de redirección: `https://login.microsoftonline.com/common/oauth2/nativeclient`
5. En "API permissions" → "Add a permission" → "Microsoft Graph" → "Delegated permissions"
6. Agrega: `Tasks.ReadWrite`, `User.Read`
7. Copia el **Application (client) ID**

---

## 📖 Uso

### Autenticación

1. Accede a `http://localhost:8000/login/`
2. Ingresa tu **Client ID** de Azure AD
3. Se mostrará un código de dispositivo
4. El código se copia automáticamente al portapapeles
5. Se abre una ventana emergente de Microsoft
6. Pega el código y autoriza la aplicación
7. Serás redirigido al dashboard

### Gestión de Tareas

- Ver listas de tareas de Microsoft To Do
- Las tareas se cachean por 5 minutos en Redis
- Actualización automática al refrescar



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

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v
```

### Entornos

**Staging:**
```env
SERVER_ENV=staging
DJANGO_DEBUG=True
```
- Servidor de desarrollo
- Debug activado
- Logs verbosos

**Production:**
```env
SERVER_ENV=main
DJANGO_DEBUG=False
```
- Gunicorn con 3 workers
- Debug desactivado
- Static files optimizados

Ver [DOCKER_GUIDE.md](DOCKER_GUIDE.md) para más información.

---

## 🧪 Testing

### Test de Redis

```bash
docker-compose exec web python test_redis.py
```

Verifica:
- Conexión a Redis
- Operaciones SET/GET/DELETE
- Incremento de contadores

### Health Check

```bash
curl http://localhost:8000/health/
```


## 🛠️ Desarrollo

### Instalar Dependencias

```bash
# Python
pip install -r requirements.txt

# Node (para Tailwind)
npm install
```

### Compilar Tailwind CSS

```bash
# Desarrollo (watch mode)
npm run dev

# Producción (minificado)
npm run build
```

### Ejecutar Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### Crear Superusuario

```bash
python manage.py createsuperuser
```

---

## 🎨 Frontend

### Tailwind CSS

El proyecto usa Tailwind CSS para el diseño:

- **Archivo fuente:** `static/css/input.css`
- **Archivo compilado:** `static/css/output.css`
- **Configuración:** `tailwind.config.js`

### Templates

- `base.html` - Template base con navbar y footer
- `login.html` - Página de login con Device Code Flow
- `index.html` - Dashboard de tareas

---

## 🔄 Flujo de Autenticación

```
1. Usuario ingresa Client ID
   ↓
2. Backend solicita Device Code a Microsoft
   ↓
3. Frontend muestra código (copiado automáticamente)
   ↓
4. Se abre popup de Microsoft
   ↓
5. Usuario pega código y autoriza
   ↓
6. Backend hace polling cada N segundos
   ↓
7. Microsoft devuelve tokens
   ↓
8. Tokens se encriptan y guardan en DB
   ↓
9. Popup se cierra automáticamente
   ↓
10. Usuario redirigido al dashboard
```

---

## 📊 Conceptos de Ingeniería de Software Aplicados

### Patrones de Diseño

- **Service Layer Pattern** - Lógica de negocio en `services/`
- **Repository Pattern** - Abstracción de acceso a datos
- **Dependency Injection** - Via Django's DI container

### Principios SOLID

- **Single Responsibility** - Cada clase tiene una responsabilidad única
- **Open/Closed** - Extensible sin modificar código existente
- **Liskov Substitution** - Interfaces consistentes
- **Interface Segregation** - Interfaces específicas
- **Dependency Inversion** - Dependencias de abstracciones

### Arquitectura

- **Layered Architecture** - Views → Services → Models → DB
- **Separation of Concerns** - Lógica separada por responsabilidad
- **DRY (Don't Repeat Yourself)** - Código reutilizable

### Seguridad

- **Defense in Depth** - Múltiples capas de seguridad
- **Principle of Least Privilege** - Permisos mínimos necesarios
- **Encryption at Rest** - Datos sensibles encriptados

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

**Última actualización:** 2025-12-04
