#!/bin/bash

# E2E Debug Script
# Diagnostiziert Frontend-Startup-Probleme und ermöglicht lokales Debugging

set -e

echo "════════════════════════════════════════════════════════════"
echo "  E2E Frontend Debugging"
echo "════════════════════════════════════════════════════════════"
echo ""

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Backend Services prüfen
echo "→ Checking backend services..."
if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}  ⚠ Backend services not running. Starting...${NC}"
    docker compose up -d
    echo "  ✓ Waiting for backend services (10s)..."
    sleep 10
else
    echo -e "${GREEN}  ✓ Backend services running${NC}"
fi

# 2. Frontend-Container Status prüfen
echo ""
echo "→ Checking frontend-e2e container status..."
if docker compose -f docker-compose.e2e.yml ps | grep -q "frontend-e2e"; then
    echo -e "${GREEN}  ✓ Container exists${NC}"
    docker compose -f docker-compose.e2e.yml ps frontend-e2e
else
    echo -e "${YELLOW}  ⚠ Container not running. Building and starting...${NC}"
    docker compose -f docker-compose.e2e.yml up -d frontend-e2e
    sleep 5
fi

# 3. Port-Bindung prüfen
echo ""
echo "→ Checking port bindings..."
docker compose -f docker-compose.e2e.yml ps | grep -E "5173|PORT"

# 4. Container-Logs anzeigen (letzte 30 Zeilen)
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Frontend Container Logs (last 30 lines)"
echo "═══════════════════════════════════════════════════════════"
docker compose -f docker-compose.e2e.yml logs --tail=30 frontend-e2e

# 5. Im Container testen ob Vite läuft
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Testing Vite server FROM INSIDE container..."
echo "═══════════════════════════════════════════════════════════"

if docker compose -f docker-compose.e2e.yml exec -T frontend-e2e curl -f http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Vite server responds on localhost:5173 (internal)${NC}"
else
    echo -e "${RED}❌ Vite server NOT responding on localhost:5173 (internal)${NC}"
    echo ""
    echo "Checking if npm dev server is running:"
    docker compose -f docker-compose.e2e.yml exec -T frontend-e2e ps aux | grep -E "node|vite"
fi

# 6. Von Host aus testen
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Testing Vite server FROM HOST..."
echo "═══════════════════════════════════════════════════════════"

if curl -f http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Vite server accessible from host on http://localhost:5173${NC}"
else
    echo -e "${RED}❌ Vite server NOT accessible from host${NC}"
fi

# 7. Netzwerk-Konfiguration prüfen
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Network Configuration"
echo "═══════════════════════════════════════════════════════════"
echo "Frontend container network:"
docker inspect erechnung_frontend_e2e --format='{{range $net, $conf := .NetworkSettings.Networks}}{{$net}}: {{$conf.IPAddress}}{{"\n"}}{{end}}' 2>/dev/null || echo "Container not found"

# 8. Anleitung für lokales Debugging
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Local Debugging Options"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Option 1: Live Logs verfolgen"
echo "  ${YELLOW}docker compose -f docker-compose.e2e.yml logs -f frontend-e2e${NC}"
echo ""
echo "Option 2: In Container Shell gehen"
echo "  ${YELLOW}docker compose -f docker-compose.e2e.yml exec frontend-e2e bash${NC}"
echo "  Dann im Container:"
echo "    - npm run dev (manuell starten)"
echo "    - curl http://localhost:5173"
echo "    - cat /app/package.json"
echo ""
echo "Option 3: Container neu starten"
echo "  ${YELLOW}docker compose -f docker-compose.e2e.yml restart frontend-e2e${NC}"
echo ""
echo "Option 4: Kompletter Rebuild"
echo "  ${YELLOW}docker compose -f docker-compose.e2e.yml down${NC}"
echo "  ${YELLOW}docker compose -f docker-compose.e2e.yml build --no-cache frontend-e2e${NC}"
echo "  ${YELLOW}docker compose -f docker-compose.e2e.yml up -d frontend-e2e${NC}"
echo ""
echo "Option 5: Playwright Tests lokal (auf Host) ausführen"
echo "  ${YELLOW}cd frontend${NC}"
echo "  ${YELLOW}npm install${NC}"
echo "  ${YELLOW}npx playwright install${NC}"
echo "  ${YELLOW}PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run test:e2e${NC}"
echo ""
echo "═══════════════════════════════════════════════════════════"
