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

## 📋 Requisitos

- Docker 20.10+
- Docker Compose 2.0+
- (Opcional) Git para despliegue desde repositorio

## 🛠️ Instalación

### Desarrollo Local

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/m3u-processor.git
cd m3u-processor
```

2. **Configurar variables de entorno**
```bash
cp docker/.env.example docker/.env
# Editar docker/.env si es necesario
```

3. **Iniciar el entorno de desarrollo**
```bash
chmod +x scripts/dev.sh
./scripts/dev.sh start
```

4. **Acceder a la aplicación**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Documentación API: http://localhost:8000/docs

### Producción

1. **Configurar variables de entorno**
```bash
cp docker/.env.example docker/.env
nano docker/.env  # ¡IMPORTANTE: Cambiar contraseñas!
```

2. **Configurar SSL (Let's Encrypt)**
```bash
chmod +x scripts/prod.sh
./scripts/prod.sh ssl
```

3. **Iniciar el entorno de producción**
```bash
./scripts/prod.sh start
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
