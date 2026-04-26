#!/bin/bash

# Local Security and Quality Checks Script
# This runs the same checks as your GitHub CI locally

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🔍 Running Local Security and Quality Checks..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 1. Running Ruff (Linting + Import Sorting)${NC}"
docker compose exec web ruff check project_root/ || echo -e "${RED}❌ Ruff linting failed${NC}"

echo -e "${BLUE}📋 2. Running Ruff (Formatting Check)${NC}"
docker compose exec web ruff format --check project_root/ || echo -e "${RED}❌ Ruff formatting failed${NC}"

echo -e "${BLUE}📋 3. Running Black (Code Formatting)${NC}"
docker compose exec web black --check project_root/ || echo -e "${RED}❌ Black formatting failed${NC}"

echo -e "${BLUE}🔒 4. Running pip-audit (Python Package Vulnerabilities)${NC}"
docker compose exec web /home/appuser/.local/bin/pip-audit --format=json || echo -e "${RED}❌ pip-audit failed${NC}"

echo -e "${BLUE}� 5. Testing Docker Build${NC}"
docker build -t erechnung-test:local --target production . || echo -e "${RED}❌ Docker build failed${NC}"

echo -e "${BLUE}🧪 6. Running Django Tests${NC}"
"$SCRIPT_DIR/run_tests_docker.sh"

echo -e "${GREEN}✅ Local security and quality checks completed!${NC}"
echo -e "${BLUE}ℹ️  Note: Trivy vulnerability scanning runs automatically in GitHub CI${NC}"
