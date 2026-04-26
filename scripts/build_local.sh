#!/bin/bash
# Build und starte lokale Docker Compose Umgebung
# Verwendung: ./scripts/build_local.sh

set -e

echo "🐳 Building lokale Docker Images..."

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
