# k3s Deployment für eRechnung

Echtes Kubernetes auf lokalem Server mit MetalLB LAN-IPs.

## Server

**Host:** 192.168.178.80 (cirrus7-neu)
**OS:** Ubuntu (vermutlich)
**Zugriff:** SSH via `rolf@192.168.178.80`

## Unterschiede zu kind

| Feature | kind | k3s |
|---------|------|-----|
| **MetalLB IPs** | Docker-Netzwerk (172.18.x.x) | LAN-IPs (192.168.178.x) |
| **Remote-Zugriff** | Via HostPort (80/443) | Via LoadBalancer IP direkt |
| **Produktion** | Nicht vergleichbar | Production-ready |
| **Image-Handling** | `kind load` | `k3s ctr import` |
| **Installation** | Lokal auf Entwickler-Rechner | Remote auf Server |

## LoadBalancer-Optionen

k3s bietet zwei LoadBalancer-Optionen:

### 1. MetalLB (Standard in diesem Setup) ⭐

**Vorteile:**

- ✅ Echte LAN-IPs (192.168.178.200-210)
- ✅ Von überall im Netzwerk erreichbar
- ✅ Production-ready (L2/BGP-Support)
- ✅ Mehrere LoadBalancer-Services möglich
- ✅ Flexible IP-Pool-Verwaltung

**Nachteile:**

- ⚠️ Erfordert separate Installation
- ⚠️ IP-Bereich muss im Router konfiguriert werden (DHCP ausschließen)

**Installation:**

```bash
# MetalLB wird automatisch von setup-k3s-local.sh installiert
# k3s wird mit --disable servicelb installiert (erforderlich!)
```

### 2. ServiceLB/Klipper (k3s built-in)

**Vorteile:**

- ✅ Eingebaut in k3s (keine Extra-Installation)
- ✅ Einfach für Single-Node-Setups
- ✅ Keine Router-Konfiguration nötig

**Nachteile:**

- ❌ Verwendet HostPorts (kein echtes LoadBalancing)
- ❌ Nur eine externe IP pro Node
- ❌ Nicht für Production empfohlen

**Umschalten auf ServiceLB:**

⚠️ **WICHTIG:** Die LoadBalancer-Wahl ist eine **Installations-Option** und kann NICHT nachträglich geändert werden.

Um ServiceLB statt MetalLB zu verwenden:

1. **k3s deinstallieren:**

   ```bash
   ./scripts/k3s-uninstall.sh
   ```

2. **setup-k3s-local.sh anpassen:**

   ```bash
   # Zeile 77: --disable servicelb ENTFERNEN
   curl -sfL https://get.k3s.io | sh -s - \
       --write-kubeconfig-mode 644 \
       --disable traefik
       # <-- servicelb NICHT deaktivieren
   ```

3. **MetalLB-Installation überspringen:**

   ```bash
   # Step 6 im Script auskommentieren oder abbrechen
   ```

4. **Neu installieren:**

   ```bash
   ./scripts/setup-k3s-local.sh
   ```

**Empfehlung für dieses Projekt:**

- **MetalLB** (aktuell) → Production-like Testing, LAN-Zugriff
- **ServiceLB** → Nur für Experimente ohne LAN-Requirements

## Quick Start

```bash
# k3s installieren und eRechnung deployen
cd scripts
./setup-k3s-local.sh

# Kubeconfig für diesen Cluster nutzen
export KUBECONFIG=~/.kube/config-k3s

# Status prüfen (mit Helper-Script)
./k3s-status.sh

# Oder manuell:
kubectl get nodes
kubectl get pods -n erechnung
kubectl get pods -n monitoring
kubectl get svc -n ingress-nginx

# Zugriff testen (von jedem Gerät im LAN!)
curl -k https://erechnung.local
```

## TLS / cert-manager

Das Cluster nutzt **cert-manager** mit einer selbst-signierten CA für TLS.

**Hosts (in `/etc/hosts` eintragen):**

```
<LoadBalancer-IP>  erechnung.local monitoring.erechnung.local
```

**CA-Zertifikat exportieren** (für Browser-Trust):

```bash
kubectl get secret erechnung-ca-secret -n cert-manager \
  -o jsonpath='{.data.ca\.crt}' | base64 -d > erechnung-ca.crt
# In Browser/System als trusted CA importieren
```

**Zertifikate prüfen:**

```bash
kubectl get certificate -A
kubectl get certificaterequest -A
```

## External Secrets Operator (ESO)

Für die zentrale Secrets-Verwaltung steht ein 3-Phasen-Migrations-Pfad bereit:

- **Phase 1 (aktuell):** Plain K8s Secret (`11-secret-erechnung-secrets.yaml`)
- **Phase 2:** ESO mit K8s-Backend (`13-external-secrets.yaml`)
- **Phase 3:** ESO mit Vault-Backend (Konfiguration vorbereitet)

**ESO aktivieren:**

```bash
# 1. Helm installieren
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace

# 2. Secrets in secret-store Namespace seeden
cd scripts && ./generate-secrets.sh --k8s

# 3. ExternalSecret-Manifest anwenden
kubectl apply -f infra/k8s/k3s/manifests/13-external-secrets.yaml

# 4. Plain Secret entfernen (ESO übernimmt)
kubectl delete -f infra/k8s/k3s/manifests/11-secret-erechnung-secrets.yaml
```

## Helper Scripts

```bash
# Installation
./scripts/setup-k3s-local.sh        # Vollständiges Setup (k3s + Registry + eRechnung)

# Verwaltung
./scripts/k3s-status.sh             # Status-Übersicht mit allen Infos
./scripts/k3s-update-images.sh      # Images neu bauen und deployen

# Deinstallation
./scripts/k3s-uninstall.sh          # k3s komplett entfernen (mit Warnung)
```

## Installation

Das Setup-Script führt automatisch aus:

1. **Docker Registry Check**
   - Prüft, ob lokale Registry (192.168.178.80:5000) läuft
   - Startet Registry automatisch falls nötig
   - Gleiche Registry wie kind und docker-compose

2. **k3s Installation** auf 192.168.178.80
   - Lightweight Kubernetes (40MB Binary)
   - Traefik deaktiviert (nutzen nginx-ingress)
   - ServiceLB deaktiviert (nutzen MetalLB)
   - Registry-Konfiguration für 192.168.178.80:5000
   - firewalld: CNI-Interfaces (`cni0`, `flannel.1`) werden in die trusted Zone aufgenommen

3. **Kubeconfig Export**
   - Speichert nach `~/.kube/config-k3s`
   - Server-IP auf 192.168.178.80 angepasst
   - Cluster-Name: k3s-cirrus7

4. **MetalLB Installation**
   - IP-Pool: 192.168.178.200-210 (LAN!)
   - Layer 2 Advertisement für lokales Netzwerk
   - Automatische IP-Vergabe an LoadBalancer Services

5. **Network Policies**
   - Werden via Kustomize aus `k8s/k3s/policies/` angewendet
   - Ingress-/Egress-Regeln für `ingress-nginx`, `erechnung` und `monitoring`

6. **nginx-ingress Controller**
   - Als LoadBalancer Service (erhält MetalLB IP)
   - Erste IP (192.168.178.200) für Ingress

7. **Image Registry Setup**
   - Baut Images lokal via Docker Compose
   - Tagged für Registry (192.168.178.80:5000/...)
   - Pushed zur lokalen HTTPS-Registry
   - **Dieselben Images wie kind und docker-compose!**
   - Frontend wird als Production-Image mit nginx gebaut (kein Vite-Dev-Server)

8. **eRechnung Deployment** (Namespace `erechnung`)
   - PostgreSQL mit PersistentVolume
   - Redis mit PersistentVolume
   - Django Backend + Celery Worker
   - Vue.js Frontend
   - API Gateway (nginx)

9. **Monitoring Stack** (Namespace `monitoring`)
   - Prometheus (Metriken-Scraping)
   - Grafana (Dashboards + eRechnung KPIs)
   - Loki (Log-Aggregation)
   - Promtail (Log-Shipper, DaemonSet)
   - Eigene PodSecurity `privileged` (Promtail braucht hostPath)

## Komponenten

### Local Docker Registry (shared with kind)

**Registry:** `192.168.178.80:5000` (HTTPS mit self-signed cert)

k3s ist konfiguriert, um diese Registry zu verwenden:

```yaml
# /etc/rancher/k3s/registries.yaml (automatisch erstellt)
mirrors:
  "192.168.178.80:5000":
    endpoint:
      - "https://192.168.178.80:5000"
configs:
  "192.168.178.80:5000":
    tls:
      insecure_skip_verify: true
```

**Images in Registry:**

All self-built images use versioned tags (`v<version>-<git-sha>`), managed via `kustomization.yaml`.
**Never use `:latest`** — see `scripts/k3s-update-images.sh` for the tagging workflow.

- `192.168.178.80:5000/erechnung-web:<tag>`
- `192.168.178.80:5000/erechnung-frontend:<tag>`
- `192.168.178.80:5000/erechnung-init:<tag>`
- `192.168.178.80:5000/erechnung-celery:<tag>`
- `192.168.178.80:5000/erechnung-api-gateway:<tag>`
- `192.168.178.80:5000/erechnung-postgres:<tag>` (PostgreSQL 17 + pgTAP)
- `192.168.178.80:5000/redis:7-alpine`
- `192.168.178.80:5000/busybox:1.35`

### MetalLB Config

```yaml
# k8s/k3s/metallb-lan-config.yaml
spec:
  addresses:
  - 192.168.178.200-192.168.178.210  # Echte LAN-IPs!
```

**Router-Konfiguration erforderlich:**

- IP-Bereich vom DHCP ausschließen
- Optional: DNS-Einträge für erechnung.local

### Kubernetes Manifests

```yaml
# k8s/k3s/kustomization.yaml
# Verwendet modulare Resources aus:
# - manifests/*.yaml (Workloads/Services/Ingress)
# - policies/*.yaml (NetworkPolicies)
#
# Zwei Namespaces:
# - erechnung: App-Workloads (PodSecurity: baseline)
# - monitoring: Prometheus, Grafana, Loki, Promtail (PodSecurity: privileged)
#
# Image-Tags werden automatisch via k3s-update-images.sh gesetzt:
image: 192.168.178.80:5000/erechnung-web:v1.0.0-<git-sha>
imagePullPolicy: IfNotPresent  # Images aus lokaler Registry
```

## Zugriff

### Von überall im LAN (192.168.178.x)

```bash
# HTTP (wird auf HTTPS redirected)
curl http://192.168.178.200

# Mit Hostname (nach DNS-Konfiguration)
curl http://erechnung.local
```

### DNS-Einträge

**Router oder /etc/hosts:**

```txt
192.168.178.200  erechnung.local
192.168.178.200  api.erechnung.local
```

## Verwaltung

### Kubeconfig wechseln

```bash
# k3s-Cluster (echter K8s)
export KUBECONFIG=~/.kube/config-k3s

# kind-Cluster (Development)
export KUBECONFIG=~/.kube/config-erechnung

# Standard (falls vorhanden)
export KUBECONFIG=~/.kube/config
```

### Logs ansehen

```bash
export KUBECONFIG=~/.kube/config-k3s

# Django Backend
kubectl logs -n erechnung -l app=django-web --tail=50 -f

# API Gateway
kubectl logs -n erechnung -l app=api-gateway --tail=50 -f

# Monitoring (eigener Namespace)
kubectl logs -n monitoring -l app=prometheus --tail=50 -f
kubectl logs -n monitoring -l app=grafana --tail=50 -f
kubectl logs -n monitoring -l app=promtail --tail=50 -f

# Ingress
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

### Services prüfen

```bash
# Alle LoadBalancer Services
kubectl get svc -A | grep LoadBalancer

# eRechnung Services
kubectl get svc -n erechnung

# Monitoring Services
kubectl get all -n monitoring

# MetalLB Status
kubectl get ipaddresspool -n metallb-system
```

### Image-Update

```bash
# Schnell-Update mit Helper-Script
cd scripts
./k3s-update-images.sh

# Das Script führt automatisch aus:
# 1. docker compose build
# 2. Tag für Registry (192.168.178.80:5000/...)
# 3. Push zur Registry
# 4. kubectl rollout restart

# App (inkl. Policies) neu anwenden
kubectl apply -k k8s/k3s
```

**Oder manuell:**

```bash
# Auf lokalem Entwickler-Rechner:
docker compose build web frontend init

# Versionierten Tag erzeugen
VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
TAG="v${VERSION}-$(git rev-parse --short HEAD)"

# Tag für Registry (NIEMALS :latest verwenden!)
docker tag erechnung_django_app-web:latest 192.168.178.80:5000/erechnung-web:$TAG
docker tag erechnung_django_app-frontend:latest 192.168.178.80:5000/erechnung-frontend:$TAG

# Push zur Registry
docker push 192.168.178.80:5000/erechnung-web:$TAG
docker push 192.168.178.80:5000/erechnung-frontend:$TAG

# kustomization.yaml aktualisieren und deployen
# → Bevorzugt: scripts/k3s-update-images.sh
```

## Deinstallation

### k3s komplett entfernen

```bash
ssh rolf@192.168.178.80 'sudo /usr/local/bin/k3s-uninstall.sh'
```

**Warnung:** Löscht alle Daten, PersistentVolumes, Configs!

### Nur eRechnung-App löschen

```bash
export KUBECONFIG=~/.kube/config-k3s
kubectl delete namespace erechnung
kubectl delete namespace monitoring
```

k3s bleibt installiert, nur die App und Monitoring werden entfernt.

## Troubleshooting

### LoadBalancer IP bleibt pending

```bash
# MetalLB Logs prüfen
kubectl logs -n metallb-system -l app=metallb,component=controller
kubectl logs -n metallb-system -l app=metallb,component=speaker

# IP-Pool prüfen
kubectl get ipaddresspool -n metallb-system -o yaml

# Häufige Ursache: IP-Bereich vom DHCP-Server blockiert
```

### Pods crashen

```bash
# Pod-Status detailliert
kubectl describe pod <pod-name> -n erechnung

# Events prüfen
kubectl get events -n erechnung --sort-by='.lastTimestamp'

# Logs ansehen
kubectl logs <pod-name> -n erechnung
```

### Ingress nicht erreichbar

```bash
# Ingress Service prüfen
kubectl get svc ingress-nginx-controller -n ingress-nginx

# Sollte EXTERNAL-IP haben (z.B. 192.168.178.200)
# Falls <pending>: MetalLB-Problem (siehe oben)

# Ingress-Controller Logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

### SSH-Probleme

```bash
# Connection testen
ssh -v rolf@192.168.178.80 echo "OK"

# Key-basierte Auth einrichten
ssh-copy-id rolf@192.168.178.80

# Falls Passwort-Prompt: SSH-Key fehlt
```

## Vergleich: kind vs. k3s

### Wann kind nutzen?

- Schnelle lokale Entwicklung
- Keine Remote-Zugriff-Anforderungen
- Häufig Cluster neu erstellen
- Ressourcen-schonend (Docker-Container)

### Wann k3s nutzen?

- Produktionsnahe Tests
- Echtes LoadBalancing (LAN-IPs)
- Remote-Zugriff von mehreren Geräten
- Persistente Test-Umgebung
- Cloud-Migration vorbereiten

### Beide parallel nutzen

Möglich! Verschiedene Kubeconfigs:

```bash
# Development
export KUBECONFIG=~/.kube/config-erechnung  # kind

# Testing
export KUBECONFIG=~/.kube/config-k3s        # k3s
```

## Ressourcen

- **k3s Docs:** <https://k3s.io>
- **MetalLB Docs:** <https://metallb.universe.tf>
- **Project Docs:** ../../docs/KUBERNETES_DEPLOYMENT_OPTIONS.md
