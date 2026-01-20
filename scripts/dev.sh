#!/bin/bash

# M3U Processor - Development Script
# Usage: ./scripts/dev.sh [start|stop|restart|logs|build|clean]

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

# Create .env file if it doesn't exist
setup_env() {
    if [ ! -f "$DOCKER_DIR/.env" ]; then
        print_warning ".env file not found. Creating from template..."
        cat > "$DOCKER_DIR/.env" << 'EOF'
# Development Environment
PORT_WEBUI=3000
PORT_API=8000
FRONTEND_DOMAIN=http://localhost:3000
API_DOMAIN=http://localhost:8000
SECRET_KEY=dev_secret_key_change_in_production
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_PASSWORD=m3upassword
TZ=Europe/Madrid
EOF
        print_success ".env file created"
    fi
}

# Start development environment
start() {
    check_docker
    setup_env
    
    print_status "Starting M3U Processor development environment..."
    cd "$DOCKER_DIR"
    docker compose up -d
    
    print_success "Development environment started!"
    echo ""
    echo "  Frontend: http://localhost:3000"
    echo "  API:      http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo "  Default admin credentials:"
    echo "    Email:    admin@m3uprocessor.xyz"
    echo "    Password: admin123"
    echo ""
    print_warning "Remember to change the admin password in production!"
}

# Stop development environment
stop() {
    print_status "Stopping M3U Processor development environment..."
    cd "$DOCKER_DIR"
    docker compose down
    print_success "Development environment stopped"
}

# Restart development environment
restart() {
    stop
    start
}

# Show logs
logs() {
    cd "$DOCKER_DIR"
    if [ -z "$2" ]; then
        docker compose logs -f
    else
        docker compose logs -f "$2"
    fi
}

# Build containers
build() {
    check_docker
    setup_env
    
    print_status "Building M3U Processor containers..."
    cd "$DOCKER_DIR"
    docker compose build --no-cache
    print_success "Build completed"
}

# Clean up containers, volumes, and images
clean() {
    print_warning "This will remove all containers, volumes, and images for M3U Processor."
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$DOCKER_DIR"
        docker compose down -v --rmi all
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Show status
status() {
    cd "$DOCKER_DIR"
    docker compose ps
}

# Main
case "${1:-start}" in
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
    clean)
        clean
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|build|clean|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start development environment"
        echo "  stop    - Stop development environment"
        echo "  restart - Restart development environment"
        echo "  logs    - Show logs (optional: service name)"
        echo "  build   - Build containers"
        echo "  clean   - Remove all containers, volumes, and images"
        echo "  status  - Show container status"
        exit 1
        ;;
esac
