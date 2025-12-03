import os
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environ
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, 'config.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('DJANGO_SECRET_KEY') # Sin default: Fallará si no existe (Buena práctica)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DJANGO_DEBUG', default=True)

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=[])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Local apps
    'apps.core',
    'apps.todo_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.todo_panel.middleware.RequestLoggingMiddleware',  # Custom logging
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default=f'postgresql://{env("DB_USER", default="postgres")}:{env("DB_PASSWORD", default="postgres")}@{env("DB_HOST", default="localhost")}:{env("DB_PORT", default="5432")}/{env("DB_NAME", default="todo_agent_db")}'
    )
}

# Redis Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Si quieres tener estáticos globales (no de una app específica), crea la carpeta 'static' en la raíz
# y descomenta la siguiente línea. Por ahora, confiamos en los estáticos de cada app.
# STATICFILES_DIRS = [BASE_DIR / 'static']

# Whitenoise configuration
if DEBUG:
    # En desarrollo/staging, no usamos Manifest para evitar errores si falta collectstatic
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
else:
    # En producción, usamos Manifest para caché agresivo y versionado
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Logging Configuration
# Crear directorio de logs si no existe
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['require_debug_false'],
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.todo_panel': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'apps.todo_panel.services': {
            'handlers': ['console', 'error_file'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# ==============================================================================
# MICROSOFT OAUTH CONFIGURATION
# ==============================================================================

MICROSOFT_TENANT_ID = env('TENANT_ID', default='consumers')
MICROSOFT_SCOPES = env.list(
    'MICROSOFT_SCOPES',
    default=['user.read', 'tasks.readwrite', 'offline_access']
)
MICROSOFT_AUTHORITY = f'https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}'
MICROSOFT_DEVICE_CODE_URL = f'{MICROSOFT_AUTHORITY}/oauth2/v2.0/devicecode'
MICROSOFT_TOKEN_URL = f'{MICROSOFT_AUTHORITY}/oauth2/v2.0/token'

# ==============================================================================
# ENCRYPTION CONFIGURATION
# ==============================================================================

ENCRYPTION_SALT = env('ENCRYPTION_SALT', default=None)
if not ENCRYPTION_SALT and not DEBUG:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("ENCRYPTION_SALT must be set in production")

# ==============================================================================
# RATE LIMITING (Para implementación futura)
# ==============================================================================

RATE_LIMIT_AUTH_INITIATE = env.int('RATE_LIMIT_AUTH_INITIATE', default=10)  # por minuto
RATE_LIMIT_AUTH_CHECK = env.int('RATE_LIMIT_AUTH_CHECK', default=30)  # por minuto

# ==============================================================================
# SECURITY HEADERS (Solo en producción)
# ==============================================================================

if not DEBUG:
    # SSL/HTTPS
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Security Headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

