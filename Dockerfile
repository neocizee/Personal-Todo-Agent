# Usar imagen base de Python oficial
FROM python:3.11-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_VERSION=18 \
    PATH="/app/node_modules/.bin:${PATH}"

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema y Node.js
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    netcat-openbsd \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario y grupo no privilegiado
RUN groupadd -r todoagent && \
    useradd -r -g todoagent -u 1000 -d /app -s /bin/bash todoagent

# Copiar archivos de dependencias primero (para cache de Docker)
COPY --chown=todoagent:todoagent requirements.txt package.json package-lock.json* ./

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar dependencias Node
RUN npm install

# Copiar el resto del código con permisos correctos
COPY --chown=todoagent:todoagent . .

# Construir CSS de Tailwind
RUN ./node_modules/.bin/tailwindcss -i ./static/css/input.css -o ./static/css/output.css --minify

# Crear directorios necesarios con permisos correctos
RUN mkdir -p /app/logs /app/staticfiles /app/media && \
    chown -R todoagent:todoagent /app/logs /app/staticfiles /app/media

# Cambiar al usuario no privilegiado
USER todoagent

# Exponer puerto
EXPOSE 8000

# Definir comando de entrada
ENTRYPOINT ["./entrypoint.sh"]
