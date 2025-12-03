# 🎓 Personal Todo Agent - Proyecto de Estudio

## Descripción

**Personal Todo Agent** es una aplicación web Django que integra Microsoft To-Do mediante OAuth 2.0 Device Code Flow. Este proyecto ha sido diseñado siguiendo las **mejores prácticas de Ingeniería de Software** para servir como laboratorio de aprendizaje y referencia de implementación.

---

## 🎯 Objetivos del Proyecto

### 1. **Funcionalidad**
- Autenticación con Microsoft Identity Platform
- Gestión de tareas de Microsoft To-Do
- Interfaz web responsive

### 2. **Educación**
- Aplicación práctica de conceptos de Software Engineering
- Código documentado y auto-explicativo
- Mapeo de teoría a implementación real

### 3. **Calidad**
- Código production-ready
- Seguridad robusta
- Arquitectura escalable

---

## 🏗️ Arquitectura

### Stack Tecnológico

```
┌─────────────────────────────────────┐
│         Frontend (HTML/CSS/JS)      │
├─────────────────────────────────────┤
│         Django 4.2 (Python)         │
├─────────────────────────────────────┤
│    PostgreSQL 15 + Redis 7          │
├─────────────────────────────────────┤
│         Docker + Docker Compose     │
└─────────────────────────────────────┘
```

### Arquitectura de Capas

```
Views Layer (HTTP)
    ↓
Services Layer (Business Logic)
    ↓
Models Layer (Data Access)
    ↓
Database (PostgreSQL)
```

---

## ✨ Características Implementadas

### Seguridad
- ✅ OAuth 2.0 Device Code Flow
- ✅ Encryption at rest (Fernet + PBKDF2)
- ✅ Input validation
- ✅ Security headers (HSTS, CSP, etc.)
- ✅ CSRF protection
- ✅ No secrets en código

### Observabilidad
- ✅ Logging estructurado
- ✅ Request tracking middleware
- ✅ Health check endpoint
- ✅ Performance metrics

### Calidad de Código
- ✅ SOLID principles
- ✅ Design patterns
- ✅ Clean code
- ✅ DRY principle
- ✅ Documentación completa

### Performance
- ✅ Database indexing
- ✅ Redis caching
- ✅ Query optimization

### DevOps
- ✅ Containerización (Docker)
- ✅ Infrastructure as Code
- ✅ 12-Factor App methodology
- ✅ Environment separation

---

## 📚 Documentación

| Documento | Descripción |
|-----------|-------------|
| **README.md** | Este archivo - Introducción general |
| **STUDY_GUIDE.md** | Mapeo de código a conceptos de Software Engineering |
| **docs/IMPLEMENTATION_SUMMARY.md** | Resumen detallado de todas las fases implementadas |
| **docs/DEVELOPMENT_GUIDE.md** | Guía práctica de desarrollo y setup |
| **docs/API_DOCUMENTATION.md** | Referencia completa de endpoints |
| **docs/QA_QC_ANALYSIS.md** | Análisis de calidad del código |

---

## 🚀 Quick Start

### Prerrequisitos
- Docker & Docker Compose
- Git

### Instalación

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/Personal-Todo-Agent.git
cd Personal-Todo-Agent

# 2. Configurar variables de entorno
cp .env.main.example .env
# Editar .env con tus credenciales

# 3. Generar ENCRYPTION_SALT
python -c "import secrets; print(secrets.token_hex(32))"
# Copiar output a .env

# 4. Iniciar aplicación
docker-compose --env-file .env up -d

# 5. Aplicar migraciones
docker-compose --env-file .env exec web python manage.py migrate

# 6. Acceder
# http://localhost:8000
```

---

## 🧪 Verificación

### Health Check
```bash
curl http://localhost:8000/health/
# Response: {"status": "healthy", "checks": {"database": "ok", "cache": "ok"}}
```

### Logs
```bash
docker-compose --env-file .env logs -f web
```

---

---

## 📖 Guía de Estudio y Teoría

Este proyecto ha sido diseñado para acompañar tu estudio de Ingeniería de Software. Todos los conceptos teóricos, patrones de diseño y explicaciones detalladas del código se encuentran en:

👉 **[STUDY_GUIDE.md](./STUDY_GUIDE.md)**

Úsalo junto con tu material de estudio para ver la teoría aplicada en un proyecto real.

---

## 🛠️ Estructura del Proyecto

```
Personal-Todo-Agent/
├── apps/
│   ├── core/                    # User management
│   └── todo_panel/              # Main app
│       ├── services/           # Business logic
│       ├── templates/          # HTML templates
│       ├── static/             # CSS, JS, images
│       ├── models.py           # Data models
│       ├── views.py            # HTTP handlers
│       ├── validators.py       # Input validation
│       ├── middleware.py       # Request logging
│       └── health.py           # Health check
├── config/
│   ├── settings.py             # Django settings
│   └── urls.py                 # URL routing
├── logs/                        # Application logs
├── prototype/                   # Legacy code (no usar)
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Container definition
├── requirements.txt             # Python dependencies
├── .env.main.example            # Environment template
└── manage.py                    # Django CLI
```

---

## 🔒 Seguridad

### Configuración Requerida

```bash
# .env
DJANGO_SECRET_KEY=<generar-con-django>
ENCRYPTION_SALT=<generar-con-secrets>
CLIENT_ID=<azure-ad-client-id>
DB_PASSWORD=<password-seguro>
```

### Generación de Secrets

```bash
# Django Secret Key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Encryption Salt
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📊 Métricas de Calidad

### Código
- ✅ SOLID principles aplicados
- ✅ Design patterns implementados
- ✅ Clean code conventions
- ✅ Documentación completa

### Seguridad
- ✅ No secrets en código
- ✅ Encryption at rest
- ✅ Input validation
- ✅ Security headers

### Performance
- ✅ Database indexes
- ✅ Caching ready
- ✅ Query optimization

### Observabilidad
- ✅ Structured logging
- ✅ Request tracking
- ✅ Health checks
- ✅ Performance metrics

---

## 🤝 Contribución

Este es un proyecto educativo. Para contribuir:

1. Fork el repositorio
2. Crear branch (`git checkout -b feature/amazing-feature`)
3. Commit cambios (`git commit -m 'feat: Add amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Abrir Pull Request

### Convención de Commits

Seguimos **Conventional Commits**:
- `feat:` Nueva funcionalidad
- `fix:` Bug fix
- `docs:` Documentación
- `refactor:` Refactorización
- `test:` Tests

---

## 📝 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

---

## 📧 Contacto

Para preguntas o soporte:
- GitHub Issues: [Crear issue]
- Email: [Tu email]

---

## 🙏 Agradecimientos

Este proyecto fue desarrollado como parte del aprendizaje de Software Engineering, aplicando conceptos de:
- Clean Architecture
- Domain-Driven Design
- Test-Driven Development
- DevOps practices
- Security best practices

---

**Última actualización:** 2025-11-29  
**Versión:** 1.0  
**Estado:** ✅ Production-ready para estudio
