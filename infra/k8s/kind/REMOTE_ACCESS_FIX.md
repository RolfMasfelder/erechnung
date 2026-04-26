# Kind Cluster Remote Access Fix

## Problem
LoadBalancer-Service hatte IP 172.18.255.200 (nur Docker-Netzwerk), nicht erreichbar von außen über 192.168.178.80.

## Root Cause
Multi-Node-Cluster mit:
- **Control-Plane**: Hat Port-Mappings 80:80 und 443:443
- **Worker 1 & 2**: Keine Port-Mappings

Ingress-Controller lief auf Worker-Node → Port-Mappings funktionierten nicht.

## Lösung

### 1. Label setzen
```bash
kubectl label node erechnung-control-plane ingress-ready=true
```

### 2. Ingress-Controller auf Control-Plane erzwingen
```bash
kubectl patch deployment ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"template":{"spec":{"nodeSelector":{"ingress-ready":"true"}}}}}'
```

### 3. Service-Typ anpassen (optional)
```bash
kubectl patch svc ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"type":"NodePort"}}'
```

## Ergebnis
✅ **http://192.168.178.80** → Frontend (HTTP/HTTPS)
✅ **https://192.168.178.80** → Frontend (HTTP/2)
✅ **https://192.168.178.80/api** → Backend API

## Permanente Fixes

### kind-cluster-multinode.yaml
- ✅ Added `ingress-ready=true` label in InitConfiguration

### setup.sh
- ✅ Automatisches Label-Setup nach Cluster-Erstellung
- ✅ Automatisches Patch des Ingress-Controllers
- ✅ Service-Typ auf ClusterIP optimiert
- ✅ Aktualisierte Access-Informationen

## MetalLB Entfernung (2026-02-06 Update)

**Grund:** MetalLB vergibt nur Docker-Netzwerk-IPs (172.18.x.x), nicht erreichbar von außen.

### Durchgeführte Änderungen:
```bash
# 1. MetalLB komplett entfernt
kubectl delete namespace metallb-system

# 2. Ingress-Service auf ClusterIP optimiert
kubectl patch svc ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"type":"ClusterIP"}}'
```

### Resultat:
- ✅ 4 Pods weniger (~40MB RAM gespart)
- ✅ Keine verwirrende 172.18.x.x External-IP
- ✅ **hostPort bleibt die Lösung für externen Zugriff**
- ✅ ClusterIP ausreichend (hostPort bindet direkt an Host)

### Dateien markiert als deprecated:
- `metallb-config.yaml` - Mit Hinweis versehen
- `metallb-native.yaml` - Mit Hinweis versehen
- `README.md` - MetalLB-Installationsschritte entfernt

## Port-Mappings im Detail

Kind-Cluster-Config:
```yaml
extraPortMappings:
  - containerPort: 80    # Ingress HTTP
    hostPort: 80
  - containerPort: 443   # Ingress HTTPS
    hostPort: 443
```

Ingress-Controller Pod:
```yaml
ports:
  - containerPort: 80
    hostPort: 80        # Bindet an Host-Port 80
  - containerPort: 443
    hostPort: 443       # Bindet an Host-Port 443
```

## Wichtige Hinweise

1. **hostPort funktioniert nur auf dem Node mit Port-Mappings**
   - In Multi-Node: Nur Control-Plane hat Mappings
   - Lösung: nodeSelector `ingress-ready=true`

2. **LoadBalancer-IP 172.18.x.x ist normal in Kind**
   - MetalLB gibt Docker-Netzwerk-IPs
   - Für externen Zugriff: hostPort oder NodePort nutzen

3. **Firewall auf Host-Rechner**
   - Port 80/443 müssen offen sein
   - Prüfen: `sudo firewall-cmd --list-ports`
   - Öffnen: `sudo firewall-cmd --permanent --add-port=80/tcp --add-port=443/tcp`

## Alternative Lösungen (nicht umgesetzt)

### Option A: Port-Mappings auf allen Nodes
```yaml
nodes:
- role: control-plane
  extraPortMappings: [...]
- role: worker
  extraPortMappings: [...]  # Gleiche Mappings
- role: worker
  extraPortMappings: [...]
```
❌ Problem: Host-Port kann nur einmal gebunden werden

### Option B: External LoadBalancer
- MetalLB mit Host-Netzwerk-IPs
- Erfordert ARP/BGP-Konfiguration
- Komplexer Setup für Single-Host

### Option C: NodePort mit expliziten Ports
```yaml
spec:
  type: NodePort
  ports:
  - nodePort: 30080
    port: 80
```
❌ Problem: Zugriff über http://192.168.178.80:30080 (nicht Port 80)

## Verifizierung

```bash
# Lokaler Test
curl -I http://localhost/
curl -Ik https://localhost/

# Remote Test
curl -I http://192.168.178.80/
curl -Ik https://192.168.178.80/

# Pod Status
kubectl get pods -n ingress-nginx -o wide
# Sollte zeigen: NODE=erechnung-control-plane

# Service Status
kubectl get svc -n ingress-nginx
```

## Datum
2026-02-06
