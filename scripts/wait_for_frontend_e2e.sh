#!/bin/bash

# Wait for E2E Frontend to be ready (Container-based check only)
# Prüft INNERHALB des Containers ob Vite läuft

set -e

echo "⏳ Waiting for E2E Frontend to be ready..."

# Farben
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Konfiguration
MAX_ATTEMPTS=30
SLEEP_SECONDS=2
CONTAINER_NAME="erechnung_frontend_e2e"
INTERNAL_URL="http://localhost:5173"  # Port 5173 INNERHALB des Containers

# 1. Prüfen ob Container läuft
echo -n "→ Checking if container is running... "
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}FAILED${NC}"
    echo ""
    echo "Container '$CONTAINER_NAME' is not running!"
    echo "Start it with:"
    echo "  docker compose -f docker-compose.e2e.yml up -d frontend-e2e"
    exit 1
fi
echo -e "${GREEN}OK${NC}"

# 2. Auf Vite Server warten (IM Container prüfen)
echo "→ Waiting for Vite dev server inside container (${INTERNAL_URL})..."
for i in $(seq 1 $MAX_ATTEMPTS); do
    # IM Container testen (curl container-intern)
    if docker compose -f docker-compose.e2e.yml exec -T frontend-e2e curl -f -s "$INTERNAL_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready!${NC}"
        echo ""
        echo "Vite server running inside container at: $INTERNAL_URL"
        echo "Accessible from host at: http://localhost:5174"
        exit 0
    fi

    # Fortschritt anzeigen
    if [ $((i % 5)) -eq 0 ]; then
        echo "  Attempt $i/$MAX_ATTEMPTS - checking logs..."
        docker compose -f docker-compose.e2e.yml logs --tail=5 frontend-e2e | grep -E "ready in|Local:|error" || true
    else
        echo -n "."
    fi

    sleep $SLEEP_SECONDS
done

# Timeout erreicht
echo ""
echo -e "${RED}❌ Timeout waiting for frontend${NC}"
echo ""
echo "Last logs from container:"
docker compose -f docker-compose.e2e.yml logs --tail=20 frontend-e2e
echo ""
echo "Check full logs with:"
echo "  docker-compose -f docker-compose.e2e.yml logs frontend-e2e"
echo ""
echo "Or run debug script:"
echo "  ./debug_e2e.sh"

exit 1
