#!/bin/bash
# Check firewall and network configuration for kind remote access
# Run this on the REMOTE HOST

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

CLUSTER_NAME="erechnung"

echo -e "${BLUE}🔍 Checking firewall and network configuration...${NC}\n"

# Check if kind cluster exists
if ! command -v kind &> /dev/null; then
    echo -e "${RED}❌ kind not installed${NC}"
    exit 1
fi

if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${YELLOW}⚠️  Cluster '${CLUSTER_NAME}' does not exist yet${NC}"
    echo "This check can still show firewall status"
    echo ""
fi

# Get kind API server port
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    API_PORT=$(docker port ${CLUSTER_NAME}-control-plane 2>/dev/null | grep '6443/tcp' | head -n1 | cut -d: -f2)
    if [ -n "$API_PORT" ]; then
        echo -e "${GREEN}✓ Kind API server port: ${API_PORT}${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not determine API server port${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Cluster not running, cannot determine API port${NC}"
    API_PORT="<will-be-assigned>"
fi

# Check if running as root
echo -e "\n${BLUE}1. User Permissions${NC}"
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Running as root${NC}"
else
    echo "✓ Running as user: $(whoami)"
fi

# Check Docker
echo -e "\n${BLUE}2. Docker Status${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not installed${NC}"
else
    echo "✓ Docker installed"
    if docker ps &> /dev/null; then
        echo "✓ Docker daemon running"
        echo "✓ User has docker permissions"
    else
        echo -e "${RED}❌ Cannot access Docker daemon${NC}"
    fi
fi

# Check network interfaces
echo -e "\n${BLUE}3. Network Interfaces${NC}"
ip -4 addr show | grep -E "inet " | grep -v "127.0.0.1" | while read -r line; do
    IP=$(echo "$line" | awk '{print $2}' | cut -d/ -f1)
    IFACE=$(echo "$line" | awk '{print $NF}')
    echo "  $IFACE: $IP"
done

# Check firewall status
echo -e "\n${BLUE}4. Firewall Status${NC}"

# Check ufw (Ubuntu/Debian)
if command -v ufw &> /dev/null; then
    echo "• UFW (Uncomplicated Firewall):"
    if sudo ufw status | grep -q "Status: active"; then
        echo -e "  ${YELLOW}⚠️  UFW is active${NC}"
        sudo ufw status | grep -E "(Status|22/tcp)"
        echo ""
        echo "  For SSH tunnel to work, port 22 must be open (usually is)"
        echo "  Kind API server is on localhost, no firewall rule needed"
    else
        echo "  ✓ UFW is inactive or not configured"
    fi
else
    echo "  UFW not found"
fi

# Check firewalld (RHEL/CentOS/Fedora)
if command -v firewall-cmd &> /dev/null; then
    echo "• firewalld:"
    if sudo firewall-cmd --state 2>/dev/null | grep -q "running"; then
        echo -e "  ${YELLOW}⚠️  firewalld is running${NC}"
        echo "  Active zones:"
        sudo firewall-cmd --get-active-zones
        echo ""
        echo "  For SSH tunnel: port 22 must be open (check with --list-services)"
    else
        echo "  ✓ firewalld not running"
    fi
else
    echo "  firewalld not found"
fi

# Check iptables
echo -e "\n${BLUE}5. iptables Rules${NC}"
if command -v iptables &> /dev/null; then
    if sudo iptables -L -n | grep -q "Chain INPUT"; then
        INPUT_POLICY=$(sudo iptables -L INPUT -n | head -n1 | grep -oP "policy \K\w+")
        echo "  INPUT chain policy: ${INPUT_POLICY}"
        if [ "$INPUT_POLICY" = "DROP" ] || [ "$INPUT_POLICY" = "REJECT" ]; then
            echo -e "  ${YELLOW}⚠️  Restrictive INPUT policy${NC}"
            echo "  Check if SSH (port 22) is allowed:"
            sudo iptables -L INPUT -n | grep -E "(22|ssh)" | head -n3
        else
            echo "  ✓ Default ACCEPT policy"
        fi
    fi
else
    echo "  iptables not found"
fi

# Check SELinux
echo -e "\n${BLUE}6. SELinux Status${NC}"
if command -v getenforce &> /dev/null; then
    SELINUX_STATUS=$(getenforce)
    if [ "$SELINUX_STATUS" = "Enforcing" ]; then
        echo -e "  ${YELLOW}⚠️  SELinux is enforcing${NC}"
        echo "  This usually doesn't affect SSH tunnels"
    else
        echo "  ✓ SELinux: $SELINUX_STATUS"
    fi
else
    echo "  SELinux not found (or not applicable)"
fi

# Check SSH daemon
echo -e "\n${BLUE}7. SSH Server${NC}"
if systemctl is-active --quiet sshd || systemctl is-active --quiet ssh; then
    echo "  ✓ SSH server is running"
    SSH_PORT=$(ss -tlnp 2>/dev/null | grep sshd | grep -oP ':\K[0-9]+' | head -n1)
    if [ -n "$SSH_PORT" ]; then
        echo "  ✓ SSH listening on port: $SSH_PORT"
    fi
else
    echo -e "  ${RED}❌ SSH server not running${NC}"
fi

# Summary and recommendations
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📋 Summary & Recommendations${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "For remote kubectl access via SSH tunnel:"
echo ""
echo "✓ Required (minimal):"
echo "  - SSH server running on this host"
echo "  - SSH port (22) accessible from your local machine"
echo "  - Docker running with kind cluster"
echo ""
echo "✓ Kind API server runs on localhost (127.0.0.1:${API_PORT})"
echo "  → No external firewall rules needed"
echo "  → SSH tunnel provides secure access"
echo ""
echo "⚠️  If you have firewall issues:"
echo "  - Only SSH port needs to be open"
echo "  - Kind API is never exposed externally"
echo "  - All traffic goes through encrypted SSH tunnel"
echo ""
echo "Test SSH access from your local machine:"
echo "  ssh $(whoami)@$(hostname -I | awk '{print $1}') echo 'SSH OK'"
echo ""
