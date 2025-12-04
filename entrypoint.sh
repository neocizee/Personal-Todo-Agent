#!/bin/bash

# Salir si hay errores
set -e

echo "🚀 Iniciando entrypoint para entorno: $SERVER_ENV"

# Esperar a que la DB esté lista si usamos Postgres
if [ "$DB_ENGINE" = "django.db.backends.postgresql" ]; then
    echo "⏳ Esperando a PostgreSQL en $DB_HOST:$DB_PORT..."
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done
    echo "✅ PostgreSQL iniciado"
fi

# Aplicar migraciones
echo "📦 Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

# Recolectar archivos estáticos
echo "🎨 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# Iniciar servidor según entorno
if [ "$SERVER_ENV" = "staging" ] || [ "$DJANGO_DEBUG" = "True" ]; then
    echo "🔧 Iniciando servidor en modo STAGING/DEV (0.0.0.0:8000)..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "🔥 Iniciando servidor en modo PRODUCCIÓN (Gunicorn)..."
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi
