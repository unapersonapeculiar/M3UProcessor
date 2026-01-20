#!/bin/bash
set -e

# ============================================
# M3UProcessor Entrypoint Script
# LinuxServer.io style configuration
# ============================================

echo "
╔═══════════════════════════════════════════╗
║         M3UProcessor Container            ║
║       IPTV M3U Playlist Processor         ║
╚═══════════════════════════════════════════╝
"

# Default values
PUID=${PUID:-1000}
PGID=${PGID:-1000}
TZ=${TZ:-Europe/Madrid}
WEBUI_PORT=${WEBUI_PORT:-3000}
API_PORT=${API_PORT:-8000}

echo "───────────────────────────────────────────"
echo "  Configuration:"
echo "───────────────────────────────────────────"
echo "  PUID:        ${PUID}"
echo "  PGID:        ${PGID}"
echo "  TZ:          ${TZ}"
echo "  WEBUI_PORT:  ${WEBUI_PORT}"
echo "  API_PORT:    ${API_PORT}"
echo "───────────────────────────────────────────"

# Set timezone
ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime
echo ${TZ} > /etc/timezone

# Update user/group IDs if different from default
if [ "${PUID}" != "1000" ] || [ "${PGID}" != "1000" ]; then
    echo "Updating user/group IDs..."
    groupmod -o -g "${PGID}" appgroup 2>/dev/null || true
    usermod -o -u "${PUID}" appuser 2>/dev/null || true
fi

# Set ownership
chown -R appuser:appgroup /app /config /var/log/supervisor /run/nginx 2>/dev/null || true

# Export environment variables for child processes
export PUID PGID TZ WEBUI_PORT API_PORT
export FRONTEND_DOMAIN="http://localhost:${WEBUI_PORT}"
export API_DOMAIN="http://localhost:${API_PORT}"

# Generate Nginx configuration from template
echo "Generating Nginx configuration..."
envsubst '${WEBUI_PORT} ${API_PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/sites-available/default

# Generate supervisord configuration
echo "Generating Supervisor configuration..."
envsubst '${API_PORT}' < /etc/supervisor/conf.d/supervisord.conf.template > /etc/supervisor/conf.d/supervisord.conf

echo "───────────────────────────────────────────"
echo "  Starting services..."
echo "───────────────────────────────────────────"
echo "  WebUI:  http://localhost:${WEBUI_PORT}"
echo "  API:    http://localhost:${API_PORT}"
echo "  Docs:   http://localhost:${API_PORT}/docs"
echo "───────────────────────────────────────────"

# Start supervisor (manages nginx + uvicorn)
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
