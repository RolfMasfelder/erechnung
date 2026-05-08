---
name: k3s_lokal
display_name: K3s Lokaler Cluster
version: 1.0.0
author: Rolf Masfelder
description: Betriebswissen für den lokalen k3s-Zwei-Node-Cluster (cirrus7-neu + cirrus7). Cluster-Topologie, Namespaces, DNS-FQDN-Muster, Firewall-Anforderungen, bekannte Fallstricke.
---

# K3s Lokaler Cluster — Betriebswissen

## Cluster-Topologie

| Node | Rolle | IP | Hostname | Hardware |
|------|-------|----|----------|----------|
| **cirrus7-neu** | Server (control-plane) | 192.168.178.80 | cirrus7-neu | NUC/Server |
| **cirrus7** | Agent (worker) | 192.168.178.53 | cirrus7 | Workstation |

```
kubectl get nodes
# NAME          STATUS   ROLES                  VERSION
# cirrus7-neu   Ready    control-plane,master   v1.35.4+k3s1
# cirrus7       Ready    <none>                 v1.35.4+k3s1
```

**k3s-Version:** v1.35.4+k3s1 (beide Nodes)
**kubeconfig:** liegt lokal, `kubectl` läuft direkt auf dem Host ohne sudo

---

## Namespaces

| Namespace | Zweck | Hinweis |
|-----------|-------|---------|
| `erechnung` | Produktion | Primäre Installation |
| `erechnung-staging` | Staging/Test | Eigene DB, eigenes Redis |

---

## DNS-Auflösung: FQDN-Pflicht

**Kritisch:** CoreDNS kann nach einem k3s-Upgrade oder Node-Neustart auf den Worker-Node (cirrus7) wechseln. Pods auf dem anderen Node müssen dann über VXLAN mit CoreDNS kommunizieren. Short-Names (`postgres-service`) schlagen ggf. fehl — immer **vollqualifizierte FQDNs** verwenden.

### FQDN-Muster

```
<service-name>.<namespace>.svc.cluster.local
```

### Konfigurierte Werte in ConfigMaps

| Namespace | Variable | Wert |
|-----------|----------|------|
| `erechnung` | `POSTGRES_HOST` / `DB_HOST` | `postgres-service.erechnung.svc.cluster.local` |
| `erechnung-staging` | `POSTGRES_HOST` / `DB_HOST` | `postgres-service.erechnung-staging.svc.cluster.local` |

**Dateien:**
- Basis: `infra/k8s/k3s/manifests/10-configmap-erechnung-config.yaml`
- Staging-Patch: `infra/k8s/k3s/overlays/staging/patch-configmap.yaml`

---

## Firewall-Anforderungen (firewalld)

Beide Nodes müssen die flannel VXLAN-Interfaces in der `trusted` Zone haben, sonst wird Pod-zu-Pod-Traffic geblockt (insbesondere DNS-Traffic zu CoreDNS).

### Auf beiden Nodes ausführen

```bash
sudo firewall-cmd --permanent --zone=trusted --add-interface=cni0
sudo firewall-cmd --permanent --zone=trusted --add-interface=flannel.1
sudo firewall-cmd --reload
```

### Prüfen

```bash
sudo firewall-cmd --zone=trusted --list-interfaces
# trusted: interfaces: cni0 flannel.1
```

### Netzwerk-Ports (zwischen den Nodes)

| Port | Protokoll | Zweck |
|------|-----------|-------|
| 6443 | TCP | k3s API Server |
| 8472 | UDP | Flannel VXLAN (Pod-Netzwerk) |
| 10250 | TCP | kubelet (Node-Kommunikation) |

---

## nodeAffinity: Stateful Workloads auf cirrus7-neu

Postgres und Redis sind an den Server-Node gebunden (lokale PVCs):

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/hostname
              operator: In
              values:
                - cirrus7-neu
```

**Betrifft:** `30-deploy-postgres.yaml`, `32-deploy-redis.yaml`

---

## Kustomize-Struktur

### Produktions-Deployment (erechnung)

```bash
kubectl apply -k infra/k8s/k3s/
```

Kustomization: `infra/k8s/k3s/kustomization.yaml` — listet alle Manifests aus `manifests/`.

### Staging-Deployment (erechnung-staging)

```bash
kubectl apply -k infra/k8s/k3s/overlays/staging/
```

**⚠️ Bekanntes Problem:** Das Staging-Overlay referenziert direkt einzelne Dateien aus `../../manifests/`. Das verletzt kustomizes Security-Restriktion (`file is not in or below the overlay root`) und schlägt fehl.

**Workaround (temporär):** ConfigMap direkt patchen:
```bash
kubectl patch configmap erechnung-config -n erechnung-staging \
  --type merge \
  -p '{"data":{"POSTGRES_HOST":"postgres-service.erechnung-staging.svc.cluster.local","DB_HOST":"postgres-service.erechnung-staging.svc.cluster.local"}}'
```

**Richtige Lösung (TODO §3.3):** `base/`-Verzeichnis einführen als Zwischenschicht — alle Manifests + eigene `kustomization.yaml`. Overlay referenziert dann nur `- ../../base`. Siehe `TODO_2026.md` §3.3.

### IMMER `kubectl apply -k <verzeichnis>` — NIE `kubectl apply -f`

---

## HPA (Horizontal Pod Autoscaler)

| Deployment | Min | Max | CPU-Trigger | scaleDown | scaleUp |
|------------|-----|-----|-------------|-----------|---------|
| `django-web` | 1 | 4 | 70% | 120s | 30s |
| `celery-worker` | 1 | 3 | 70% | 180s | — |

`replicas:` ist aus `50-deploy-django-web.yaml` und `52-deploy-celery-worker.yaml` entfernt — HPA verwaltet die Replikate.

**Datei:** `infra/k8s/k3s/manifests/54-hpa.yaml`

---

## Typische Debugging-Befehle

```bash
# Pod-Status beider Namespaces
kubectl get pods -n erechnung
kubectl get pods -n erechnung-staging

# Logs eines crashenden Pods
kubectl logs -n erechnung deployment/django-web --previous

# DNS-Test innerhalb eines Pods
kubectl exec -n erechnung deployment/django-web -- nslookup postgres-service.erechnung.svc.cluster.local

# CoreDNS-Node prüfen (wichtig nach Upgrades!)
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide

# ConfigMap-Inhalt prüfen
kubectl get configmap erechnung-config -n erechnung -o yaml | grep -E "POSTGRES|DB_HOST"

# Rollout nach ConfigMap-Änderung
kubectl rollout restart deployment/django-web deployment/celery-worker -n erechnung
```

---

## Bekannte Fallstricke

1. **CoreDNS-Wanderung nach k3s-Upgrade:** Nach einem Upgrade landet CoreDNS oft auf dem Worker-Node. Falls flannel-Interfaces dort nicht in `trusted` sind → alle Pods verlieren DNS → CrashLoopBackOff. Immer nach Upgrades `kubectl get pods -n kube-system -o wide` prüfen und ggf. Firewall-Interfaces nachziehen.

2. **Short-Names funktionieren nicht namespace-übergreifend:** `postgres-service` löst nur im selben Namespace auf. Staging-Pods die `postgres-service` (ohne Namespace) konfiguriert haben, treffen den Produktions-Postgres — oder gar nichts. Immer FQDN.

3. **Staging-Overlay bricht `apply -k`:** Siehe oben. Bis zum Refactoring muss ConfigMap manuell gepatcht werden.

4. **PVCs sind node-gebunden:** Lokale PVCs (kein distributed Storage) können nicht auf den anderen Node migrieren. nodeAffinity für Postgres/Redis ist deshalb Pflicht.

5. **Traefik nach k3s-Upgrade:** k3s installiert Traefik als Default-Ingress bei Erstinstallation/Upgrade automatisch. Dieses Projekt nutzt **ingress-nginx** (192.168.178.200, `class: nginx`). Traefik wurde dauerhaft deaktiviert via `/etc/rancher/k3s/config.yaml`:
   ```yaml
   disable:
     - traefik
   ```
   Falls Traefik nach einem Upgrade wieder auftaucht: `kubectl delete helmchart -n kube-system traefik` entfernt ihn sofort (kein k3s-Restart nötig). Die config.yaml verhindert Neuinstallation.

6. **Agent-config.yaml darf keine Server-Flags enthalten:** `disable:` ist ein Server-only-Flag. Falls es in `/etc/rancher/k3s/config.yaml` auf dem Agent-Node steht, schlägt `systemctl restart k3s-agent` fehl mit `flag provided but not defined: -disable`. Lösung: config.yaml auf dem Agent leeren. Das `disable: traefik` im Server config.yaml hat auf den Agent-Node keinen Einfluss — er führt Traefik ohnehin nicht aus.

7. **django-web + celery-worker können nicht auf cirrus7 laufen:** Beide Deployments mounten `media-pvc` (lokales PV auf cirrus7-neu). Solange kein distributed storage existiert, landen alle App-Pods auf cirrus7-neu. `topologySpreadConstraints: DoNotSchedule` würde Pods in Pending lassen. `ScheduleAnyway` ist unschädlich aber wirkungslos.

---

## Zweiter Node (cirrus7) — Agent-Join & Validierung

> **Status (Stand 07.05.2026):** zurückgestellt. Noch ausstehend: belastbare Tests zur Pod-Verteilung über beide Nodes, insbesondere HPA-Skalierung. Die Abschnitte unten dokumentieren den Stand und was bei Wiederaufnahme zu tun ist.

### Agent-Node joinen (Referenz-Kommandos)

**Schritt 1: Token vom Server-Node holen** (auf cirrus7-neu ausführen)

```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```

**Schritt 2: k3s-Agent auf cirrus7 installieren** (auf cirrus7 ausführen)

```bash
curl -sfL https://get.k3s.io | \
  K3S_URL=https://192.168.178.80:6443 \
  K3S_TOKEN=<token-aus-schritt-1> \
  sh -
```

**Schritt 3: Firewall-Interfaces auf cirrus7 in `trusted` Zone setzen**

```bash
sudo firewall-cmd --permanent --zone=trusted --add-interface=cni0
sudo firewall-cmd --permanent --zone=trusted --add-interface=flannel.1
sudo firewall-cmd --reload
```

> **Wichtig:** Schritt 3 muss auf cirrus7 (Agent) genauso wie auf cirrus7-neu (Server) gemacht werden. Ohne dies bricht flannel VXLAN-Traffic und DNS schlägt fehl (CrashLoopBackOff auf Pods die auf cirrus7 landen).

**Prüfen ob Join erfolgreich war** (auf cirrus7-neu)

```bash
kubectl get nodes -o wide
# NAME          STATUS   ROLES                  AGE   VERSION         INTERNAL-IP
# cirrus7-neu   Ready    control-plane,master   ...   v1.35.4+k3s1   192.168.178.80
# cirrus7       Ready    <none>                 ...   v1.35.4+k3s1   192.168.178.53
```

### nodeAffinity schützt stateful Workloads

Postgres und Redis sind durch `nodeAffinity` hart an cirrus7-neu gebunden. Das ist Pflicht, weil lokale PVCs nicht zwischen Nodes wandern können.

**Wichtig:** `django-web` und `celery-worker` mounten `media-pvc` — ebenfalls ein lokales PV auf `cirrus7-neu`. Daher können auch diese Workloads **nur auf `cirrus7-neu` laufen**. `topologySpreadConstraints` ist deshalb nicht anwendbar solange lokale PVCs verwendet werden. Für echtes Multi-Node-Spreading wäre distributed storage nötig (z.B. Longhorn oder NFS).

### Agent-Setup: registries.yaml und config.yaml

Beim Agent-Node-Join müssen zwei Dateien manuell konfiguriert werden:

**1. `/etc/rancher/k3s/registries.yaml`** — von cirrus7-neu kopieren:
```bash
ssh cirrus7-neu "sudo cat /etc/rancher/k3s/registries.yaml" | ssh cirrus7 "sudo tee /etc/rancher/k3s/registries.yaml > /dev/null"
ssh cirrus7 "sudo systemctl restart k3s-agent"
```

**2. `/etc/rancher/k3s/config.yaml`** — darf auf dem Agent **keine** Server-only-Flags enthalten (`disable:`, etc.). Falls vorhanden: leeren oder entfernen.
```bash
# Prüfen:
ssh cirrus7 "sudo cat /etc/rancher/k3s/config.yaml"
# Falls server-only-Flags drin: leeren
ssh cirrus7 "sudo bash -c 'echo \"\" > /etc/rancher/k3s/config.yaml'"
```

### Validierungen: Ergebnisse (Stand 07.05.2026)

- [x] **Flannel VXLAN verifiziert:** DNS-Auflösung von Pod auf `cirrus7-neu` → CoreDNS auf `cirrus7` funktioniert. `postgres-service.erechnung.svc.cluster.local` → `10.43.125.117` ✓
- [x] **Pods auf cirrus7 schedulierbar:** Test-Pod mit explizitem `nodeName: cirrus7` läuft und erhält IP `10.42.1.x` ✓
- [x] **Registry auf cirrus7:** Nach Kopieren der `registries.yaml` und k3s-agent-Restart kann `cirrus7` Images von `192.168.178.80:5000` pullen ✓
- [ ] **Pod-Verteilung (django-web/celery):** **Nicht möglich** solange `media-pvc` ein lokales PV auf `cirrus7-neu` ist. Alle App-Pods bleiben auf `cirrus7-neu`. Für Spreading: distributed storage einführen.
- [ ] **HPA über zwei Nodes:** Nicht testbar bis Pod-Verteilung gelöst ist
- [ ] **Staging-Overlay:** Nach dem Refactoring (TODO §3.3) muss `kubectl apply -k infra/k8s/k3s/overlays/staging/` auch im Zwei-Node-Setup funktionieren
