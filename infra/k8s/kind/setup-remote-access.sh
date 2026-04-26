#!/bin/bash
# Setup script for remote kubectl access to kind cluster
# Run this on your LOCAL machine to access the remote kind cluster
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - EDIT THESE VALUES
REMOTE_HOST="rolf@192.168.178.80"  # e.g., user@192.168.1.100
REMOTE_KIND_API_PORT="${REMOTE_KIND_API_PORT:-}"  # Will be auto-detected if empty
LOCAL_TUNNEL_PORT="6443"
CLUSTER_NAME="erechnung"
KUBECONFIG_PATH="$HOME/.kube/config-kind-erechnung"

echo -e "${BLUE}🔧 Remote kubectl Setup for kind cluster '${CLUSTER_NAME}'${NC}\n"

# Function to check prerequisites
check_prerequisites() {
    echo -e "${GREEN}Step 1: Checking prerequisites...${NC}"

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl is not installed${NC}"
        echo "Install: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    echo "✓ kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"

    # Check ssh
    if ! command -v ssh &> /dev/null; then
        echo -e "${RED}❌ ssh is not installed${NC}"
        exit 1
    fi
    echo "✓ ssh found"

    # Check if REMOTE_HOST is set
    if [ -z "$REMOTE_HOST" ]; then
        echo -e "${YELLOW}⚠️  REMOTE_HOST not set${NC}"
        read -p "Enter remote host (user@hostname or IP): " REMOTE_HOST
        if [ -z "$REMOTE_HOST" ]; then
            echo -e "${RED}❌ REMOTE_HOST required${NC}"
            exit 1
        fi
    fi
    echo "✓ Remote host: $REMOTE_HOST"

    # Test SSH connection
    echo "Testing SSH connection..."
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$REMOTE_HOST" "echo 'SSH OK'" &> /dev/null; then
        echo -e "${YELLOW}⚠️  SSH connection test failed (might need password/key)${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✓ SSH connection OK"
    fi
}

# Function to check remote cluster status
check_remote_cluster() {
    echo -e "\n${GREEN}Step 2: Checking remote kind cluster...${NC}"

    # Check if kind exists on remote
    if ! ssh "$REMOTE_HOST" "command -v kind" &> /dev/null; then
        echo -e "${RED}❌ kind not found on remote host${NC}"
        echo "Install kind on $REMOTE_HOST first:"
        echo "  curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64"
        echo "  chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind"
        exit 1
    fi
    echo "✓ kind found on remote host"

    # Check if cluster exists
    if ! ssh "$REMOTE_HOST" "kind get clusters 2>/dev/null | grep -q '^${CLUSTER_NAME}$'"; then
        echo -e "${YELLOW}⚠️  Cluster '${CLUSTER_NAME}' does not exist on remote host${NC}"
        echo ""
        echo "Please create the cluster first on $REMOTE_HOST:"
        echo "  cd /path/to/eRechnung_Django_App"
        echo "  ./k8s/kind/setup.sh"
        echo ""
        echo "Then run this script again."
        exit 1
    fi
    echo "✓ Cluster '$CLUSTER_NAME' exists on remote host"
}

# Function to get kubeconfig from remote
get_remote_kubeconfig() {
    echo -e "\n${GREEN}Step 3: Fetching kubeconfig from remote...${NC}"

    # Get kubeconfig
    echo "Exporting kubeconfig from remote..."
    if ! ssh "$REMOTE_HOST" "kind get kubeconfig --name ${CLUSTER_NAME}" > /tmp/kubeconfig-${CLUSTER_NAME}.tmp 2>/dev/null; then
        echo -e "${RED}❌ Failed to get kubeconfig from remote${NC}"
        exit 1
    fi

    # Extract API server port
    REMOTE_KIND_API_PORT=$(grep "server:" /tmp/kubeconfig-${CLUSTER_NAME}.tmp | sed -E 's/.*:([0-9]+).*/\1/')
    if [ -z "$REMOTE_KIND_API_PORT" ]; then
        echo -e "${RED}❌ Could not determine API server port${NC}"
        exit 1
    fi
    echo "✓ Remote API server port: $REMOTE_KIND_API_PORT"

    # Create kubeconfig directory if not exists
    mkdir -p "$(dirname "$KUBECONFIG_PATH")"

    # Modify kubeconfig to use localhost (for SSH tunnel)
    sed "s|server:.*|server: https://127.0.0.1:${LOCAL_TUNNEL_PORT}|" \
        /tmp/kubeconfig-${CLUSTER_NAME}.tmp > "$KUBECONFIG_PATH"

    chmod 600 "$KUBECONFIG_PATH"
    rm /tmp/kubeconfig-${CLUSTER_NAME}.tmp

    echo "✓ Kubeconfig saved to: $KUBECONFIG_PATH"
}

# Function to setup SSH tunnel
setup_ssh_tunnel() {
    echo -e "\n${GREEN}Step 4: Setting up SSH tunnel...${NC}"

    # Check if tunnel already exists
    if pgrep -f "ssh.*-L ${LOCAL_TUNNEL_PORT}:127.0.0.1:${REMOTE_KIND_API_PORT}.*${REMOTE_HOST}" > /dev/null; then
        echo -e "${YELLOW}⚠️  SSH tunnel already exists${NC}"
        read -p "Kill existing tunnel and create new one? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pkill -f "ssh.*-L ${LOCAL_TUNNEL_PORT}:127.0.0.1:${REMOTE_KIND_API_PORT}.*${REMOTE_HOST}"
            sleep 2
        else
            echo "Using existing tunnel"
            return 0
        fi
    fi

    # Create SSH tunnel
    echo "Creating SSH tunnel: localhost:${LOCAL_TUNNEL_PORT} -> ${REMOTE_HOST}:${REMOTE_KIND_API_PORT}"
    ssh -f -N -L "${LOCAL_TUNNEL_PORT}:127.0.0.1:${REMOTE_KIND_API_PORT}" "$REMOTE_HOST"

    # Wait a moment for tunnel to establish
    sleep 2

    # Verify tunnel
    if ! pgrep -f "ssh.*-L ${LOCAL_TUNNEL_PORT}:127.0.0.1:${REMOTE_KIND_API_PORT}.*${REMOTE_HOST}" > /dev/null; then
        echo -e "${RED}❌ Failed to create SSH tunnel${NC}"
        echo "Try manual tunnel: ssh -L ${LOCAL_TUNNEL_PORT}:127.0.0.1:${REMOTE_KIND_API_PORT} ${REMOTE_HOST}"
        exit 1
    fi

    echo "✓ SSH tunnel created (PID: $(pgrep -f "ssh.*-L ${LOCAL_TUNNEL_PORT}:127.0.0.1:${REMOTE_KIND_API_PORT}.*${REMOTE_HOST}"))"
}

# Function to test kubectl access
test_kubectl_access() {
    echo -e "\n${GREEN}Step 5: Testing kubectl access...${NC}"

    export KUBECONFIG="$KUBECONFIG_PATH"

    echo "Testing cluster connection..."
    if ! kubectl cluster-info --request-timeout=10s &> /dev/null; then
        echo -e "${RED}❌ Cannot connect to cluster${NC}"
        echo "Debug: kubectl cluster-info"
        kubectl cluster-info
        exit 1
    fi
    echo "✓ Cluster connection OK"

    echo "Getting cluster nodes..."
    kubectl get nodes

    echo "Getting pods in erechnung namespace..."
    if kubectl get namespace erechnung &> /dev/null; then
        kubectl get pods -n erechnung
    else
        echo -e "${YELLOW}⚠️  Namespace 'erechnung' not found (cluster might be empty)${NC}"
    fi
}

# Function to show usage info
show_usage_info() {
    echo -e "\n${GREEN}✅ Setup complete!${NC}"
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}📋 Usage Instructions${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "1. Set KUBECONFIG environment variable:"
    echo -e "   ${YELLOW}export KUBECONFIG=\"$KUBECONFIG_PATH\"${NC}"
    echo ""
    echo "2. Or add to your shell profile (~/.bashrc or ~/.zshrc):"
    echo "   export KUBECONFIG=\"$KUBECONFIG_PATH\""
    echo ""
    echo "3. Test access:"
    echo "   kubectl get pods -n erechnung"
    echo "   kubectl logs -n erechnung -l app=django-web"
    echo ""
    echo "4. SSH Tunnel Management:"
    echo "   Status:  pgrep -af 'ssh.*-L ${LOCAL_TUNNEL_PORT}'"
    echo "   Stop:    pkill -f 'ssh.*-L ${LOCAL_TUNNEL_PORT}:127.0.0.1:${REMOTE_KIND_API_PORT}.*${REMOTE_HOST}'"
    echo "   Restart: $0"
    echo ""
    echo "5. Important Notes:"
    echo "   - SSH tunnel must be running for kubectl to work"
    echo "   - Tunnel runs in background (survives terminal close)"
    echo "   - Recreate tunnel after reboot or network changes"
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "SSH Tunnel Status:"
    if pgrep -f "ssh.*-L ${LOCAL_TUNNEL_PORT}:127.0.0.1:${REMOTE_KIND_API_PORT}.*${REMOTE_HOST}" > /dev/null; then
        echo -e "  ${GREEN}✓ Running (PID: $(pgrep -f "ssh.*-L ${LOCAL_TUNNEL_PORT}:127.0.0.1:${REMOTE_KIND_API_PORT}.*${REMOTE_HOST}"))${NC}"
    else
        echo -e "  ${RED}✗ Not running${NC}"
    fi
    echo ""
    echo "Current context:"
    export KUBECONFIG="$KUBECONFIG_PATH"
    kubectl config current-context
}

# Main execution
main() {
    check_prerequisites
    check_remote_cluster
    get_remote_kubeconfig
    setup_ssh_tunnel
    test_kubectl_access
    show_usage_info
}

# Run main function
main
