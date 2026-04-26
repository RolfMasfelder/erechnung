#!/bin/bash

# Start the Django application using Docker Compose with Init Container
# This script sets up the environment, starts the application with proper initialization,
# and provides helpful information for accessing it
#
# Usage:
#   ./start_app.sh          # Normal startup (production-like)
#   ./start_app.sh --dev    # Development mode with volume mounts for hot reload

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse command line arguments
DEV_MODE=false
for arg in "$@"; do
    case $arg in
        --dev)
        DEV_MODE=true
        shift
        ;;
        -h|--help)
        echo "Usage: $0 [--dev] [--help]"
        echo ""
        echo "Options:"
        echo "  --dev    Start in development mode with volume mounts for hot reload"
        echo "  --help   Show this help message"
        exit 0
        ;;
        *)
        echo "Unknown option: $arg"
        echo "Use --help for usage information"
        exit 1
        ;;
    esac
done

# Function to check if Docker and Docker Compose are installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker compose &> /dev/null; then
        echo "Error: Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# Function to check the .env file
setup_env() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo "Error: .env file not found at $PROJECT_ROOT/.env"
        echo "Please create it first: ./scripts/generate-secrets.sh"
        exit 1
    fi
    echo "Using existing .env file."

    # Check if the environment variables needed by Docker are present
    if ! grep -q "DB_NAME" "$PROJECT_ROOT/.env" || ! grep -q "DB_USER" "$PROJECT_ROOT/.env" || ! grep -q "DB_PASSWORD" "$PROJECT_ROOT/.env"; then
        echo "Warning: Your .env file may be missing required Docker variables."
        echo "Consider adding DB_NAME, DB_USER, and DB_PASSWORD to match your POSTGRES_* settings."
    fi
}

# Function to start the application
start_app() {
    echo "Starting the eRechnung application..."

    # Create necessary directories with proper permissions
    echo "Creating required directories..."
    mkdir -p "$PROJECT_ROOT/media" "$PROJECT_ROOT/static" "$PROJECT_ROOT/logs"
    chmod -R 777 "$PROJECT_ROOT/media" "$PROJECT_ROOT/static"
    # Ensure existing log files are writable by container UID 1234
    find "$PROJECT_ROOT/logs" -name "*.log" -exec chmod 666 {} \;

    # Build and start the containers
    cd "$PROJECT_ROOT"
    if [ "$DEV_MODE" = true ]; then
        echo "🚀 Starting in DEVELOPMENT mode with volume mounts for hot reload..."
        docker compose -f docker-compose.yml -f docker-compose.dev-volumes.yml --env-file "$PROJECT_ROOT/.env" up -d --build
        echo "📝 Code changes will be automatically reflected (hot reload enabled)"
    else
        echo "🚀 Starting in PRODUCTION mode..."
        docker compose --env-file "$PROJECT_ROOT/.env" up -d --build
    fi

    # Wait for services to be ready using our dedicated script
    echo "Waiting for services to be ready..."
    "$SCRIPT_DIR/wait_for_services.sh"

    echo "Note: Migrations and initial setup are now handled by the init container"
    echo "If you need to run migrations manually, use:"
    echo "  docker compose run --rm init"
    echo "  docker compose exec web python project_root/manage.py collectstatic --noinput --clear"

    echo ""
    echo "==================================================================="
    echo "eRechnung application is now running! "
    if [ "$DEV_MODE" = true ]; then
        echo "🔧 Running in DEVELOPMENT mode with hot reload"
    else
        echo "🚀 Running in PRODUCTION mode"
    fi
    echo "==================================================================="
    echo "Admin interface: http://localhost:8000/admin/"
    echo "Username: admin"
    echo "Password: adminpassword"
    echo ""
    echo "API documentation: http://localhost:8000/api/swagger/"
    echo ""
    if [ "$DEV_MODE" = true ]; then
        echo "To stop the application, run: docker compose -f docker-compose.yml -f docker-compose.dev-volumes.yml down"
    else
        echo "To stop the application, run: docker compose down"
    fi
    echo "To view logs, run: docker compose logs -f"
    echo "==================================================================="
}

# Main execution
check_docker
setup_env
start_app
