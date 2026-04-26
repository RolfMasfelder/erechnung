#!/bin/bash
# Check k3s cluster status and eRechnung deployment
set -e

KUBECONFIG_PATH="$HOME/.kube/config-k3s"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ ! -f "$KUBECONFIG_PATH" ]; then
    echo -e "${RED}❌ Kubeconfig not found: $KUBECONFIG_PATH${NC}"
    echo "Run: ./setup-k3s-local.sh first"
    exit 1
fi

export KUBECONFIG="$KUBECONFIG_PATH"

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      k3s Cluster Status (192.168.178.80)      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check cluster connectivity
echo -e "${BLUE}🔌 Cluster Connection:${NC}"
if kubectl cluster-info &>/dev/null; then
    echo -e "${GREEN}✅ Connected to k3s cluster${NC}"
    kubectl cluster-info
else
    echo -e "${RED}❌ Cannot connect to cluster${NC}"
    exit 1
fi
echo ""

# Check nodes
echo -e "${BLUE}🖥️  Nodes:${NC}"
kubectl get nodes -o wide
echo ""

# Check MetalLB
echo -e "${BLUE}📡 MetalLB Status:${NC}"
echo "IP Address Pool:"
kubectl get ipaddresspool -n metallb-system 2>/dev/null || echo "Not configured"
echo ""

# Check Ingress
echo -e "${BLUE}🌐 Ingress Controller:${NC}"
kubectl get svc ingress-nginx-controller -n ingress-nginx -o wide
INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
if [ -n "$INGRESS_IP" ]; then
    echo -e "${GREEN}LoadBalancer IP: $INGRESS_IP${NC}"
else
    echo -e "${YELLOW}⚠️  LoadBalancer IP pending${NC}"
fi
echo ""

# Network policies
echo -e "${BLUE}🛡️  Network Policies:${NC}"
kubectl get networkpolicy -A 2>/dev/null || echo "No NetworkPolicies found"
echo ""

# Check eRechnung namespace
echo -e "${BLUE}📦 eRechnung Deployment:${NC}"
if kubectl get namespace erechnung &>/dev/null; then
    kubectl get pods -n erechnung -o wide
    echo ""
    kubectl get svc -n erechnung
    echo ""

    # Check pod status
    NOT_READY=$(kubectl get pods -n erechnung --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
    if [ "$NOT_READY" -eq 0 ]; then
        echo -e "${GREEN}✅ All pods running${NC}"
    else
        echo -e "${YELLOW}⚠️  $NOT_READY pod(s) not ready${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  eRechnung namespace not found${NC}"
    echo "Run: kubectl apply -k infra/k8s/k3s"
fi
echo ""

# Quick validation (pod-to-pod and service routing)
echo -e "${BLUE}🧪 Quick Validation:${NC}"
API_POD=$(kubectl get pod -n erechnung -l app=api-gateway -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
FRONTEND_POD_IP=$(kubectl get pod -n erechnung -l app=frontend -o jsonpath='{.items[0].status.podIP}' 2>/dev/null)
FRONTEND_SVC_IP=$(kubectl get svc -n erechnung frontend-service -o jsonpath='{.spec.clusterIP}' 2>/dev/null)

if [ -n "$API_POD" ] && [ -n "$FRONTEND_POD_IP" ] && [ -n "$FRONTEND_SVC_IP" ]; then
    echo "Pod: $API_POD"
    echo "Frontend Pod IP: $FRONTEND_POD_IP"
    echo "Frontend Service IP: $FRONTEND_SVC_IP"

    echo "Testing service IP..."
    kubectl exec -n erechnung "$API_POD" -- wget -O- --timeout=2 http://$FRONTEND_SVC_IP 2>/dev/null | head -1 || echo "Service check failed"

    echo "Testing pod IP..."
    kubectl exec -n erechnung "$API_POD" -- wget -O- --timeout=2 http://$FRONTEND_POD_IP 2>/dev/null | head -1 || echo "Pod IP check failed"
else
    echo "Skipping validation (missing api-gateway or frontend pods/services)."
fi
echo ""

# Access info
if [ -n "$INGRESS_IP" ]; then
    echo -e "${BLUE}🌍 Access URLs:${NC}"
    echo "---------------------------------------------------"
    echo -e "Frontend:  ${GREEN}http://$INGRESS_IP${NC}"
    echo -e "API:       ${GREEN}http://$INGRESS_IP/api${NC}"
    echo -e "Admin:     ${GREEN}http://$INGRESS_IP/admin${NC}"
    echo "---------------------------------------------------"
    echo ""
    echo "Test from LAN:"
    echo "  curl http://$INGRESS_IP"
    echo ""
    echo "Add to /etc/hosts:"
    echo "  $INGRESS_IP  erechnung.local"
fi
echo ""

# Useful commands
echo -e "${BLUE}📝 Useful Commands:${NC}"
echo "View logs (Django):"
echo "  kubectl logs -n erechnung -l app=django-web --tail=50 -f"
echo ""
echo "Shell access (Django):"
echo "  kubectl exec -it -n erechnung deployment/django-web -- bash"
echo ""
echo "Restart deployment:"
echo "  kubectl rollout restart deployment/django-web -n erechnung"
echo ""
echo "Delete and redeploy:"
echo "  kubectl delete -k infra/k8s/k3s"
echo "  kubectl apply -k infra/k8s/k3s"
echo ""
