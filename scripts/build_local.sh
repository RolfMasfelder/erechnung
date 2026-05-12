#!/bin/bash
# Build und starte lokale Docker Compose Umgebung
# Verwendung: ./scripts/build_local.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Versionierungs-Variablen (analog zu k3s-update-images.sh)
export APP_VERSION=$(grep '^version' "$PROJECT_ROOT/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export GIT_SHA=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "🐳 Building lokale Docker Images (v${APP_VERSION}, sha=${GIT_SHA})..."

# Frontend
echo "📦 Building Frontend..."
docker compose build frontend

# Backend
echo "📦 Building Django Backend..."
docker compose build web

# Optional: API Gateway
# docker compose build api-gateway

echo "✅ Images erfolgreich gebaut!"
echo ""
echo "🚀 Starte Services..."
docker compose up -d

echo ""
echo "✅ Services gestartet!"
echo "📍 Frontend: http://localhost:5173"
echo "📍 Backend API: http://localhost:8000"
echo "📍 Django Admin: http://localhost:8000/admin"
echo ""
echo "📊 Container Status:"
docker compose ps
