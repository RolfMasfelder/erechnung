#!/bin/bash
# Install Falco Runtime Security Monitoring on k3s
#
# Falco detects anomalous activity at runtime:
#   - Unexpected process execution in containers
#   - Shell spawned in container
#   - File access outside allowed paths
#   - Network connections to unexpected destinations
#   - Privilege escalation attempts
#
# Prerequisites:
#   - k3s running on remote host
#   - Helm v3 installed locally
#   - KUBECONFIG pointing to k3s cluster
#
# Usage:
#   export KUBECONFIG=~/.kube/config-k3s
#   cd scripts && ./setup-falco-k3s.sh
set -e

NAMESPACE="falco"
ERECHNUNG_NS="erechnung"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Falco Runtime Security Setup (k3s)          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Preflight ────────────────────────────────────────────────────────

echo -e "${GREEN}Step 1: Preflight checks...${NC}"

# Check KUBECONFIG
if [ -z "$KUBECONFIG" ]; then
    if [ -f "$HOME/.kube/config-k3s" ]; then
        export KUBECONFIG="$HOME/.kube/config-k3s"
        echo -e "${YELLOW}Auto-detected KUBECONFIG: $KUBECONFIG${NC}"
    else
        echo -e "${RED}❌ KUBECONFIG not set. Run: export KUBECONFIG=~/.kube/config-k3s${NC}"
        exit 1
    fi
fi

if ! kubectl cluster-info &>/dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi

# Check Helm
if ! command -v helm &>/dev/null; then
    echo -e "${YELLOW}Installing Helm...${NC}"
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

echo -e "${GREEN}✅ Prerequisites met${NC}"

# ─── Check Existing Installation ─────────────────────────────────────

if kubectl get namespace "$NAMESPACE" &>/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Falco namespace already exists.${NC}"
    read -p "Reinstall Falco? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing Falco..."
        helm uninstall falco -n "$NAMESPACE" 2>/dev/null || true
        kubectl delete namespace "$NAMESPACE" 2>/dev/null || true
        sleep 5
    else
        echo "Skipping installation."
        exit 0
    fi
fi

# ─── Add Falco Helm Repository ───────────────────────────────────────

echo -e "\n${GREEN}Step 2: Adding Falco Helm repository...${NC}"
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update
echo -e "${GREEN}✅ Helm repo added${NC}"

# ─── Create Namespace ────────────────────────────────────────────────

echo -e "\n${GREEN}Step 3: Creating Falco namespace...${NC}"
kubectl create namespace "$NAMESPACE" 2>/dev/null || true

# ─── Create Custom Rules ─────────────────────────────────────────────

echo -e "\n${GREEN}Step 4: Creating eRechnung-specific Falco rules...${NC}"

kubectl apply -f - << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: falco-custom-rules
  namespace: falco
data:
  erechnung-rules.yaml: |
    # ═══════════════════════════════════════════════════════════════
    # eRechnung Custom Falco Rules
    # Runtime security monitoring for invoice processing system
    # ═══════════════════════════════════════════════════════════════

    # ─── Shell Access Detection ───────────────────────────────────
    - rule: Shell spawned in eRechnung container
      desc: Detect any shell spawned inside an eRechnung application container
      condition: >
        spawned_process
        and container
        and k8s.ns.name = "erechnung"
        and proc.name in (bash, sh, dash, ash, zsh, csh, fish)
        and not proc.pname in (init_django.sh, start_app.sh, gunicorn, celery)
      output: >
        Shell spawned in eRechnung container
        (user=%user.name container=%container.name pod=%k8s.pod.name
        namespace=%k8s.ns.name shell=%proc.name parent=%proc.pname
        cmdline=%proc.cmdline)
      priority: WARNING
      tags: [erechnung, shell]

    # ─── Sensitive File Access ────────────────────────────────────
    - rule: Sensitive file access in eRechnung
      desc: Detect access to sensitive files (secrets, env, certificates)
      condition: >
        open_read
        and container
        and k8s.ns.name = "erechnung"
        and (fd.name startswith /run/secrets/
          or fd.name startswith /var/run/secrets/
          or fd.name endswith .key
          or fd.name endswith .pem
          or fd.name = /app/.env)
        and not proc.name in (gunicorn, python, python3, celery, nginx)
      output: >
        Sensitive file read in eRechnung
        (user=%user.name file=%fd.name container=%container.name
        pod=%k8s.pod.name process=%proc.name)
      priority: WARNING
      tags: [erechnung, filesystem]

    # ─── Unexpected Network Connections ───────────────────────────
    - rule: Unexpected outbound connection from Django
      desc: Detect outbound connections from Django to unexpected destinations
      condition: >
        outbound
        and container
        and k8s.ns.name = "erechnung"
        and container.name = "django-web"
        and not fd.sip in (rfc_1918_addresses)
        and not fd.sport in (53, 80, 443, 5432, 6379, 8000, 9090)
      output: >
        Unexpected outbound connection from Django
        (connection=%fd.name container=%container.name pod=%k8s.pod.name
        destination=%fd.sip:%fd.sport)
      priority: NOTICE
      tags: [erechnung, network]

    # ─── Database Access Anomaly ──────────────────────────────────
    - rule: Direct postgres access outside Django
      desc: Detect processes connecting to postgres that are not Django or Celery
      condition: >
        outbound
        and container
        and k8s.ns.name = "erechnung"
        and fd.sport = 5432
        and not container.name in (django-web, celery-worker)
        and not k8s.pod.name startswith "django-init"
      output: >
        Non-Django process connecting to PostgreSQL
        (process=%proc.name container=%container.name pod=%k8s.pod.name
        connection=%fd.name)
      priority: WARNING
      tags: [erechnung, database]

    # ─── Privilege Escalation ─────────────────────────────────────
    - rule: Privilege escalation in eRechnung
      desc: Detect setuid/setgid or capability changes in eRechnung namespace
      condition: >
        spawned_process
        and container
        and k8s.ns.name = "erechnung"
        and (proc.name in (su, sudo, chown, chmod)
          or (proc.name = "setns" and not proc.pname = "runc"))
      output: >
        Privilege escalation attempt in eRechnung
        (user=%user.name process=%proc.name container=%container.name
        pod=%k8s.pod.name cmdline=%proc.cmdline)
      priority: ERROR
      tags: [erechnung, privilege_escalation]

    # ─── Crypto Mining Detection ──────────────────────────────────
    - rule: Potential crypto miner in eRechnung
      desc: Detect processes that may be crypto miners
      condition: >
        spawned_process
        and container
        and k8s.ns.name = "erechnung"
        and proc.name in (xmrig, minerd, minergate, cpuminer, ccminer)
      output: >
        Potential crypto miner detected
        (process=%proc.name container=%container.name pod=%k8s.pod.name
        cmdline=%proc.cmdline)
      priority: CRITICAL
      tags: [erechnung, cryptomining]
EOF

echo -e "${GREEN}✅ Custom rules created${NC}"

# ─── Install Falco via Helm ──────────────────────────────────────────

echo -e "\n${GREEN}Step 5: Installing Falco via Helm...${NC}"

# For k3s: Use modern eBPF driver (no kernel headers needed)
helm install falco falcosecurity/falco \
    --namespace "$NAMESPACE" \
    --set falcosidekick.enabled=true \
    --set falcosidekick.webui.enabled=true \
    --set driver.kind=modern_ebpf \
    --set collectors.containerd.enabled=true \
    --set collectors.containerd.socket=/run/k3s/containerd/containerd.sock \
    --set customRules."erechnung-rules\.yaml"="$(kubectl get configmap falco-custom-rules -n falco -o jsonpath='{.data.erechnung-rules\.yaml}')" \
    --set falco.json_output=true \
    --set falco.log_stderr=true \
    --set falco.log_syslog=false \
    --set falco.priority=notice \
    --wait \
    --timeout 300s

echo -e "${GREEN}✅ Falco installed${NC}"

# ─── Verify Installation ─────────────────────────────────────────────

echo -e "\n${GREEN}Step 6: Verifying Falco installation...${NC}"

echo "Waiting for Falco pods to be ready..."
kubectl wait --for=condition=ready pod \
    --selector=app.kubernetes.io/name=falco \
    --namespace "$NAMESPACE" \
    --timeout=180s || true

echo ""
echo "Falco pods:"
kubectl get pods -n "$NAMESPACE" -o wide

echo ""
echo "Falco DaemonSet status:"
kubectl get daemonset -n "$NAMESPACE"

# Check logs for successful startup
echo ""
echo "Recent Falco logs:"
kubectl logs -n "$NAMESPACE" -l app.kubernetes.io/name=falco --tail=10 2>/dev/null || echo "(waiting for logs...)"

# ─── Create NetworkPolicy for Falco ──────────────────────────────────

echo -e "\n${GREEN}Step 7: Creating NetworkPolicy for Falco...${NC}"

kubectl apply -f - << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-falco-metrics
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: falco
  policyTypes:
  - Egress
  egress:
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  # Allow Falco to reach Falcosidekick
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: falcosidekick
    ports:
    - protocol: TCP
      port: 2801
EOF

echo -e "${GREEN}✅ NetworkPolicy created${NC}"

# ─── Summary ─────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Falco Setup Complete!                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Runtime Security Monitoring Active:${NC}"
echo "  ✅ Shell access detection in eRechnung containers"
echo "  ✅ Sensitive file access monitoring"
echo "  ✅ Unexpected network connection detection"
echo "  ✅ Database access anomaly detection"
echo "  ✅ Privilege escalation detection"
echo "  ✅ Crypto mining detection"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  # View Falco alerts"
echo "  kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=falco -f"
echo ""
echo "  # Filter for eRechnung alerts"
echo "  kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=falco | grep erechnung"
echo ""
echo "  # Falcosidekick WebUI (if enabled)"
echo "  kubectl port-forward -n $NAMESPACE svc/falco-falcosidekick-ui 2802:2802"
echo "  # Then open: http://localhost:2802"
echo ""
echo "  # Test: Trigger a shell alert"
echo "  kubectl exec -it -n erechnung deploy/django-web -- sh"
echo ""
echo -e "${GREEN}✅ Done!${NC}"
