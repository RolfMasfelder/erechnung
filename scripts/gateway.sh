#!/bin/bash
# API Gateway Management Script for eRechnung
# Easy switching between development and production setups

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo -e "${BLUE}eRechnung API Gateway Management${NC}"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  dev          Start development environment (direct Django access)"
    echo "  prod         Start production environment (via API Gateway)"
    echo "  stop         Stop all services"
    echo "  logs         Show logs"
    echo "  test         Run tests (direct access)"
    echo "  build        Build all containers"
    echo "  status       Show running services"
    echo ""
    echo "Examples:"
    echo "  $0 dev       # Start development without API Gateway"
    echo "  $0 prod      # Start production with API Gateway"
    echo "  $0 logs api-gateway  # Show API Gateway logs"
    echo ""
}

# Resolve Docker Compose command (plugin preferred)
DOCKER_COMPOSE_CMD=()
dc() { "${DOCKER_COMPOSE_CMD[@]}" "$@"; }

check_dependencies() {
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi

    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD=(docker-compose)
    else
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        exit 1
    fi
}

start_development() {
    echo -e "${GREEN}🚀 Starting eRechnung in DEVELOPMENT mode${NC}"
    echo -e "${YELLOW}   Direct Django access on http://localhost:8000${NC}"
    echo ""

    dc -f docker-compose.dev.yml up -d

    echo ""
    echo -e "${GREEN}✅ Development environment started${NC}"
    echo -e "${BLUE}📊 API Documentation: http://localhost:8000/api/swagger/${NC}"
    echo -e "${BLUE}🔧 Admin Interface: http://localhost:8000/admin/${NC}"
    echo -e "${BLUE}💾 Database: localhost:5432 (exposed for dev tools)${NC}"
}

start_production() {
    echo -e "${GREEN}🚀 Starting eRechnung in PRODUCTION mode${NC}"
    echo -e "${YELLOW}   API Gateway access on https://localhost (Port 80 redirects to HTTPS)${NC}"
    echo ""

    # Build API Gateway if needed
    if [[ ! "$(docker images -q erechnung_api-gateway 2> /dev/null)" ]]; then
        echo -e "${BLUE}🏗️  Building API Gateway container...${NC}"
        dc -f docker-compose.production.yml build api-gateway
    fi
    dc -f docker-compose.production.yml up -d

    echo ""
    echo -e "${GREEN}✅ Production environment started${NC}"
    echo -e "${BLUE}🌐 API Gateway: https://localhost${NC}"
    echo -e "${BLUE}📊 API Documentation: https://localhost/api/swagger/${NC}"
    echo -e "${BLUE}🔧 Admin Interface: https://localhost/admin/${NC}"
    echo -e "${BLUE}📈 Gateway Health: https://localhost/health${NC}"
}

stop_services() {
    echo -e "${YELLOW}🛑 Stopping all eRechnung services${NC}"

    # Stop both dev and prod environments
    dc -f docker-compose.dev.yml down 2>/dev/null || true
    dc -f docker-compose.production.yml down 2>/dev/null || true

    echo -e "${GREEN}✅ All services stopped${NC}"
}

show_logs() {
    local service=${1:-""}

    if [[ -z "$service" ]]; then
        echo -e "${BLUE}Available services:${NC}"
        echo "  Development:"
        echo "    - web (Django application)"
        echo "    - db (PostgreSQL 17)"
        echo "    - redis (Redis cache)"
        echo "  Production:"
        echo "    - api-gateway (API Gateway)"
        echo "    - django_app (Django backend)"
        echo "    - db (PostgreSQL 17)"
        echo "    - redis (Redis cache)"
        echo "    - celery (Background tasks)"
        echo ""
        echo "Usage: $0 logs [service_name]"
        return
    fi

    # Try production first, then dev
    if dc -f docker-compose.production.yml logs "$service" 2>/dev/null; then
        return
    fi

    if dc -f docker-compose.dev.yml logs "$service" 2>/dev/null; then
        return
    fi

    echo -e "${RED}Service '$service' not found or not running${NC}"
}

run_tests() {
    echo -e "${GREEN}🧪 Running tests (development environment)${NC}"

    # Ensure dev environment is running
    dc -f docker-compose.dev.yml up -d db redis
    sleep 5

    # Run tests
    dc -f docker-compose.dev.yml exec web python project_root/manage.py test invoice_app.tests

    echo -e "${GREEN}✅ Tests completed${NC}"
}

build_containers() {
    echo -e "${GREEN}🏗️  Building all containers${NC}"

    dc -f docker-compose.dev.yml build
    dc -f docker-compose.production.yml build

    echo -e "${GREEN}✅ All containers built${NC}"
}

show_status() {
    echo -e "${BLUE}📊 eRechnung Service Status${NC}"
    echo ""

    echo -e "${YELLOW}Development Services:${NC}"
    dc -f docker-compose.dev.yml ps

    echo ""
    echo -e "${YELLOW}Production Services:${NC}"
    dc -f docker-compose.production.yml ps
}

# Main script logic
check_dependencies

case "${1:-}" in
    "dev"|"development")
        start_development
        ;;
    "prod"|"production")
        start_production
        ;;
    "stop")
        stop_services
        ;;
    "logs")
        show_logs "$2"
        ;;
    "test"|"tests")
        run_tests
        ;;
    "build")
        build_containers
        ;;
    "status")
        show_status
        ;;
    "help"|"-h"|"--help")
        usage
        ;;
    *)
        echo -e "${RED}Unknown command: ${1:-}${NC}"
        echo ""
        usage
        exit 1
        ;;
esac
