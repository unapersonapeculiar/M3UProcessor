# M3UProcessor - All-in-One Docker Image
# Similar to LinuxServer.io style images
FROM python:3.11-slim

LABEL maintainer="M3UProcessor"
LABEL description="IPTV M3U Playlist Processor - All-in-One Image"

# Environment variables with defaults
ENV PUID=1000 \
    PGID=1000 \
    TZ=Europe/Madrid \
    WEBUI_PORT=3000 \
    API_PORT=8000 \
    SECRET_KEY=change-me-in-production-very-long-secret-key \
    MYSQL_HOST=mysql \
    MYSQL_PORT=3306 \
    MYSQL_USER=m3u_user \
    MYSQL_PASSWORD=m3u_password \
    MYSQL_DATABASE=m3u_processor \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    nginx \
    supervisor \
    gettext-base \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user and directories
RUN groupadd -g ${PGID} appgroup || true && \
    useradd -u ${PUID} -g ${PGID} -m -s /bin/bash appuser || true && \
    mkdir -p /app /config /var/log/supervisor /run/nginx && \
    chown -R appuser:appgroup /app /config /var/log /run/nginx

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend/main.py /app/
COPY frontend/ /app/frontend/

# Copy configuration files
COPY docker/root/ /

# Make entrypoint executable
RUN chmod +x /entrypoint.sh && \
    chown -R appuser:appgroup /app

# Expose ports (these are the defaults, but can be overridden)
EXPOSE ${WEBUI_PORT} ${API_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${API_PORT}/api/health || exit 1

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
