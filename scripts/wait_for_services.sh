#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
MAX_WAIT_TIME=900  # 15 minutes total (CI environments need more time)
BASE_SLEEP=2
MAX_SLEEP=30
HEALTH_TIMEOUT=10

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Exponential backoff function
wait_with_backoff() {
    local service_name="$1"
    local check_command="$2"
    local current_sleep=$BASE_SLEEP
    local elapsed_time=0

    log "Waiting for $service_name..."

    while [ $elapsed_time -lt $MAX_WAIT_TIME ]; do
        if eval "$check_command"; then
            log "$service_name is ready!"
            return 0
        fi

        log "Waiting for $service_name... (${elapsed_time}s elapsed, sleeping ${current_sleep}s)"
        sleep $current_sleep
        elapsed_time=$((elapsed_time + current_sleep))

        # Exponential backoff with cap
        current_sleep=$((current_sleep * 2))
        if [ $current_sleep -gt $MAX_SLEEP ]; then
            current_sleep=$MAX_SLEEP
        fi
    done

    error "$service_name not ready after ${MAX_WAIT_TIME} seconds"
    return 1
}

# Check if running inside Docker
if [ "${IS_DOCKER:-}" = "true" ]; then
    log "Running inside Docker container, skipping external service checks"
    exit 0
fi

log "Starting service readiness checks..."

# Phase 1: Check Docker containers are running
log "Phase 1: Checking Docker containers..."
# For init container, check if it completed successfully (Exited 0) or is no longer needed
if docker compose -f "$PROJECT_ROOT/docker-compose.yml" --env-file "$PROJECT_ROOT/.env" ps -a init | grep -qE "(Exited \\(0\\)|exited with code 0)"; then
    log "Init container completed successfully"
elif ! docker compose -f "$PROJECT_ROOT/docker-compose.yml" --env-file "$PROJECT_ROOT/.env" ps -a init | grep -q init; then
    warn "Init container not found (may have been cleaned up)"
else
    wait_with_backoff "Init container" "docker compose -f '$PROJECT_ROOT/docker-compose.yml' --env-file '$PROJECT_ROOT/.env' ps -a init | grep -E '(Exited \\(0\\)|exited with code 0)'"
fi

wait_with_backoff "PostgreSQL container" "docker compose -f '$PROJECT_ROOT/docker-compose.yml' --env-file '$PROJECT_ROOT/.env' ps db | grep -q 'Up'"
wait_with_backoff "Redis container" "docker compose -f '$PROJECT_ROOT/docker-compose.yml' --env-file '$PROJECT_ROOT/.env' ps redis | grep -q 'Up'"

# Phase 2: Check services are responding
log "Phase 2: Checking service connectivity..."
wait_with_backoff "PostgreSQL service" "docker compose -f '$PROJECT_ROOT/docker-compose.yml' --env-file '$PROJECT_ROOT/.env' exec -T db pg_isready -h localhost -p 5432"
wait_with_backoff "Redis service" "docker compose -f '$PROJECT_ROOT/docker-compose.yml' --env-file '$PROJECT_ROOT/.env' exec -T redis redis-cli ping | grep -q 'PONG'"

# Phase 3: Check Django application health
log "Phase 3: Checking Django application..."
wait_with_backoff "Django web container" "docker compose -f '$PROJECT_ROOT/docker-compose.yml' --env-file '$PROJECT_ROOT/.env' ps web | grep -q 'Up'"

# Wait for Django to be ready to serve requests
wait_with_backoff "Django health endpoint" "timeout $HEALTH_TIMEOUT curl -sf http://localhost:8000/health/ > /dev/null 2>&1"

# Check readiness (should work now since init container ran migrations)
wait_with_backoff "Django readiness endpoint" "timeout $HEALTH_TIMEOUT curl -sf http://localhost:8000/health/readiness/ > /dev/null 2>&1"

log "All services are ready!"
log "Health check summary:"
log "  - Database: $(timeout $HEALTH_TIMEOUT curl -sf http://localhost:8000/health/detailed/ 2>/dev/null | grep -o '\"database\":[^,]*' || echo 'N/A')"
log "  - Cache: $(timeout $HEALTH_TIMEOUT curl -sf http://localhost:8000/health/detailed/ 2>/dev/null | grep -o '\"cache\":[^,]*' || echo 'N/A')"

exit 0
