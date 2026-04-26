#!/usr/bin/env bash
# Regenerate docs/openapi.json from the running Django application.
# Uses drf-spectacular to produce OpenAPI 3.0 JSON.
#
# Usage:
#   cd scripts && ./regenerate_openapi.sh
#
# Prerequisites:
#   docker compose up -d web

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

echo "▶ Generating openapi.json (OpenAPI 3.0) inside container…"
docker compose -f "${PROJECT_DIR}/docker-compose.yml" exec web \
    python project_root/manage.py spectacular --file /tmp/openapi_generated.json --format openapi-json

echo "▶ Copying openapi.json to docs/…"
CONTAINER=$(docker compose -f "${PROJECT_DIR}/docker-compose.yml" ps -q web)
docker cp "${CONTAINER}:/tmp/openapi_generated.json" "${PROJECT_DIR}/docs/openapi.json"

PATHS=$(python3 -c "import json; d=json.load(open('${PROJECT_DIR}/docs/openapi.json')); print(len(d.get('paths', {})))")
echo "✓ docs/openapi.json updated (OpenAPI 3.0) — ${PATHS} paths"
echo ""
echo "Commit with:"
echo "  git add docs/openapi.json && git commit -m 'docs: regenerate openapi.json'"
