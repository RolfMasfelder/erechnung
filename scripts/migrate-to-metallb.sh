#!/bin/bash
# MetalLB Migration Script für eRechnung kind-Cluster
# Migriert von Hostport-Setup zu produktionsnaher LoadBalancer-Konfiguration
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_KIND_DIR="$SCRIPT_DIR/../infra/k8s/kind"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   MetalLB Migration für eRechnung Cluster     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed.${NC}"
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ No Kubernetes cluster found. Is kind running?${NC}"
    exit 1
fi

# Step 1: Verify IP range
echo -e "\n${YELLOW}Step 1: IP-Bereich Konfiguration${NC}"
echo "────────────────────────────────────────────────"
echo "Aktuelle Konfiguration in metallb-config.yaml:"
grep -A 2 "addresses:" "$K8S_KIND_DIR/metallb-config.yaml" | grep -E "^\s*-\s" || true
echo ""
echo -e "${YELLOW}⚠️  WICHTIG: IP-Bereich prüfen!${NC}"
echo "   - Muss im lokalen Netzwerk sein (z.B. 192.168.178.200-210)"
echo "   - Darf NICHT vom DHCP-Server vergeben werden"
echo "   - Muss auf Router/Gateway erreichbar sein"
echo ""
read -p "IP-Bereich korrekt konfiguriert? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Bitte metallb-config.yaml anpassen und erneut starten.${NC}"
    exit 1
fi

# Step 2: Install MetalLB
echo -e "\n${GREEN}Step 2: MetalLB Installation${NC}"
echo "────────────────────────────────────────────────"

if kubectl get namespace metallb-system &> /dev/null; then
    echo -e "${YELLOW}⚠️  MetalLB namespace bereits vorhanden.${NC}"
    read -p "MetalLB neu installieren? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Lösche alte MetalLB Installation..."
        kubectl delete namespace metallb-system --wait=true || true
        sleep 5
    else
        echo "Überspringe MetalLB Installation."
    fi
fi

if ! kubectl get namespace metallb-system &> /dev/null; then
    echo "Installiere MetalLB v0.14.8..."
    kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml

    echo "⏳ Warte auf MetalLB Controller..."
    kubectl wait --namespace metallb-system \
        --for=condition=ready pod \
        --selector=app=metallb,component=controller \
        --timeout=120s || {
        echo -e "${YELLOW}⚠️  Timeout, prüfe Status...${NC}"
        kubectl get pods -n metallb-system
    }

    echo "⏳ Warte auf MetalLB Speaker..."
    kubectl wait --namespace metallb-system \
        --for=condition=ready pod \
        --selector=app=metallb,component=speaker \
        --timeout=120s || {
        echo -e "${YELLOW}⚠️  Timeout, prüfe Status...${NC}"
        kubectl get pods -n metallb-system
    }
fi

# Step 3: Configure MetalLB IP Pool
echo -e "\n${GREEN}Step 3: MetalLB IP-Pool Konfiguration${NC}"
echo "────────────────────────────────────────────────"
kubectl apply -f "$K8S_KIND_DIR/metallb-config.yaml"

echo "Warte auf IPAddressPool..."
sleep 5
kubectl get ipaddresspool -n metallb-system || true
kubectl get l2advertisement -n metallb-system || true

# Step 4: Update Ingress Controller to LoadBalancer
echo -e "\n${GREEN}Step 4: Ingress-Controller auf LoadBalancer umstellen${NC}"
echo "────────────────────────────────────────────────"

CURRENT_TYPE=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
    -o jsonpath='{.spec.type}' 2>/dev/null || echo "unknown")
echo "Aktueller Service-Type: $CURRENT_TYPE"

if [ "$CURRENT_TYPE" != "LoadBalancer" ]; then
    echo "Ändere Service-Type zu LoadBalancer..."
    kubectl patch svc ingress-nginx-controller -n ingress-nginx \
        -p '{"spec":{"type":"LoadBalancer"}}'

    echo "⏳ Warte auf IP-Zuweisung..."
    sleep 10
else
    echo "Service bereits als LoadBalancer konfiguriert."
fi

# Get LoadBalancer IP
INGRESS_IP=""
for i in {1..30}; do
    INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -n "$INGRESS_IP" ]; then
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

if [ -n "$INGRESS_IP" ]; then
    echo -e "${GREEN}✅ Ingress LoadBalancer IP: $INGRESS_IP${NC}"
else
    echo -e "${YELLOW}⚠️  LoadBalancer IP noch ausstehend (pending)${NC}"
    kubectl get svc ingress-nginx-controller -n ingress-nginx
fi

# Step 5: Optional - Update API Gateway to LoadBalancer
echo -e "\n${GREEN}Step 5: API Gateway Service-Typ (optional)${NC}"
echo "────────────────────────────────────────────────"
echo "API Gateway kann als ClusterIP (nur via Ingress) oder LoadBalancer (direkt) betrieben werden."
echo ""
read -p "API Gateway als LoadBalancer konfigurieren? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Ändere API Gateway zu LoadBalancer..."
    kubectl patch svc api-gateway-service -n erechnung \
        -p '{"spec":{"type":"LoadBalancer"}}'

    echo "⏳ Warte auf IP-Zuweisung..."
    sleep 10

    API_GW_IP=$(kubectl get svc api-gateway-service -n erechnung \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

    if [ -n "$API_GW_IP" ]; then
        echo -e "${GREEN}✅ API Gateway LoadBalancer IP: $API_GW_IP${NC}"
    else
        echo -e "${YELLOW}⚠️  LoadBalancer IP noch ausstehend${NC}"
    fi
else
    echo "API Gateway bleibt als ClusterIP (nur via Ingress erreichbar)."
fi

# Step 6: Verification
echo -e "\n${GREEN}Step 6: Verifikation${NC}"
echo "────────────────────────────────────────────────"

echo -e "\n${BLUE}MetalLB Status:${NC}"
kubectl get pods -n metallb-system

echo -e "\n${BLUE}LoadBalancer Services:${NC}"
kubectl get svc -A | grep LoadBalancer || echo "Keine LoadBalancer Services gefunden."

echo -e "\n${BLUE}IPAddressPool:${NC}"
kubectl get ipaddresspool -n metallb-system -o wide

echo -e "\n${BLUE}L2Advertisement:${NC}"
kubectl get l2advertisement -n metallb-system -o wide

# Final Summary
echo -e "\n${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Migration abgeschlossen!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""

if [ -n "$INGRESS_IP" ]; then
    echo -e "${GREEN}🌐 Zugriff über:${NC}"
    echo "   http://$INGRESS_IP"
    echo "   http://erechnung.local (nach DNS-Konfiguration)"
    echo ""
    echo -e "${YELLOW}📝 Nächste Schritte:${NC}"
    echo "   1. DNS konfigurieren: $INGRESS_IP → erechnung.local"
    echo "   2. Router: IP-Bereich 192.168.178.200-210 statisch reservieren"
    echo "   3. Test: curl http://$INGRESS_IP"
else
    echo -e "${YELLOW}⚠️  LoadBalancer IP pending - mögliche Ursachen:${NC}"
    echo "   - IP-Pool außerhalb des erreichbaren Netzwerks"
    echo "   - MetalLB L2Advertisement nicht aktiv"
    echo "   - Netzwerk-Routing-Problem"
    echo ""
    echo "Debug-Befehle:"
    echo "   kubectl logs -n metallb-system -l app=metallb,component=controller"
    echo "   kubectl logs -n metallb-system -l app=metallb,component=speaker"
fi

echo ""
echo -e "${BLUE}📚 Dokumentation: docs/METALLB_MIGRATION.md${NC}"
