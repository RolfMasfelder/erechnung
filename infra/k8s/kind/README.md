# kind Configuration for eRechnung

Diese Konfiguration ermöglicht das lokale Testen der Kubernetes-Manifests mit [kind](https://kind.sigs.k8s.io/) (Kubernetes in Docker).

## Voraussetzungen

- **Docker** installiert und laufend
- **kind** installiert: https://kind.sigs.k8s.io/docs/user/quick-start/#installation
- **kubectl** installiert: https://kubernetes.io/docs/tasks/tools/

```bash
# kind Installation (Linux/macOS)
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# kubectl Installation (falls noch nicht vorhanden)
# Siehe: https://kubernetes.io/docs/tasks/tools/
```

## Quick Start

### 1. Cluster erstellen und Anwendung deployen

```bash
# Setup-Skript ausführbar machen
chmod +x k8s/kind/setup.sh k8s/kind/build-and-load-images.sh

# Cluster erstellen, Images bauen und App deployen
./k8s/kind/setup.sh
```

Das Skript führt automatisch folgende Schritte aus:
1. Erstellt kind-Cluster mit Ingress-Support (Multi-Node: 1 Control-Plane + 2 Worker)
2. Installiert Calico CNI (aus lokaler HTTPS Registry)
3. Installiert nginx-ingress-controller (mit hostPort 80/443)
4. **Optional: MetalLB LoadBalancer** (für produktionsnahe Konfiguration)
5. Deployed PostgreSQL, Redis, Django Backend, Celery Worker, API Gateway, Frontend
6. Deployed 12 Network Policies (Zero-Trust Security)
7. Wartet bis alle Pods bereit sind
8. Zeigt Zugriffsinformationen an

### MetalLB LoadBalancer (Production-like Setup)

**Zwei Deployment-Modi:**

| Modus | Beschreibung | Empfehlung |
|-------|--------------|------------|
| **HostPort** | Direkte Port-Mappings (80/443) | Entwicklung/Testing |
| **MetalLB** | LoadBalancer mit dedizierten IPs | Staging/Production |

**MetalLB aktivieren:**
```bash
# Während setup.sh → Bei Frage "Install MetalLB?" → **Y** drücken

# Oder nachträglich migrieren:
cd ../../scripts && ./migrate-to-metallb.sh
```

**Konfiguration** (`metallb-config.yaml`):
```yaml
spec:
  addresses:
  - 192.168.178.200-192.168.178.210  # ← An lokales Netzwerk anpassen!
```

**Wichtig:** IP-Bereich muss:
- Im gleichen Subnet wie Host sein (z.B. 192.168.178.0/24)
- NICHT vom DHCP-Server vergeben werden
- Vom Router/Gateway erreichbar sein

**Vorteile:**
- ✅ Identisch zu Cloud-Providern (AWS ELB, GCP LB)
- ✅ Dedizierte IPs pro Service (keine Port-Konflikte)
- ✅ Multi-Node fähig (horizontal skalierbar)
- ✅ Production-ready Testing

📖 **Detaillierte Anleitung:** [docs/METALLB_MIGRATION.md](../../docs/METALLB_MIGRATION.md)

### HTTPS Docker Registry (Production-like Setup)

**Für Multi-Node kind-Cluster werden ALLE Images aus einer lokalen HTTPS Registry geladen:**

```bash
# Registry läuft auf Host: 192.168.178.80:5000
# TLS-Zertifikate: api-gateway/certs/ (self-signed)
# Containerd trust: skip_verify=true auf allen kind-Nodes
```

**Images in Registry (11 total):**
- Application: `erechnung-{web,celery,init,frontend}:latest`
- Infrastructure: `postgres:17`, `redis:7-alpine`, `busybox:1.35`, `nginx:alpine`
- Calico CNI: `calico/{node,cni,kube-controllers}`

**Vorteile:**
- ⚡ Schnelle Deployments: Postgres in <20s statt >12min
- 🔒 Keine externen Registry-Abhängigkeiten
- 📦 Vollständige Reproduzierbarkeit
- 🌐 Offline-fähig nach Initial-Pull

### Hinweis zu Docker Images

**Multi-Node Cluster (Production-like):**
- Alle Images aus lokaler HTTPS Registry `192.168.178.80:5000`
- `imagePullPolicy: IfNotPresent` - Nutzt lokale Registry
- Kein `kind load docker-image` nötig

**Single-Node Cluster (Legacy/Testing):**
- **erechnung-django:local** - Wird aus Dockerfile gebaut
- **imagePullPolicy: Never** - Verhindert Pull-Versuche
- Externe Images (postgres, redis, nginx) werden normal gepullt

## Manual Setup (Step-by-Step)

Für mehr Kontrolle oder Debugging kann der Cluster auch manuell aufgesetzt werden:

### 1. Multi-Node Cluster erstellen

```bash
cd k8s/kind
./restart-cluster-multinode.sh
```

Erstellt einen kind-Cluster mit:
- 1 Control-Plane Node mit API-Server certSAN für Remote-Zugriff (192.168.178.80)
- 2 Worker Nodes
- Port-Mapping: 6443 (API), 80 (HTTP), 443 (HTTPS)
- Calico CNI (disableDefaultCNI: true)

### 2. kubeconfig exportieren und konfigurieren

```bash
# Kubeconfig vom Remote-Host exportieren
ssh rolf@192.168.178.80 "kind export kubeconfig --name erechnung --kubeconfig ~/.kube/config && cat ~/.kube/config" > ~/.kube/config-erechnung

# Server-IP anpassen (von 0.0.0.0/127.0.0.1 auf Remote-IP)
sed -i 's|server: https://0.0.0.0:[0-9]*|server: https://192.168.178.80:6443|g' ~/.kube/config-erechnung
sed -i 's|server: https://127.0.0.1:[0-9]*|server: https://192.168.178.80:6443|g' ~/.kube/config-erechnung

# kubeconfig aktivieren
export KUBECONFIG=~/.kube/config-erechnung

# Testen
kubectl get nodes  # Sollte 3 Nodes zeigen (NotReady bis Calico installiert ist)
```

### 3. Calico CNI installieren

```bash
# Option A: Via fix-calico-remote.sh (lädt Images in alle Nodes)
./fix-calico-remote.sh

# Calico Manifest anwenden
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml

# Option B: Wenn Images bereits in lokaler Registry
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml

# Warten bis Calico ready ist
kubectl wait --for=condition=ready pod -l k8s-app=calico-node -n kube-system --timeout=120s
kubectl wait --for=condition=ready pod -l k8s-app=calico-kube-controllers -n kube-system --timeout=120s

# Nodes sollten jetzt Ready sein
kubectl get nodes
```

### 4. nginx Ingress Controller installieren

```bash
# Ingress Controller deployen (lokale Datei - bereits für kind optimiert)
kubectl apply -f ingress-nginx-deploy.yaml

# Automatisch nodeSelector und ClusterIP-Service konfigurieren
kubectl label node erechnung-control-plane ingress-ready=true --overwrite
kubectl patch deployment ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"template":{"spec":{"nodeSelector":{"ingress-ready":"true"}}}}}'

# Warten bis Ingress Controller ready ist
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=controller -n ingress-nginx --timeout=120s

# Ingress läuft mit hostPort 80/443 auf Control-Plane Node
kubectl get pods -n ingress-nginx -o wide
```

### 5. TLS-Secret erstellen

```bash
# Self-signed cert für Development
./create-tls-secret.sh
```

### 6. Application deployen

```bash
# Namespace mit Pod Security Labels erstellen (bereits in Manifest enthalten)
# Application deployen
kubectl apply -f k8s-erechnung-local.yaml

# Warten bis alle Pods ready sind
kubectl wait --for=condition=ready pod -l app=postgres -n erechnung --timeout=180s
kubectl wait --for=condition=ready pod -l app=redis -n erechnung --timeout=60s
kubectl wait --for=condition=ready pod -l app=django-web -n erechnung --timeout=120s
kubectl wait --for=condition=ready pod -l app=celery-worker -n erechnung --timeout=60s
kubectl wait --for=condition=ready pod -l app=frontend -n erechnung --timeout=60s
kubectl wait --for=condition=ready pod -l app=api-gateway -n erechnung --timeout=60s

# Status prüfen
kubectl get pods -n erechnung
```

### 7. Network Policies deployen (optional)

```bash
# Zero-Trust Network Policies
kubectl apply -f network-policies.yaml

# Policies testen
./test-network-policies.sh
```

### 8. Zugriff testen

```bash
# Ingress läuft mit hostPort direkt auf Host-IP
# Lokal (auf Remote-Host):
curl -I http://localhost/
curl -Ik https://localhost/

# Von extern (Remote-Zugriff):
curl -I http://192.168.178.80/
curl -Ik https://192.168.178.80/
```

## Anwendung testen (nach Setup)

```bash
# Option A: Via Ingress (Port 80)
curl http://localhost/health/

# Option B: Via Hostname
echo "127.0.0.1 api.erechnung.local" | sudo tee -a /etc/hosts
curl http://api.erechnung.local/health/

# Option C: Via Port-Forward
kubectl port-forward -n erechnung svc/api-gateway-service 8080:80
curl http://localhost:8080/health/
```

## Logs anschauen

```bash
# Django Backend Logs
kubectl logs -n erechnung -l app=django-web --tail=50 -f

# API Gateway Logs
kubectl logs -n erechnung -l app=api-gateway --tail=50 -f

# PostgreSQL Logs
kubectl logs -n erechnung -l app=postgres --tail=50 -f

# Alle Pods im Namespace
kubectl get pods -n erechnung
```

### 4. Django Management Commands ausführen

```bash
# Shell im Django Pod öffnen
kubectl exec -it -n erechnung deployment/django-web -- /bin/bash

# Oder direkt Commands ausführen
kubectl exec -n erechnung deployment/django-web -- \
    python project_root/manage.py migrate

kubectl exec -n erechnung deployment/django-web -- \
    python project_root/manage.py createsuperuser
```

### 5. Cluster löschen

```bash
# Mit Teardown-Skript
chmod +x k8s/kind/teardown.sh
./k8s/kind/teardown.sh

# Oder direkt
kind delete cluster --name erechnung
```

## Unterschiede zur Production-Konfiguration

| Aspekt | Production | kind |
|--------|-----------|------|
| Service Type | LoadBalancer | NodePort |
| Ingress Domain | api.erechnung.com | api.erechnung.local |
| Storage | Cloud PV | hostPath (ephemeral) |
| Auto-Scaling | HPA mit Metriken | Manuell |
| SSL/TLS | Let's Encrypt | Kein SSL |

## Tipps & Troubleshooting

### Pods starten nicht

```bash
# Pod-Status prüfen
kubectl get pods -n erechnung
kubectl describe pod -n erechnung <pod-name>

# Events anzeigen
kubectl get events -n erechnung --sort-by='.lastTimestamp'
```

### Image Pull Probleme

```bash
# Images vorab in kind laden (falls lokale Images)
kind load docker-image your-image:tag --name erechnung
```

### Datenbank-Verbindungsprobleme

```bash
# PostgreSQL Service prüfen
kubectl get svc -n erechnung postgres-service

# PostgreSQL Logs
kubectl logs -n erechnung -l app=postgres

# In Django Pod testen
kubectl exec -n erechnung deployment/django-web -- \
    python -c "from django.db import connection; connection.ensure_connection(); print('DB OK')"
```

### Ingress funktioniert nicht

```bash
# Ingress Controller Status
kubectl get pods -n ingress-nginx

# Ingress Details
kubectl describe ingress -n erechnung erechnung-ingress

# Controller Logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

### Storage-Probleme

```bash
# PVC Status prüfen
kubectl get pvc -n erechnung

# PV prüfen (werden automatisch erstellt)
kubectl get pv
```

## Image Updates und Registry Management

### Application Images aktualisieren

Nach Code-Änderungen oder Dependency-Updates:

```bash
# 1. Images neu bauen (auf Development-Maschine)
cd /home/rolf/workspace/eRechnung/eRechnung_Django_App
docker-compose build --no-cache web celery init
docker build -f frontend/Dockerfile.prod -t 192.168.178.80:5000/erechnung-frontend:latest frontend/

# 2. Für Registry taggen
docker tag erechnung_django_app-web:latest 192.168.178.80:5000/erechnung-web:latest
docker tag erechnung_django_app-celery:latest 192.168.178.80:5000/erechnung-celery:latest
docker tag erechnung_django_app-init:latest 192.168.178.80:5000/erechnung-init:latest

# 3. In Registry pushen
docker push 192.168.178.80:5000/erechnung-web:latest
docker push 192.168.178.80:5000/erechnung-celery:latest
docker push 192.168.178.80:5000/erechnung-init:latest
docker push 192.168.178.80:5000/erechnung-frontend:latest

# 4. In Kubernetes rollout starten (auf Remote-Host oder mit KUBECONFIG)
KUBECONFIG=~/.kube/config-erechnung kubectl rollout restart deployment/django-web -n erechnung
KUBECONFIG=~/.kube/config-erechnung kubectl rollout restart deployment/celery-worker -n erechnung
KUBECONFIG=~/.kube/config-erechnung kubectl rollout restart deployment/frontend -n erechnung

# Rollout-Status überwachen
KUBECONFIG=~/.kube/config-erechnung kubectl rollout status deployment/django-web -n erechnung
```

### Infrastructure Images aktualisieren (PostgreSQL, Redis, etc.)

```bash
# Neue Version pullen
docker pull postgres:17
docker pull redis:7-alpine
docker pull nginx:alpine
docker pull busybox:1.35

# Für lokale Registry taggen
docker tag postgres:17 192.168.178.80:5000/postgres:17
docker tag redis:7-alpine 192.168.178.80:5000/redis:7-alpine
docker tag nginx:alpine 192.168.178.80:5000/nginx:alpine
docker tag busybox:1.35 192.168.178.80:5000/busybox:1.35

# Pushen
docker push 192.168.178.80:5000/postgres:17
docker push 192.168.178.80:5000/redis:7-alpine
docker push 192.168.178.80:5000/nginx:alpine
docker push 192.168.178.80:5000/busybox:1.35

# Deployment neu starten (mit imagePullPolicy: IfNotPresent werden neue Images geladen)
KUBECONFIG=~/.kube/config-erechnung kubectl rollout restart deployment/postgres -n erechnung
KUBECONFIG=~/.kube/config-erechnung kubectl rollout restart deployment/redis -n erechnung
```

### Calico CNI aktualisieren

Wenn Calico auf eine neue Version aktualisiert werden soll:

```bash
# Neue Version definieren
CALICO_VERSION=v3.28.0

# Images pullen
docker pull calico/node:$CALICO_VERSION
docker pull calico/cni:$CALICO_VERSION
docker pull calico/kube-controllers:$CALICO_VERSION

# Für Registry taggen
docker tag calico/node:$CALICO_VERSION 192.168.178.80:5000/calico/node:$CALICO_VERSION
docker tag calico/cni:$CALICO_VERSION 192.168.178.80:5000/calico/cni:$CALICO_VERSION
docker tag calico/kube-controllers:$CALICO_VERSION 192.168.178.80:5000/calico/kube-controllers:$CALICO_VERSION

# Pushen
docker push 192.168.178.80:5000/calico/node:$CALICO_VERSION
docker push 192.168.178.80:5000/calico/cni:$CALICO_VERSION
docker push 192.168.178.80:5000/calico/kube-controllers:$CALICO_VERSION

# Calico Manifest URL in setup.sh anpassen und Cluster neu erstellen
```

### Registry-Inhalt verifizieren

```bash
# Alle Images auflisten
curl -k https://192.168.178.80:5000/v2/_catalog | jq -r '.repositories[]' | sort

# Tags eines bestimmten Images
curl -k https://192.168.178.80:5000/v2/erechnung-web/tags/list | jq .

# Image Digest prüfen (für Rollback)
curl -k -I -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  https://192.168.178.80:5000/v2/erechnung-web/manifests/latest
```

### Troubleshooting Image Pull

**Problem: ImagePullBackOff trotz Image in Registry**

```bash
# 1. Containerd-Config auf allen Nodes prüfen
for node in erechnung-control-plane erechnung-worker erechnung-worker2; do
  echo "=== $node ==="
  docker exec $node cat /etc/containerd/certs.d/192.168.178.80:5000/hosts.toml
done

# 2. Registry erreichbar?
docker exec erechnung-control-plane curl -k https://192.168.178.80:5000/v2/_catalog

# 3. Image vollständig gepusht?
curl -k https://192.168.178.80:5000/v2/erechnung-web/manifests/latest

# 4. Pod Events prüfen
kubectl describe pod <pod-name> -n erechnung
```

## Persistent Data über Cluster-Neuerstellung hinaus

Standardmäßig werden Daten mit dem Cluster gelöscht. Für persistente Daten:

1. **Uncomment** die `extraMounts` Sektion in `kind-cluster-config.yaml`
2. Erstelle die Host-Verzeichnisse:
   ```bash
   mkdir -p /tmp/kind-postgres-data /tmp/kind-redis-data
   ```
3. Erstelle Cluster neu: `./setup.sh`

## Remote kubectl Zugriff

Um von einem anderen Rechner auf den kind-Cluster zuzugreifen:

### Vorbereitung auf dem Remote-Host (wo kind läuft)

```bash
# 1. Firewall/Netzwerk prüfen
./k8s/kind/check-firewall.sh

# 2. kind-Cluster erstellen (falls noch nicht vorhanden)
./k8s/kind/setup.sh

# 3. Kubeconfig exportieren (optional, wird automatisch geholt)
./k8s/kind/export-kubeconfig.sh
```

### Setup auf dem lokalen Rechner

```bash
# Automatisches Setup (empfohlen)
./k8s/kind/setup-remote-access.sh

# Das Skript wird nach folgenden Informationen fragen:
# - Remote Host (user@hostname oder IP)
# - SSH-Zugriff testen
# - kubeconfig holen
# - SSH-Tunnel einrichten

# Umgebungsvariable setzen
export KUBECONFIG=~/.kube/config-kind-erechnung

# Testen
kubectl get pods -n erechnung
```

### Manuelle Alternative

Wenn das automatische Setup nicht funktioniert:

```bash
# Auf dem kind-Host
kind get kubeconfig --name erechnung > kubeconfig-erechnung.yaml

# API Server IP in kubeconfig ändern (localhost → Host-IP)
sed -i 's/127.0.0.1/<HOST-IP>/g' kubeconfig-erechnung.yaml

# kubeconfig auf Remote-Rechner kopieren
scp kubeconfig-erechnung.yaml user@remote:/path/to/kubeconfig

# Auf Remote-Rechner
export KUBECONFIG=/path/to/kubeconfig
kubectl get pods -n erechnung
```

### SSH-Tunnel Management

```bash
# Tunnel Status prüfen
pgrep -af 'ssh.*-L 6443'

# Tunnel stoppen
pkill -f 'ssh.*-L 6443'

# Tunnel neu starten
./k8s/kind/setup-remote-access.sh
```

### Troubleshooting Remote Access

**Problem: SSH-Verbindung funktioniert nicht**
```bash
# Auf Remote-Host: Firewall prüfen
./k8s/kind/check-firewall.sh

# SSH-Port testen
ssh -v user@remote-host
```

**Problem: kubectl timeout**
```bash
# SSH-Tunnel prüfen
pgrep -af 'ssh.*-L 6443'

# Manuell testen
ssh -L 6443:127.0.0.1:<remote-port> user@remote-host
kubectl cluster-info --request-timeout=10s
```

**Problem: Certificate errors**
```bash
# Kubeconfig neu holen
./k8s/kind/setup-remote-access.sh
```

**Hinweis:** kind API Server lauscht standardmäßig nur auf localhost. Für Remote-Zugriff muss Docker Port Forwarding eingerichtet werden.

## Ressourcen

- kind Dokumentation: https://kind.sigs.k8s.io/
- Ingress für kind: https://kind.sigs.k8s.io/docs/user/ingress/
- kubectl Cheat Sheet: https://kubernetes.io/docs/reference/kubectl/cheatsheet/
