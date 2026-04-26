#!/bin/bash

# E2E Test Setup Script
# Baut und startet die E2E-Test-Umgebung mit Playwright

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "════════════════════════════════════════════════════════════"
echo "  E2E Test Environment Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# 1. Backend Services prüfen
echo "→ Checking backend services..."
if ! docker compose ps | grep -q "Up"; then
    echo "  ⚠ Backend services not running. Starting..."
    docker compose up -d
    echo "  ✓ Waiting for services to be ready (15s)..."
    sleep 15
else
    echo "  ✓ Backend services already running"
fi

# 2. E2E Frontend Image bauen
echo ""
echo "→ Building E2E Frontend Image (Playwright + Chromium/Firefox/WebKit)..."
docker compose -f docker-compose.e2e.yml build frontend-e2e

# 3. Image Details
echo ""
echo "→ Image Information:"
docker images | grep -E "erechnung.*frontend-e2e|REPOSITORY" | head -2

# 4. Browser-Verfügbarkeit prüfen
echo ""
echo "→ Verifying Playwright Installation:"
docker run --rm erechnung_django_app-frontend-e2e:latest npx playwright --version

echo ""
echo "→ Installed Browsers:"
docker run --rm erechnung_django_app-frontend-e2e:latest ls -1 /ms-playwright/ | grep -v "^\."

# 5. Anweisungen
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✓ Setup Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🎯 EMPFOHLEN: Vollautomatischer Test-Run"
echo "  ./run_e2e_container.sh"
echo ""
echo "📋 Manueller Workflow:"
echo ""
echo "  1. Start E2E frontend container:"
echo "     docker compose -f docker-compose.e2e.yml up -d frontend-e2e"
echo ""
echo "  2. Check if Vite is ready:"
echo "     ./wait_for_frontend_e2e.sh"
echo ""
echo "  3. Run tests (inside container):"
echo "     docker compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e"
echo ""
echo "  4. View HTML report:"
echo "     docker compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e:report"
echo "     # Or: http://localhost:9323"
echo ""
echo "  5. Cleanup:"
echo "     docker compose -f docker-compose.e2e.yml down"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🔧 Debug Tools"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Status check:  ./debug_e2e.sh"
echo "  Live logs:     docker compose -f docker-compose.e2e.yml logs -f frontend-e2e"
echo "  Shell access:  docker compose -f docker-compose.e2e.yml exec frontend-e2e bash"
echo ""
echo "════════════════════════════════════════════════════════════"
