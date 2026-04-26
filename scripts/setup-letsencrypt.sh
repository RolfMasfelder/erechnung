#!/bin/bash
# =============================================================================
# Let's Encrypt Setup für eRechnung Docker-Only Production
# =============================================================================
#
# Erstellt initiales TLS-Zertifikat via certbot (HTTP-01 Challenge).
# Voraussetzung: Domain zeigt auf diesen Server (DNS A-Record).
#
# Usage:
#   ./scripts/setup-letsencrypt.sh rechnung.example.com admin@example.com
#
# Ablauf:
#   1. Startet nginx mit HTTP-only Konfiguration (ACME Challenge)
#   2. certbot holt Zertifikat via HTTP-01
#   3. Wechselt nginx auf HTTPS-Konfiguration mit Let's Encrypt Zertifikat
#   4. Richtet automatische Erneuerung ein (certbot Container)
#
# =============================================================================

set -euo pipefail

# ─── Konfiguration ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.production.yml"
CERTBOT_DATA="$PROJECT_ROOT/certbot"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ─── Argumente prüfen ───────────────────────────────────────────────────────
if [ $# -lt 2 ]; then
    echo -e "${RED}Usage: $0 <domain> <email>${NC}"
    echo ""
    echo "Beispiel:"
    echo "  $0 rechnung.example.com admin@example.com"
    echo ""
    echo "Voraussetzung: DNS A-Record für <domain> zeigt auf diesen Server."
    exit 1
fi

DOMAIN="$1"
EMAIL="$2"

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Let's Encrypt Setup für eRechnung${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Domain: $DOMAIN"
echo "E-Mail: $EMAIL"
echo ""

# ─── Überprüfungen ──────────────────────────────────────────────────────────
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker nicht gefunden. Bitte erst installieren.${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

# ─── Schritt 1: Verzeichnisse erstellen ─────────────────────────────────────
echo -e "${YELLOW}Schritt 1: Verzeichnisse erstellen...${NC}"
mkdir -p "$CERTBOT_DATA/www"
mkdir -p "$CERTBOT_DATA/conf"
echo -e "${GREEN}✓ Verzeichnisse erstellt${NC}"

# ─── Schritt 2: Domain in .env setzen ───────────────────────────────────────
echo -e "${YELLOW}Schritt 2: Konfiguration aktualisieren...${NC}"

# LETSENCRYPT_DOMAIN in .env setzen/aktualisieren
if grep -q "^LETSENCRYPT_DOMAIN=" .env 2>/dev/null; then
    sed -i "s/^LETSENCRYPT_DOMAIN=.*/LETSENCRYPT_DOMAIN=$DOMAIN/" .env
else
    echo "LETSENCRYPT_DOMAIN=$DOMAIN" >> .env
fi

# LETSENCRYPT_EMAIL in .env setzen/aktualisieren
if grep -q "^LETSENCRYPT_EMAIL=" .env 2>/dev/null; then
    sed -i "s/^LETSENCRYPT_EMAIL=.*/LETSENCRYPT_EMAIL=$EMAIL/" .env
else
    echo "LETSENCRYPT_EMAIL=$EMAIL" >> .env
fi

# DJANGO_ENV auf production setzen
if grep -q "^DJANGO_ENV=" .env 2>/dev/null; then
    sed -i "s/^DJANGO_ENV=.*/DJANGO_ENV=production/" .env
else
    echo "DJANGO_ENV=production" >> .env
fi

# DJANGO_ALLOWED_HOSTS um Domain erweitern
if ! grep -q "$DOMAIN" .env 2>/dev/null; then
    if grep -q "^DJANGO_ALLOWED_HOSTS=" .env 2>/dev/null; then
        sed -i "s/^DJANGO_ALLOWED_HOSTS=\(.*\)/DJANGO_ALLOWED_HOSTS=\1,$DOMAIN/" .env
    else
        echo "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,$DOMAIN" >> .env
    fi
fi

echo -e "${GREEN}✓ .env aktualisiert (LETSENCRYPT_DOMAIN=$DOMAIN)${NC}"

# ─── Schritt 3: Temporäre nginx Konfiguration für ACME Challenge ────────────
echo -e "${YELLOW}Schritt 3: Temporäre HTTP-Only nginx Konfiguration...${NC}"

# Temporäre Konfiguration: Nur HTTP + ACME Challenge (noch kein Zertifikat)
cat > "$PROJECT_ROOT/infra/api-gateway/api-gateway-init-letsencrypt.conf" <<'NGINX_CONF'
# Temporäre Konfiguration: Nur HTTP für initiale Zertifikats-Ausstellung
server {
    listen 80;
    server_name _;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files $uri =404;
    }

    # Alles andere: Warte auf Zertifikat
    location / {
        return 503 '{"status": "initializing", "message": "Obtaining TLS certificate..."}';
        add_header Content-Type application/json;
    }
}
NGINX_CONF

echo -e "${GREEN}✓ Temporäre nginx Konfiguration erstellt${NC}"

# ─── Schritt 4: nginx mit HTTP-Only starten ─────────────────────────────────
echo -e "${YELLOW}Schritt 4: nginx starten (HTTP-only für ACME Challenge)...${NC}"

# Stoppe laufende Container
docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true

# Starte mit temporärer HTTP-Only Konfiguration
docker compose -f "$COMPOSE_FILE" run --rm -d \
    -v "$PROJECT_ROOT/infra/api-gateway/api-gateway-init-letsencrypt.conf:/etc/nginx/conf.d/default.conf:ro" \
    -v "$CERTBOT_DATA/www:/var/www/certbot:ro" \
    -p 80:80 \
    --name erechnung-nginx-init \
    api-gateway 2>/dev/null || \
    docker run --rm -d \
        -v "$PROJECT_ROOT/infra/api-gateway/nginx.conf:/etc/nginx/nginx.conf:ro" \
        -v "$PROJECT_ROOT/infra/api-gateway/api-gateway-init-letsencrypt.conf:/etc/nginx/conf.d/default.conf:ro" \
        -v "$CERTBOT_DATA/www:/var/www/certbot:ro" \
        -p 80:80 \
        --name erechnung-nginx-init \
        nginx:alpine

echo -e "${GREEN}✓ nginx gestartet (Port 80)${NC}"

# Kurz warten bis nginx healthy ist
sleep 3

# ─── Schritt 5: Zertifikat mit certbot holen ────────────────────────────────
echo -e "${YELLOW}Schritt 5: Zertifikat von Let's Encrypt holen...${NC}"
echo "  Domain:    $DOMAIN"
echo "  Challenge: HTTP-01"
echo ""

docker run --rm \
    -v "$CERTBOT_DATA/conf:/etc/letsencrypt" \
    -v "$CERTBOT_DATA/www:/var/www/certbot" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN"

CERTBOT_EXIT=$?

# Temporären nginx stoppen
docker stop erechnung-nginx-init 2>/dev/null || true

if [ $CERTBOT_EXIT -ne 0 ]; then
    echo -e "${RED}✗ Zertifikat konnte nicht erstellt werden!${NC}"
    echo ""
    echo "Häufige Ursachen:"
    echo "  1. DNS A-Record für $DOMAIN zeigt nicht auf diesen Server"
    echo "  2. Port 80 ist blockiert (Firewall)"
    echo "  3. Let's Encrypt Rate Limit erreicht"
    echo ""
    # Temporäre Konfiguration aufräumen
    rm -f "$PROJECT_ROOT/infra/api-gateway/api-gateway-init-letsencrypt.conf"
    exit 1
fi

echo -e "${GREEN}✓ Zertifikat erfolgreich erstellt!${NC}"

# ─── Schritt 6: Aufräumen & Production-Stack starten ────────────────────────
echo -e "${YELLOW}Schritt 6: Production-Stack mit HTTPS starten...${NC}"

# Temporäre Konfiguration entfernen
rm -f "$PROJECT_ROOT/infra/api-gateway/api-gateway-init-letsencrypt.conf"

# Starte den kompletten Production-Stack mit Let's Encrypt
docker compose -f "$COMPOSE_FILE" up -d

echo -e "${GREEN}✓ Production-Stack gestartet${NC}"

# ─── Schritt 7: Zertifikat prüfen ───────────────────────────────────────────
echo -e "${YELLOW}Schritt 7: Zertifikat prüfen...${NC}"
sleep 5

if curl -sSf "https://$DOMAIN/health" --max-time 10 -o /dev/null 2>/dev/null; then
    echo -e "${GREEN}✓ HTTPS funktioniert! https://$DOMAIN ist erreichbar${NC}"
else
    echo -e "${YELLOW}⚠ HTTPS-Check fehlgeschlagen — bitte manuell prüfen: https://$DOMAIN${NC}"
fi

# ─── Zusammenfassung ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ Let's Encrypt Setup abgeschlossen!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Zertifikat:      $CERTBOT_DATA/conf/live/$DOMAIN/"
echo "Gültigkeit:      90 Tage (automatische Erneuerung aktiv)"
echo "Erneuerung:      certbot-Container prüft alle 12 Stunden"
echo "HTTPS-URL:       https://$DOMAIN"
echo ""
echo "Zertifikat manuell erneuern:"
echo "  docker compose -f docker-compose.production.yml exec certbot certbot renew"
echo ""
echo "Zertifikat-Status prüfen:"
echo "  docker compose -f docker-compose.production.yml exec certbot certbot certificates"
echo ""
