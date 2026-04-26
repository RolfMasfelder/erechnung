# MetalLB Migration für produktionsnahe Kubernetes-Konfiguration

## Problem
Die aktuelle kind-Konfiguration nutzt Hostports (`extraPortMappings`), was **nicht produktionsnah** ist:
- ❌ Hostports binden direkt an Node-Ports (80/443)
- ❌ Nicht skalierbar (funktioniert nur auf Control-Plane Node)
- ❌ Keine echte Load-Balancing-Funktionalität
- ❌ Nicht portierbar auf echte Kubernetes-Cluster

## Lösung: MetalLB als LoadBalancer

MetalLB bietet produktionsnahe Load-Balancing-Funktionalität:
- ✅ LoadBalancer Services erhalten echte externe IPs
- ✅ L2-Modus für lokales Netzwerk (Layer 2 Advertisement)
- ✅ BGP-Modus für Cloud/Enterprise-Umgebungen
- ✅ Funktioniert identisch wie Cloud-Provider LoadBalancer (AWS ELB, GCP LB)

---

## Migrations-Schritte

### 1. MetalLB konfigurieren

#### a) IP-Pool für lokales Netzwerk anpassen

**Aktuell** (`k8s/kind/metallb-config.yaml`):
```yaml
# DEPRECATED - nutzt Docker-Netzwerk (nicht erreichbar von außen)
addresses:
- 172.18.255.200-172.18.255.250
```

**Neu** - für 192.168.178.x Netzwerk:
```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: local-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.178.200-192.168.178.210  # 11 IPs für Services

---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: local-l2-advert
  namespace: metallb-system
spec:
  ipAddressPools:
  - local-pool
```

**Wichtig - kind-Limitation:**
- **kind-Cluster:** Muss Docker-Netzwerk verwenden (z.B. 172.18.255.200-210)
  - MetalLB kann in kind nur Docker-Bridge IPs vergeben
  - Für Remote-Zugriff: HostPort-Mapping (extraPortMappings) zusätzlich nutzen
- **Echtes Kubernetes:** Kann Host-LAN verwenden (z.B. 192.168.178.200-210)
  - IP-Bereich im lokalen Netzwerk sein (192.168.178.0/24)
  - NICHT vom DHCP-Server vergeben werden (statischer Bereich)
  - Auf Routern/Firewalls erreichbar sein

#### b) MetalLB-Manifeste aktualisieren

Die `metallb-native.yaml` ist veraltet. Verwendet aktuelle Version:
```bash
# MetalLB v0.14.x (aktuelle stable)
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml
```

### 2. Services auf LoadBalancer umstellen

#### Vorher (NodePort):
```yaml
# k8s/kind/api-gateway-service.yaml
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080  # High port, nicht Standard
```

#### Nachher (LoadBalancer):
```yaml
# k8s/kind/api-gateway-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
  namespace: erechnung
  labels:
    app: api-gateway
spec:
  selector:
    app: api-gateway
  type: LoadBalancer  # ← Änderung
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
  - name: https
    port: 443
    targetPort: 8443
    protocol: TCP
```

### 3. Ingress-Controller Service anpassen

Im `setup.sh` wird aktuell der Ingress-Controller auf ClusterIP gepatchet:
```bash
# ENTFERNEN (setup.sh, Zeile ~95):
kubectl patch svc ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"type":"ClusterIP"}}' || true
```

**Stattdessen:** Ingress-Controller als LoadBalancer belassen:
```bash
# setup.sh - Neuer Abschnitt nach ingress-nginx Installation:
echo -e "\n${GREEN}Configuring ingress-controller as LoadBalancer...${NC}"
kubectl patch svc ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"type":"LoadBalancer"}}'
```

### 4. kind-cluster-config anpassen - Hybrid-Modus (empfohlen)

**Für kind-Cluster: Hybrid-Setup** (MetalLB + HostPort):
```yaml
# k8s/kind/kind-cluster-config.yaml
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  # BEHALTEN: extraPortMappings für Remote-Zugriff
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
  - containerPort: 443
    hostPort: 443
```

**Warum Hybrid?**
- MetalLB nutzt Docker-Netzwerk (172.18.x.x) - nicht von außen erreichbar
- HostPort ermöglicht LAN-Zugriff (192.168.178.80:80)
- Beide Modi parallel = produktionsnahe Tests + praktischer Zugriff

### 5. setup.sh erweitern

```bash
# Nach Step 2 (nginx-ingress installation):

# Step 2.5: Install MetalLB
echo -e "\n${GREEN}Step 2.5: Installing MetalLB...${NC}"
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml

echo "⏳ Waiting for MetalLB controller..."
kubectl wait --namespace metallb-system \
  --for=condition=ready pod \
  --selector=app=metallb \
  --timeout=120s || {
    echo -e "${YELLOW}⚠️  MetalLB not ready yet, checking pods...${NC}"
    kubectl get pods -n metallb-system
}

# Configure MetalLB IP pool
echo "Configuring MetalLB IP address pool..."
kubectl apply -f "$SCRIPT_DIR/metallb-config.yaml"

# Step 2.6: Configure Ingress-Controller as LoadBalancer
echo -e "\n${GREEN}Step 2.6: Configuring ingress-controller...${NC}"
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

# Ensure LoadBalancer type (not ClusterIP/NodePort)
kubectl patch svc ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"type":"LoadBalancer"}}'

echo "⏳ Waiting for LoadBalancer IP assignment..."
sleep 10
INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo -e "${GREEN}✅ Ingress Controller IP: ${INGRESS_IP:-Pending...}${NC}"
```

---

## Netzwerk-Konfiguration

### Router/Firewall-Einstellungen

**Statische IP-Adressen reservieren:**
```
192.168.178.200 → Ingress LoadBalancer (nginx-ingress-controller)
192.168.178.201 → API Gateway LoadBalancer (optional, falls direkt exposed)
192.168.178.202-210 → Reserve für weitere Services
```

**DNS-Einstellungen** (Router oder `/etc/hosts`):

```bash
# Für kind-Cluster (Hybrid-Modus):
192.168.178.80  erechnung.local  # Docker-Host mit HostPort
192.168.178.80  api.erechnung.local

# Für echtes Kubernetes (MetalLB-only):
# 192.168.178.200  erechnung.local  # LoadBalancer IP
# 192.168.178.200  api.erechnung.local
```

### Firewall-Regeln (falls nötig)
```bash
# Ubuntu/Debian
sudo ufw allow from 192.168.178.0/24 to any port 80,443

# iptables
iptables -A INPUT -s 192.168.178.0/24 -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -s 192.168.178.0/24 -p tcp --dport 443 -j ACCEPT
```

---

## Verifikation

### 1. MetalLB Status prüfen
```bash
kubectl get pods -n metallb-system
kubectl get ipaddresspool -n metallb-system
kubectl get l2advertisement -n metallb-system
```

### 2. LoadBalancer IPs prüfen
```bash
# Ingress Controller
kubectl get svc ingress-nginx-controller -n ingress-nginx

# API Gateway (falls exposed)
kubectl get svc api-gateway-service -n erechnung

# Erwartete Ausgabe:
# NAME                       TYPE           EXTERNAL-IP       PORT(S)
# ingress-nginx-controller   LoadBalancer   192.168.178.200   80:xxxx/TCP,443:yyyy/TCP
```

### 3. Erreichbarkeit testen
```bash
# kind-Cluster: MetalLB IP (nur vom Docker-Host aus)
curl http://172.18.255.200  # Docker-Netzwerk IP

# kind-Cluster: HostPort (von überall im LAN)
curl http://192.168.178.80  # Docker-Host IP

# Echtes Kubernetes: LoadBalancer IP (von überall im LAN)
# curl http://192.168.178.200
```

### 4. Logs prüfen (bei Problemen)
```bash
# MetalLB Controller
kubectl logs -n metallb-system -l app=metallb,component=controller

# MetalLB Speaker (L2 Advertisement)
kubectl logs -n metallb-system -l app=metallb,component=speaker
```

---

## Rollback-Plan

Falls Probleme auftreten:

```bash
# 1. Zurück zu NodePort/Hostport
kubectl patch svc ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"type":"ClusterIP"}}'

# 2. MetalLB deinstallieren
kubectl delete -f k8s/kind/metallb-config.yaml
kubectl delete namespace metallb-system

# 3. kind-cluster mit altem Config neu erstellen
kind delete cluster --name erechnung
kind create cluster --config k8s/kind/kind-cluster-config.yaml
```

---

## Vorteile nach Migration

| Aspekt | Vorher (Hostports) | Nachher (MetalLB) |
|--------|-------------------|-------------------|
| **Produktion** | ❌ Nicht vergleichbar | ✅ Identisch zu Cloud LB |
| **Skalierung** | ❌ Single-Node only | ✅ Multi-Node fähig |
| **Portabilität** | ❌ kind-spezifisch | ✅ Standard Kubernetes |
| **Externe IPs** | ❌ Nur 127.0.0.1/Node-IP | ✅ Dedizierte IPs |
| **Service-Trennung** | ❌ Port-Sharing | ✅ IP pro Service |
| **Cloud-Migration** | ❌ Konfiguration anders | ✅ Type: LB identisch |

---

## Nächste Schritte

1. **IP-Bereich mit Router koordinieren** (192.168.178.200-210 reservieren)
2. **metallb-config.yaml aktualisieren** (IP-Pool anpassen)
3. **setup.sh erweitern** (MetalLB Installation)
4. **Services umstellen** (LoadBalancer statt NodePort)
5. **Testen auf localhost** (kind-Cluster)
6. **Remote-Deployment** (192.168.178.80)

## Automatisierte Migration

Für schnelle Umsetzung erstellen wir ein Migration-Script:
```bash
# scripts/migrate-to-metallb.sh
```
