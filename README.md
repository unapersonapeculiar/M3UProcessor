# M3U Processor

Una aplicación web completa para procesar, editar y compartir listas IPTV en formato M3U.

![M3U Processor](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![MySQL](https://img.shields.io/badge/MySQL-8.0_LTS-orange)
![Docker](https://img.shields.io/badge/Docker-ready-blue)

## 🚀 Características

### Editor de Listas M3U
- **Dos modos de entrada**: Pegar texto directamente o cargar desde URL
- **Buscar y Reemplazar**: Soporte para múltiples reglas, regex y sensibilidad a mayúsculas
- **Previsualización en tiempo real** con estadísticas
- **Límite de 5MB** por lista

### Generación de Enlaces
- URLs únicas con tokens UUID
- Endpoint raw: `/raw/{token}.m3u`
- Nombres personalizados
- Opción de compartir en tablón público

### Auto-actualización
- Descarga automática desde URL de origen
- Intervalos configurables (30s - 24h)
- Presets: 5min, 15min, 30min, 1h, 3h, 6h, 12h, 24h
- Aplicación automática de reglas al actualizar

### Verificación de Fuentes
- Comprobación de disponibilidad cada 24h
- Historial de verificaciones
- Estados: OK, FAIL, UNKNOWN
- Verificación manual disponible

### Tablón Público
- Top 50 listas más populares
- Filtros por período: Total, 24h, 7d, 30d
- Indicador de estado de fuente

### Sistema de Autenticación
- Registro con aprobación manual
- "Puertas Abiertas" para registro automático
- Roles: usuario y administrador
- JWT con duración de 7 días

### Panel de Administración
- Gestión de usuarios pendientes
- Control de registro abierto/cerrado
- Estadísticas del sistema
- Gestión de usuarios y playlists

---

## 📦 Instalación

Elige el método que mejor se adapte a tu entorno:

| Método | Recomendado para | Dificultad |
|--------|------------------|------------|
| [Docker Compose](#-opción-1-docker-compose-recomendado) | Producción, VPS, NAS | Fácil |
| [Tradicional (Bare Metal)](#-opción-2-instalación-tradicional-bare-metal) | Desarrollo, control total | Media |

---

## 🐳 Opción 1: Docker Compose (Recomendado)

### Requisitos
- Docker 20.10+
- Docker Compose 2.0+

### Despliegue Rápido (3 pasos)

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/m3u-processor.git
cd m3u-processor

# 2. Configurar contraseñas (opcional pero recomendado)
cp .env.example .env
nano .env  # Cambiar SECRET_KEY y contraseñas MySQL

# 3. Iniciar
docker-compose up -d
```

**¡Listo!** Accede a:
- **WebUI**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### docker-compose.yaml personalizado

Si prefieres crear tu propio archivo en cualquier ubicación:

```yaml
services:
  m3uprocessor:
    image: ghcr.io/tu-usuario/m3uprocessor:latest
    container_name: m3uprocessor
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Madrid
      - WEBUI_PORT=3000
      - API_PORT=8000
      - MYSQL_HOST=mysql
      - MYSQL_PASSWORD=tu_password_seguro
      - SECRET_KEY=tu_clave_secreta_muy_larga
    ports:
      - "3000:3000"
      - "8000:8000"
    volumes:
      - ./config:/config
    depends_on:
      - mysql

  mysql:
    image: mysql:8.0
    container_name: m3u-mysql
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=root_password_seguro
      - MYSQL_DATABASE=m3u_processor
      - MYSQL_USER=m3u_user
      - MYSQL_PASSWORD=tu_password_seguro
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

### Configuración de Puertos Personalizados

Puedes cambiar los puertos de la WebUI y la API:

```yaml
environment:
  - WEBUI_PORT=8989    # Puerto de la interfaz web
  - API_PORT=9898      # Puerto de la API
ports:
  - "8989:8989"        # Mapear al mismo valor que WEBUI_PORT
  - "9898:9898"        # Mapear al mismo valor que API_PORT
```

### Variables de Entorno (Docker)

| Variable | Descripción | Por defecto |
|----------|-------------|-------------|
| `PUID` | User ID para permisos | `1000` |
| `PGID` | Group ID para permisos | `1000` |
| `TZ` | Zona horaria | `Europe/Madrid` |
| `WEBUI_PORT` | Puerto de la interfaz web | `3000` |
| `API_PORT` | Puerto de la API backend | `8000` |
| `SECRET_KEY` | Clave secreta para JWT | Cambiar en producción |
| `MYSQL_HOST` | Host de la base de datos | `mysql` |
| `MYSQL_PASSWORD` | Contraseña de MySQL | Cambiar en producción |

### Comandos Docker Útiles

```bash
# Iniciar en segundo plano
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f m3uprocessor

# Reiniciar
docker-compose restart

# Detener
docker-compose down

# Actualizar a nueva versión
docker-compose pull && docker-compose up -d

# Ver estado
docker-compose ps
```

---

## 🖥️ Opción 2: Instalación Tradicional (Bare Metal)

### Requisitos del Sistema

- **Sistema Operativo**: Ubuntu 20.04+, Debian 11+, o similar
- **Python**: 3.11+
- **MySQL**: 8.0+
- **Nginx**: 1.18+ (para servir el frontend)
- **RAM**: Mínimo 1GB
- **Disco**: Mínimo 1GB libre

### Paso 1: Instalar dependencias del sistema

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python y herramientas
sudo apt install -y python3.11 python3.11-venv python3-pip

# Instalar MySQL
sudo apt install -y mysql-server mysql-client

# Instalar Nginx
sudo apt install -y nginx

# Instalar dependencias de compilación (para algunas librerías Python)
sudo apt install -y build-essential libmysqlclient-dev pkg-config
```

### Paso 2: Configurar MySQL

```bash
# Iniciar y habilitar MySQL
sudo systemctl start mysql
sudo systemctl enable mysql

# Configurar MySQL (establecer contraseña root)
sudo mysql_secure_installation

# Crear base de datos y usuario
sudo mysql -u root -p
```

```sql
-- Dentro de MySQL ejecutar:
CREATE DATABASE m3u_processor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'm3u_user'@'localhost' IDENTIFIED BY 'tu_password_seguro';
GRANT ALL PRIVILEGES ON m3u_processor.* TO 'm3u_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Paso 3: Clonar y configurar el proyecto

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/m3u-processor.git
cd m3u-processor

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias Python
pip install -r backend/requirements.txt
```

### Paso 4: Configurar variables de entorno

```bash
# Crear archivo de configuración
cat > backend/.env << 'EOF'
SECRET_KEY=tu_clave_secreta_muy_larga_cambiar_en_produccion
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=m3u_user
MYSQL_PASSWORD=tu_password_seguro
MYSQL_DATABASE=m3u_processor
FRONTEND_DOMAIN=http://localhost:3000
API_DOMAIN=http://localhost:8000
EOF
```

### Paso 5: Configurar Nginx (Frontend)

```bash
# Crear configuración de Nginx
sudo nano /etc/nginx/sites-available/m3uprocessor
```

Contenido del archivo:

```nginx
server {
    listen 3000;
    server_name localhost;

    root /ruta/a/m3u-processor/frontend;
    index index.html;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Frontend
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy a la API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Proxy para archivos M3U raw
    location /raw/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Activar sitio y reiniciar Nginx
sudo ln -s /etc/nginx/sites-available/m3uprocessor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Paso 6: Crear servicio systemd (Backend)

```bash
sudo nano /etc/systemd/system/m3uprocessor.service
```

Contenido del archivo:

```ini
[Unit]
Description=M3U Processor API
After=network.target mysql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/ruta/a/m3u-processor/backend
Environment="PATH=/ruta/a/m3u-processor/venv/bin"
EnvironmentFile=/ruta/a/m3u-processor/backend/.env
ExecStart=/ruta/a/m3u-processor/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar e iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable m3uprocessor
sudo systemctl start m3uprocessor

# Verificar estado
sudo systemctl status m3uprocessor
```

### Paso 7: Verificar instalación

```bash
# Ver logs del backend
sudo journalctl -u m3uprocessor -f

# Probar API
curl http://localhost:8000/api/health

# Probar frontend
curl http://localhost:3000
```

**¡Listo!** Accede a:
- **WebUI**: http://tu-servidor:3000
- **API**: http://tu-servidor:8000
- **API Docs**: http://tu-servidor:8000/docs

### Comandos Útiles (Bare Metal)

```bash
# Reiniciar backend
sudo systemctl restart m3uprocessor

# Ver logs del backend
sudo journalctl -u m3uprocessor -f

# Reiniciar Nginx
sudo systemctl restart nginx

# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log

# Actualizar aplicación
cd /ruta/a/m3u-processor
git pull
source venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart m3uprocessor
```

### Configurar SSL con Certbot (Producción)

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtener certificado (reemplazar dominio)
sudo certbot --nginx -d tu-dominio.com

# Renovación automática (ya configurada por Certbot)
sudo certbot renew --dry-run
```

## 🔑 Credenciales por Defecto

| Campo | Valor |
|-------|-------|
| Email | admin@m3uprocessor.xyz |
| Contraseña | admin123 |

⚠️ **¡Cambia la contraseña del admin inmediatamente después del primer inicio de sesión!**

## 📁 Estructura del Proyecto

```
m3u-processor/
├── backend/
│   ├── main.py              # API FastAPI completa
│   ├── requirements.txt     # Dependencias Python
│   └── tests/               # Tests
├── frontend/
│   ├── index.html           # Página principal (editor)
│   ├── index.css            # Estilos
│   ├── script.js            # JavaScript del editor
│   ├── auth.js              # Módulo de autenticación
│   ├── login.html           # Página de login
│   ├── register.html        # Página de registro
│   ├── my-playlists.html    # Panel del usuario
│   ├── admin.html           # Panel de administración
│   └── view.html            # Vista de playlist/tablón
├── docker/
│   ├── docker-compose.yml        # Desarrollo
│   ├── docker-compose.prod.yml   # Producción
│   ├── Dockerfile.backend        # Imagen del backend
│   ├── nginx.conf.template       # Nginx desarrollo
│   ├── nginx-frontend.conf       # Nginx frontend producción
│   ├── nginx-api.conf            # Nginx API producción
│   └── .env                      # Variables de entorno
├── scripts/
│   ├── dev.sh               # Script de desarrollo
│   └── prod.sh              # Script de producción
└── README.md
```

## 🗄️ Base de Datos

### Tablas

| Tabla | Descripción |
|-------|-------------|
| `system_settings` | Configuración global (open_registration) |
| `users` | Usuarios del sistema |
| `playlists` | Playlists procesadas |
| `daily_hits` | Estadísticas de acceso diario |
| `check_history` | Historial de verificaciones |

### Esquema de Users
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_at DATETIME,
    approved_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME
);
```

## 🔌 API Endpoints

### Públicos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/process` | Previsualizar cambios |
| POST | `/api/generate` | Generar enlace |
| POST | `/api/fetch-m3u` | Cargar desde URL |
| GET | `/raw/{token}.m3u` | Obtener M3U |
| GET | `/api/playlist/{token}` | Info de playlist |
| POST | `/api/playlist/{token}/check` | Verificar fuente |
| GET | `/api/board` | Tablón público |
| GET | `/api/health` | Health check |

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/register` | Registro |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Usuario actual |
| PUT | `/api/auth/me` | Actualizar perfil |

### Usuario (requiere auth)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/my/playlists` | Mis playlists |
| PUT | `/api/my/playlists/{token}` | Editar playlist |
| DELETE | `/api/my/playlists/{token}` | Eliminar playlist |

### Admin (requiere rol admin)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/admin/stats` | Estadísticas |
| GET/PUT | `/api/admin/settings` | Configuración |
| GET | `/api/admin/users` | Lista usuarios |
| PUT | `/api/admin/users/{id}` | Editar usuario |
| POST | `/api/admin/users/{id}/approve` | Aprobar usuario |
| POST | `/api/admin/users/{id}/reject` | Rechazar usuario |
| DELETE | `/api/admin/users/{id}` | Eliminar usuario |
| GET | `/api/admin/playlists` | Lista playlists |

## 🎨 Diseño UI

- **Tema oscuro** con gradientes (slate-900 → indigo-900)
- **Efecto glass** (backdrop-blur)
- **Fuentes**: Inter para texto, JetBrains Mono para código
- **Colores de estado**: Verde (OK), Rojo (FAIL), Amarillo (Pending)
- **Toast notifications** para feedback
- **Responsive design** para móviles

## 🔧 Scripts de Utilidad

### Desarrollo
```bash
./scripts/dev.sh start    # Iniciar
./scripts/dev.sh stop     # Detener
./scripts/dev.sh restart  # Reiniciar
./scripts/dev.sh logs     # Ver logs
./scripts/dev.sh build    # Reconstruir
./scripts/dev.sh clean    # Limpiar todo
./scripts/dev.sh status   # Estado de contenedores
```

### Producción
```bash
./scripts/prod.sh start   # Iniciar
./scripts/prod.sh stop    # Detener
./scripts/prod.sh restart # Reiniciar
./scripts/prod.sh logs    # Ver logs
./scripts/prod.sh build   # Reconstruir
./scripts/prod.sh update  # Git pull + rebuild
./scripts/prod.sh backup  # Backup de MySQL
./scripts/prod.sh ssl     # Configurar Let's Encrypt
./scripts/prod.sh status  # Estado de contenedores
./scripts/prod.sh health  # Verificar servicios
```

## 🔒 Seguridad

- Contraseñas hasheadas con bcrypt
- JWT para autenticación
- CORS configurado
- Validación de entrada
- Rate limiting en endpoints sensibles
- Headers de seguridad en Nginx
- HTTPS obligatorio en producción

## 📝 Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `PORT_WEBUI` | Puerto del frontend | 3000 |
| `PORT_API` | Puerto de la API | 8000 |
| `FRONTEND_DOMAIN` | Dominio del frontend | http://localhost:3000 |
| `API_DOMAIN` | Dominio de la API | http://localhost:8000 |
| `SECRET_KEY` | Clave secreta para JWT | ⚠️ Cambiar en producción |
| `MYSQL_ROOT_PASSWORD` | Contraseña root MySQL | ⚠️ Cambiar en producción |
| `MYSQL_PASSWORD` | Contraseña usuario MySQL | ⚠️ Cambiar en producción |
| `TZ` | Zona horaria | Europe/Madrid |

## 🤝 Contribuir

1. Fork del repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- [FastAPI](https://fastapi.tiangolo.com/) - Framework web moderno para Python
- [Tailwind CSS](https://tailwindcss.com/) - Framework CSS utility-first
- [MySQL](https://www.mysql.com/) - Sistema de gestión de base de datos
- [Docker](https://www.docker.com/) - Plataforma de contenedores

---

**M3U Processor** - Hecho con ❤️ para la comunidad IPTV
