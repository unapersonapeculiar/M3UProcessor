#!/bin/bash

# M3U Processor - Production Deployment Script
# Usage: ./scripts/prod.sh [start|stop|restart|logs|build|update|backup|ssl]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_DIR/docker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Check if docker-compose.yaml has production-safe settings
check_env() {
    COMPOSE_FILE="$PROJECT_DIR/docker-compose.yaml"
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "docker-compose.yaml not found!"
        exit 1
    fi

    # Check for default passwords in docker-compose.yaml
    if grep -q "rootpassword_cambiar\|m3u_password_cambiar\|clave_secreta_para_jwt" "$COMPOSE_FILE"; then
        print_error "Please change default passwords and secrets in docker-compose.yaml before deploying to production!"
        print_status "Look for values marked with '# ⚠️ CHANGE IN PRODUCTION!'"
        exit 1
    fi
}

# Start production environment
start() {
    check_docker
    check_env
    
    print_status "Starting M3U Processor production environment..."
    cd "$DOCKER_DIR"
    docker compose -f docker-compose.prod.yml up -d
    
    print_success "Production environment started!"
    echo ""
    echo "  Frontend: https://m3uprocessor.xyz"
    echo "  API:      https://api.m3uprocessor.xyz"
    echo ""
}

# Stop production environment
stop() {
    print_status "Stopping M3U Processor production environment..."
    cd "$DOCKER_DIR"
    docker compose -f docker-compose.prod.yml down
    print_success "Production environment stopped"
}

# Restart production environment
restart() {
    stop
    start
}

# Show logs
logs() {
    cd "$DOCKER_DIR"
    if [ -z "$2" ]; then
        docker compose -f docker-compose.prod.yml logs -f
    else
        docker compose -f docker-compose.prod.yml logs -f "$2"
    fi
}

# Build and deploy
build() {
    check_docker
    check_env
    
    print_status "Building M3U Processor production containers..."
    cd "$DOCKER_DIR"
    docker compose -f docker-compose.prod.yml build --no-cache
    print_success "Build completed"
}

# Update (git pull + rebuild + restart)
update() {
    print_status "Updating M3U Processor..."
    
    cd "$PROJECT_DIR"
    
    # Pull latest changes
    print_status "Pulling latest changes..."
    git pull
    
    # Rebuild and restart
    cd "$DOCKER_DIR"
    print_status "Rebuilding containers..."
    docker compose -f docker-compose.prod.yml build
    
    print_status "Restarting services..."
    docker compose -f docker-compose.prod.yml up -d
    
    print_success "Update completed!"
}

# Backup database
backup() {
    BACKUP_DIR="$PROJECT_DIR/backups"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/m3u_processor_$TIMESTAMP.sql"

    mkdir -p "$BACKUP_DIR"

    print_status "Creating database backup..."

    # Extract MYSQL_ROOT_PASSWORD from docker-compose.yaml
    MYSQL_ROOT_PASSWORD=$(grep -oP 'MYSQL_ROOT_PASSWORD=\K[^#\s]+' "$PROJECT_DIR/docker-compose.yaml" | head -1)

    cd "$DOCKER_DIR"
    docker compose -f docker-compose.prod.yml exec -T mysql \
        mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" m3u_processor > "$BACKUP_FILE"
    
    # Compress backup
    gzip "$BACKUP_FILE"
    
    print_success "Backup created: ${BACKUP_FILE}.gz"
    
    # Clean old backups (keep last 7)
    print_status "Cleaning old backups..."
    cd "$BACKUP_DIR"
    ls -t *.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm
    
    print_success "Backup process completed"
}

# Setup SSL certificates with Let's Encrypt
ssl() {
    print_status "Setting up SSL certificates..."
    
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        print_status "Installing certbot..."
        sudo apt-get update
        sudo apt-get install -y certbot
    fi
    
    print_warning "Make sure your DNS records point to this server before continuing."
    read -p "Continue? (y/N) " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "SSL setup cancelled"
        exit 0
    fi
    
    # Get certificates
    print_status "Obtaining certificate for m3uprocessor.xyz..."
    sudo certbot certonly --standalone -d m3uprocessor.xyz -d www.m3uprocessor.xyz
    
    print_status "Obtaining certificate for api.m3uprocessor.xyz..."
    sudo certbot certonly --standalone -d api.m3uprocessor.xyz
    
    # Setup auto-renewal
    print_status "Setting up auto-renewal..."
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker compose -f $DOCKER_DIR/docker-compose.prod.yml restart nginx-frontend nginx-api") | crontab -
    
    print_success "SSL certificates installed and auto-renewal configured"
}

# Show status
status() {
    cd "$DOCKER_DIR"
    docker compose -f docker-compose.prod.yml ps
}

# Health check
health() {
    print_status "Checking service health..."
    
    # Check frontend
    if curl -s -o /dev/null -w "%{http_code}" https://m3uprocessor.xyz/health | grep -q "200"; then
        print_success "Frontend: OK"
    else
        print_error "Frontend: FAIL"
    fi
    
    # Check API
    if curl -s -o /dev/null -w "%{http_code}" https://api.m3uprocessor.xyz/api/health | grep -q "200"; then
        print_success "API: OK"
    else
        print_error "API: FAIL"
    fi
}

# Main
case "${1:-}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$@"
        ;;
    build)
        build
        ;;
    update)
        update
        ;;
    backup)
        backup
        ;;
    ssl)
        ssl
        ;;
    status)
        status
        ;;
    health)
        health
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|build|update|backup|ssl|status|health}"
        echo ""
        echo "Commands:"
        echo "  start   - Start production environment"
        echo "  stop    - Stop production environment"
        echo "  restart - Restart production environment"
        echo "  logs    - Show logs (optional: service name)"
        echo "  build   - Build production containers"
        echo "  update  - Git pull + rebuild + restart"
        echo "  backup  - Backup MySQL database"
        echo "  ssl     - Setup SSL certificates with Let's Encrypt"
        echo "  status  - Show container status"
        echo "  health  - Check service health"
        exit 1
        ;;
esac
