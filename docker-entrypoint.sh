#!/bin/bash
set -e

echo "🚀 Starting Personal Todo Agent..."
echo "Environment: ${SERVER_ENV:-main}"

# Instalar netcat si no está disponible (para el health check)
if ! command -v nc &> /dev/null; then
    echo "Installing netcat..."
    apt-get update && apt-get install -y netcat-openbsd
fi

echo "⏳ Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "✅ PostgreSQL started"

echo "⏳ Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "✅ Redis started"

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Setup complete!"

# Ejecutar el comando pasado al contenedor
exec "$@"
