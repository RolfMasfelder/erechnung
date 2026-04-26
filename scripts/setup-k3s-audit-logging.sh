#!/bin/bash
# Enable Kubernetes API Server Audit Logging on k3s
#
# k3s doesn't use kubeadm - audit logging is configured via
# --kube-apiserver-arg flags in the k3s systemd service.
#
# This script:
#   1. Copies the audit policy to the k3s server
#   2. Configures k3s with audit logging flags
#   3. Restarts k3s to apply changes
#
# Prerequisites:
#   - SSH access to k3s server (192.168.178.80)
#   - sudo privileges on remote host
#
# Usage:
#   cd scripts && ./setup-k3s-audit-logging.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REMOTE_HOST="${K3S_HOST:-rolf@192.168.178.80}"
AUDIT_POLICY="$PROJECT_ROOT/infra/k8s/k3s/audit-policy.yaml"
REMOTE_AUDIT_DIR="/etc/rancher/k3s/audit"
REMOTE_LOG_DIR="/var/log/kubernetes/audit"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   k3s Audit Logging Setup                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Preflight ────────────────────────────────────────────────────────

echo -e "${GREEN}Step 1: Preflight checks...${NC}"

if [ ! -f "$AUDIT_POLICY" ]; then
    echo -e "${RED}❌ Audit policy not found: $AUDIT_POLICY${NC}"
    exit 1
fi

if ! ssh -o ConnectTimeout=5 "$REMOTE_HOST" "echo 'ok'" &>/dev/null; then
    echo -e "${RED}❌ Cannot connect to $REMOTE_HOST${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites met${NC}"

# ─── Copy Audit Policy ───────────────────────────────────────────────

echo -e "\n${GREEN}Step 2: Copying audit policy to k3s server...${NC}"

ssh "$REMOTE_HOST" "sudo mkdir -p $REMOTE_AUDIT_DIR && sudo mkdir -p $REMOTE_LOG_DIR"
scp "$AUDIT_POLICY" "$REMOTE_HOST:/tmp/audit-policy.yaml"
ssh "$REMOTE_HOST" "sudo mv /tmp/audit-policy.yaml $REMOTE_AUDIT_DIR/audit-policy.yaml && sudo chmod 644 $REMOTE_AUDIT_DIR/audit-policy.yaml"

echo -e "${GREEN}✅ Audit policy deployed to $REMOTE_AUDIT_DIR/audit-policy.yaml${NC}"

# ─── Check Current k3s Configuration ─────────────────────────────────

echo -e "\n${GREEN}Step 3: Checking current k3s configuration...${NC}"

ALREADY_CONFIGURED=$(ssh "$REMOTE_HOST" "sudo grep -c 'audit-policy-file' /etc/systemd/system/k3s.service 2>/dev/null || echo 0")

if [ "$ALREADY_CONFIGURED" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Audit logging already configured in k3s service${NC}"
    read -p "Reconfigure? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping configuration."
        exit 0
    fi
fi

# ─── Configure k3s with Audit Logging ────────────────────────────────

echo -e "\n${GREEN}Step 4: Configuring k3s audit logging...${NC}"

# k3s uses a config file approach (preferred over editing systemd unit)
ssh "$REMOTE_HOST" << 'REMOTE_EOF'
    # Create/update k3s config with audit logging
    # k3s reads /etc/rancher/k3s/config.yaml on startup
    CONFIG_FILE="/etc/rancher/k3s/config.yaml"

    # Check if config.yaml exists
    if [ -f "$CONFIG_FILE" ]; then
        # Check if audit args already present
        if sudo grep -q "audit-policy-file" "$CONFIG_FILE" 2>/dev/null; then
            echo "Audit logging already in config.yaml - updating..."
            # Remove old audit args
            sudo sed -i '/audit-policy-file/d; /audit-log-path/d; /audit-log-maxage/d; /audit-log-maxbackup/d; /audit-log-maxsize/d' "$CONFIG_FILE"
        fi
    fi

    # Append kube-apiserver-arg entries for audit logging
    sudo tee -a "$CONFIG_FILE" > /dev/null << 'CONF_EOF'

# Kubernetes API Server Audit Logging (Phase 2 Security)
kube-apiserver-arg:
  - "audit-policy-file=/etc/rancher/k3s/audit/audit-policy.yaml"
  - "audit-log-path=/var/log/kubernetes/audit/audit.log"
  - "audit-log-maxage=30"
  - "audit-log-maxbackup=10"
  - "audit-log-maxsize=100"
CONF_EOF

    echo "✅ k3s config updated"
REMOTE_EOF

echo -e "${GREEN}✅ Audit logging configured${NC}"

# ─── Restart k3s ─────────────────────────────────────────────────────

echo -e "\n${GREEN}Step 5: Restarting k3s to apply audit logging...${NC}"
echo -e "${YELLOW}⚠️  This will briefly interrupt the cluster!${NC}"

read -p "Restart k3s now? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    ssh "$REMOTE_HOST" "sudo systemctl restart k3s"

    echo "⏳ Waiting for k3s to be ready..."
    sleep 15

    # Verify k3s is running
    if ssh "$REMOTE_HOST" "sudo k3s kubectl get nodes --no-headers 2>/dev/null | grep -q 'Ready'"; then
        echo -e "${GREEN}✅ k3s restarted successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  k3s may still be starting up...${NC}"
        sleep 15
        ssh "$REMOTE_HOST" "sudo k3s kubectl get nodes" || true
    fi

    # Verify audit logging is active
    echo -e "\n${GREEN}Step 6: Verifying audit logging...${NC}"

    AUDIT_LOG_EXISTS=$(ssh "$REMOTE_HOST" "sudo test -f /var/log/kubernetes/audit/audit.log && echo 'yes' || echo 'no'")

    if [ "$AUDIT_LOG_EXISTS" = "yes" ]; then
        echo -e "${GREEN}✅ Audit log file created${NC}"

        # Show a few recent entries
        echo ""
        echo "Recent audit entries:"
        ssh "$REMOTE_HOST" "sudo tail -5 /var/log/kubernetes/audit/audit.log 2>/dev/null | jq -r '.verb + \" \" + .objectRef.resource + \"/\" + (.objectRef.name // \"*\") + \" by \" + .user.username' 2>/dev/null || sudo tail -3 /var/log/kubernetes/audit/audit.log" || true
    else
        echo -e "${YELLOW}⚠️  Audit log not yet created (may need a few seconds)${NC}"
    fi
else
    echo -e "${YELLOW}Skipping restart. Run manually: ssh $REMOTE_HOST 'sudo systemctl restart k3s'${NC}"
fi

# ─── Setup Log Rotation ──────────────────────────────────────────────

echo -e "\n${GREEN}Step 7: Setting up log rotation...${NC}"

ssh "$REMOTE_HOST" << 'REMOTE_EOF'
    sudo tee /etc/logrotate.d/k3s-audit > /dev/null << 'LOGROTATE_EOF'
/var/log/kubernetes/audit/audit.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 100M
}
LOGROTATE_EOF
    echo "✅ Log rotation configured"
REMOTE_EOF

echo -e "${GREEN}✅ Log rotation configured (30 days retention)${NC}"

# ─── Summary ─────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Audit Logging Setup Complete!               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}What is being logged:${NC}"
echo "  • Secret access/modification in erechnung namespace"
echo "  • RBAC changes (roles, bindings)"
echo "  • Pod exec/attach/portforward"
echo "  • Deployment/Service/Ingress changes"
echo "  • ConfigMap modifications"
echo ""
echo -e "${BLUE}Log location:${NC}  /var/log/kubernetes/audit/audit.log"
echo -e "${BLUE}Retention:${NC}     30 days, max 100MB per file, 10 backups"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  # View recent audit events"
echo "  ssh $REMOTE_HOST 'sudo tail -20 /var/log/kubernetes/audit/audit.log | jq .'"
echo ""
echo "  # Search for secret access"
echo "  ssh $REMOTE_HOST 'sudo cat /var/log/kubernetes/audit/audit.log | jq \"select(.objectRef.resource==\\\"secrets\\\")\"'"
echo ""
echo "  # Search for exec commands"
echo "  ssh $REMOTE_HOST 'sudo cat /var/log/kubernetes/audit/audit.log | jq \"select(.objectRef.subresource==\\\"exec\\\")\"'"
echo ""
echo -e "${GREEN}✅ Done!${NC}"
