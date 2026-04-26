#!/bin/bash

# Vollständiger E2E Test Run (100% Container-basiert)
# Startet Frontend, wartet bis bereit, führt Tests IM CONTAINER aus
# WICHTIG: Installiert NICHTS auf dem Host!

set -e

# Change to project root (docker compose needs to find docker-compose*.yml)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"

echo "════════════════════════════════════════════════════════════"
echo "  E2E Test Run (Container-Only)"
echo "════════════════════════════════════════════════════════════"
echo ""

# 1. Backend starten (falls nicht läuft)
echo "→ Checking backend..."
if ! docker compose ps | grep -q "web.*Up"; then
    echo "  Starting backend services..."
    docker compose up -d
    echo "  Waiting for backend (15s)..."
    sleep 15
else
    echo "  ✓ Backend running"
fi

# 1b. Test-Daten generieren (löscht alte Daten via --clear)
echo ""
echo "→ Generating test data..."
docker compose exec -T web python project_root/manage.py generate_test_data --clear --preset standard
echo "  ✓ Test data ready"

# 2. E2E Frontend Container starten
echo ""
echo "→ Starting E2E Frontend Container..."
docker compose -f docker-compose.e2e.yml up -d frontend-e2e

# 3. Auf Frontend warten (Check IM Container)
echo ""
"$SCRIPT_DIR/wait_for_frontend_e2e.sh"

# 4. Playwright Tests IM CONTAINER ausführen
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Running Playwright Tests (inside container)"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Test URL (internal): http://localhost:5173"
echo "Browser: Chromium (from mcr.microsoft.com/playwright)"
echo ""

# Tests im Container ausführen (BaseURL = localhost:5173 im Container)
docker compose -f docker-compose.e2e.yml exec -T frontend-e2e \
  bash -c "PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run test:e2e -- $*"

TEST_EXIT_CODE=$?

# 5. Ergebnis
echo ""
echo "════════════════════════════════════════════════════════════"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "  ✅ All E2E tests passed!"
else
    echo "  ❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi
echo "════════════════════════════════════════════════════════════"
echo ""
echo "View HTML report:"
echo "  docker compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e:report"
echo ""
echo "Or access report server: http://localhost:9323"
echo ""
echo "Cleanup:"
echo "  docker compose -f docker-compose.e2e.yml down"
echo ""

exit $TEST_EXIT_CODE
