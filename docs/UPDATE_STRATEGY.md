# Update-Strategie für produktive eRechnung-Installationen

**Erstellt:** 17.03.2026
**Status:** Implementiert (Phase 1–7 abgeschlossen, 18.03.2026)
**Betrifft:** Docker-Only (KMU ≤ 5 User) und Kubernetes/K3s (Enterprise > 10 User)

---

## Inhaltsverzeichnis

1. [Überblick und Ziele](#1-überblick-und-ziele)
2. [Versionierungsstrategie](#2-versionierungsstrategie)
3. [Szenario A: Docker-Only Update (KMU)](#3-szenario-a-docker-only-update-kmu)
4. [Szenario B: Kubernetes/K3s Rolling Update (Enterprise)](#4-szenario-b-kubernetesk3s-rolling-update-enterprise)
5. [Datenbank-Migrationen bei Updates](#5-datenbank-migrationen-bei-updates)
6. [Rollback-Verfahren](#6-rollback-verfahren)
7. [Update-Benachrichtigungen und Release Notes](#7-update-benachrichtigungen-und-release-notes)
8. [Checklisten](#8-checklisten)
9. [Risiken und Mitigationen](#9-risiken-und-mitigationen)
10. [Integrationstests für Update-Szenarien](#10-integrationstests-für-update-szenarien)
11. [Offene Punkte für Implementierung](#11-offene-punkte-für-implementierung)

---

## 1. Überblick und Ziele

### 1.1 Problemstellung

Die eRechnung-Applikation läuft in zwei Deployment-Varianten produktiv. Für beide fehlt ein definierter, wiederholbarer Prozess, um Software-Updates (neue Features, Bugfixes, Sicherheitspatches) sicher auf einer laufenden Installation einzuspielen — ohne Datenverlust und mit möglichst geringer Downtime.

### 1.2 Anforderungen an den Update-Prozess

| Anforderung | Docker-Only (KMU) | Kubernetes (Enterprise) |
|---|---|---|
| **Maximale Downtime** | ≤ 5 Minuten (Wartungsfenster) | Zero-Downtime (Rolling Update) |
| **Datenverlust** | Keiner | Keiner |
| **Rollback-Fähigkeit** | Ja, auf vorherige Version | Ja, automatisch bei Health-Check-Fehler |
| **Automatisierungsgrad** | Skript-gesteuert (ein Befehl) | Vollautomatisch via kubectl/CI-CD |
| **Technisches Wissen** | Minimal (docker compose) | K8s-Grundkenntnisse |
| **Backup vor Update** | Automatisch (erzwungen) | Automatisch (erzwungen) |
| **DB-Migration** | Automatisch im Init-Container | Automatisch via Kubernetes Job |

### 1.3 Bestandsaufnahme

Folgende Bausteine existieren bereits und werden im Update-Prozess genutzt:

- **Backup/Restore**: `scripts/backup.sh`, `scripts/restore.sh`, `scripts/backup_restore_test.sh`
- **DB-Migrationen**: Alle reversibel, Zero-Downtime-Patterns dokumentiert (siehe `docs/MIGRATION_STRATEGY.md`)
- **Image-Build und -Push (K3s)**: `scripts/k3s-update-images.sh` (Build → Tag → Push → Apply)
- **Kustomize-basierte Versionierung**: `infra/k8s/k3s/kustomization.yaml` mit Image-Tag-Overrides
- **Init-Container**: `scripts/init_django.sh` (migrate + collectstatic + Superuser)
- **Health Checks**: Liveness/Readiness-Probes auf `/health/` (K8s), `manage.py check --database` (Docker)
- **Monitoring**: Prometheus + Grafana (K3s), docker-compose.monitoring.yml (Docker)

---

## 2. Versionierungsstrategie

### 2.1 Semantic Versioning (SemVer)

Die Applikation folgt **Semantic Versioning 2.0.0** (`MAJOR.MINOR.PATCH`):

| Segment | Bedeutung | Beispiel |
|---|---|---|
| **MAJOR** | Breaking Changes: API-Inkompatibilität, DB-Schema ohne Rückwärtskompatibilität | 1.0.0 → 2.0.0 |
| **MINOR** | Neue Features, rückwärtskompatibel | 1.0.0 → 1.1.0 |
| **PATCH** | Bugfixes, Sicherheitspatches, keine Feature-Änderungen | 1.0.0 → 1.0.1 |

Die Version wird zentral in `pyproject.toml` gepflegt:

```toml
[project]
version = "1.0.0"
```

### 2.2 Image-Tagging

Jedes Release erzeugt Docker-Images mit folgenden Tags:

```txt
v<VERSION>-<GIT-SHA-SHORT>   # Eindeutig: v1.1.0-a3f8b2c
v<VERSION>                    # Release-Alias: v1.1.0
latest                        # Immer das neueste Release
```

**Betroffene Images** (5 Stück):

- `erechnung-web` (Django + Gunicorn)
- `erechnung-init` (Migrations-Job)
- `erechnung-frontend` (Vue.js + nginx)
- `erechnung-api-gateway` (OpenResty + Lua JWT)
- `erechnung-postgres` (PostgreSQL 17 + pgTAP)

### 2.3 Kompatibilitätsmatrix

Jedes Release dokumentiert:

| Komponente | Minimal-Version | Empfohlene Version |
|---|---|---|
| PostgreSQL | 17.x | 17.x (identisch) |
| Redis | 7.x | 7.x (identisch) |
| Docker Engine | 24.0+ | 27.x |
| Docker Compose | v2.20+ | v2.32+ |
| K3s | v1.28+ | v1.31+ |
| Python | 3.13 | 3.13 |

---

## 3. Szenario A: Docker-Only Update (KMU)

### 3.1 Gesamtablauf

```txt
┌──────────────────────────────────────────────────────┐
│              Docker-Only Update-Ablauf                │
│                                                      │
│  1. Pre-Flight Check                                 │
│     ├─ Aktuelle Version ermitteln                    │
│     ├─ Ziel-Version prüfen                           │
│     └─ Freier Speicherplatz prüfen                   │
│                                                      │
│  2. Automatisches Backup (erzwungen)                 │
│     ├─ Datenbank-Dump (pg_dump)                      │
│     ├─ Media-Dateien (tar.gz)                        │
│     └─ Backup-Verifizierung (SHA256)                 │
│                                                      │
│  3. Neue Images ziehen                               │
│     └─ docker compose pull                           │
│                                                      │
│  4. Applikation stoppen                              │
│     └─ docker compose down                           │
│    ┌─── Downtime-Beginn ───────────────────────┐     │
│  5. │ Neue Container starten                   │     │
│     │  └─ docker compose up -d                 │     │
│     │    ├─ Init-Container: migrate + static   │     │
│     │    ├─ Web-Container: Health Check         │     │
│     │    └─ Frontend: Startup                   │     │
│    └─── Downtime-Ende (~2-3 Min) ──────────────┘     │
│                                                      │
│  6. Post-Update Verification                         │
│     ├─ Health-Endpoint prüfen                        │
│     ├─ Versions-Endpoint prüfen                      │
│     ├─ Smoke-Test (Login + Rechnungsliste)           │
│     └─ DB-Migration-Status prüfen                    │
│                                                      │
│  7. Rollback (nur bei Fehler)                        │
│     ├─ docker compose down                           │
│     ├─ Alte Images taggen                            │
│     ├─ Restore aus Backup                            │
│     └─ docker compose up -d (alte Version)           │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 3.2 Update-Quellen

Für Docker-Only-Installationen gibt es zwei mögliche Distributionswege:

**Option A — Docker Hub (empfohlen für KMU):**

```bash
# Images werden vom Betreiber in Docker Hub veröffentlicht
# Kunde zieht neue Version:
docker compose -f docker-compose.yml -f docker-compose.production.yml pull
```

**Option B — Lokaler Build (für Selbst-Hoster mit Quellcode):**

```bash
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.production.yml build
```

### 3.3 Update-Skript: `scripts/update-docker.sh`

Das zentrale Update-Skript kapselt den gesamten Ablauf in einen einzelnen Befehl:

```bash
# Standard-Update
./scripts/update-docker.sh

# Update auf eine bestimmte Version
./scripts/update-docker.sh --version v1.2.0

# Trockenlauf (nur prüfen, nichts ändern)
./scripts/update-docker.sh --dry-run

# Ohne Bestätigungsabfrage (für Automatisierung)
./scripts/update-docker.sh --yes
```

**Skript-Ablauf im Detail:**

```txt
update-docker.sh
├── 1. Pre-Flight Checks
│   ├── Docker Daemon läuft?
│   ├── docker-compose.yml vorhanden?
│   ├── Freier Speicherplatz > 2 GB?
│   ├── Aktuelle Version ermitteln (docker inspect → LABEL)
│   └── Ziel-Version ermitteln (--version oder latest)
│
├── 2. Backup (erzwungen, nicht überspringbar)
│   ├── ./scripts/backup.sh --all
│   ├── SHA256-Verifizierung
│   └── Backup-Pfad protokollieren
│
├── 3. Image-Update
│   ├── docker compose pull (Option A)
│   │   oder
│   ├── docker compose build (Option B)
│   └── Alte Images als Fallback taggen (:pre-update)
│
├── 4. Controlled Shutdown
│   ├── docker compose stop web celery frontend api-gateway
│   ├── 10s Grace Period für laufende Requests
│   └── docker compose stop db redis (zuletzt)
│
├── 5. Startup mit neuer Version
│   ├── docker compose up -d db redis
│   ├── Warte auf DB-Readiness (pg_isready)
│   ├── docker compose up -d init (Migrations)
│   ├── Warte auf Init-Container-Exit (Code 0)
│   ├── docker compose up -d web celery
│   ├── Warte auf Health Check (/health/)
│   └── docker compose up -d frontend api-gateway
│
├── 6. Post-Update Verification
│   ├── curl /api/health/ → 200 OK
│   ├── curl /api/version/ → Ziel-Version
│   ├── showmigrations → alle [X]
│   └── Monitoring-Metriken prüfen
│
└── 7. Status-Ausgabe
    ├── ✅ Update erfolgreich: v1.0.0 → v1.1.0
    ├── Backup-Pfad: ./backups/20260317_120000/
    └── Rollback-Befehl bei Problemen
```

### 3.4 Wartungsmodus

Während des Updates zeigt der API-Gateway eine Wartungsseite:

```txt
┌─────────────────────────────────────────┐
│      eRechnung — Wartungsarbeiten       │
│                                         │
│  Das System wird gerade aktualisiert.   │
│  Bitte versuchen Sie es in wenigen      │
│  Minuten erneut.                        │
│                                         │
│  Geschätzte Dauer: 2-5 Minuten         │
└─────────────────────────────────────────┘
```

**Technische Umsetzung**: Der API-Gateway-Container bleibt als letzter laufen und leitet alle Requests auf eine statische HTML-Wartungsseite um, bis das Backend wieder erreichbar ist. Alternative: Der API-Gateway wird zuerst gestoppt und neu gestartet — die kurze Downtime von 2-3 Minuten ist für KMU-Installationen akzeptabel.

---

## 4. Szenario B: Kubernetes/K3s Rolling Update (Enterprise)

### 4.1 Gesamtablauf

```txt
┌──────────────────────────────────────────────────────────┐
│          Kubernetes Rolling Update-Ablauf                 │
│                                                          │
│  1. Pre-Flight Check                                     │
│     ├─ Cluster-Health prüfen (alle Nodes Ready)          │
│     ├─ Aktuelle Deployment-Version ermitteln              │
│     ├─ PVC-Speicherplatz prüfen                          │
│     └─ kustomization.yaml vorbereiten                    │
│                                                          │
│  2. Automatisches Backup                                 │
│     ├─ pg_dump aus dem Postgres-Pod                       │
│     ├─ PVC-Snapshot (falls StorageClass unterstützt)     │
│     └─ Backup-Verifizierung                              │
│                                                          │
│  3. Neue Images in Registry pushen                       │
│     ├─ Build aller 5 Images                              │
│     ├─ Tag mit Version + Git-SHA                         │
│     └─ Push in lokale Registry (192.168.178.80:5000)     │
│                                                          │
│  4. DB-Migration als Kubernetes Job                      │
│     ├─ Job: django-migrate-v<VERSION>                    │
│     ├─ Wartet auf DB-Readiness                           │
│     ├─ `manage.py migrate --noinput`                     │
│     └─ Job muss erfolgreich abschließen                  │
│                                                          │
│                                                          │
│  5. Rolling Update (Zero-Downtime)                       │
│     ├─ kubectl apply -k infra/k8s/k3s/                   │
│     ├─ K8s startet neue Pods parallel                    │
│     │   ├─ Readiness Probe: /health/ (5s Intervall)      │
│     │   ├─ Alter Pod bedient Requests weiter             │
│     │   └─ Neuer Pod übernimmt nach Readiness            │
│     ├─ maxSurge: 1 (ein zusätzlicher Pod)                │
│     └─ maxUnavailable: 0 (kein Pod offline)              │
│                                                          │
│  6. Post-Update Verification                             │
│     ├─ kubectl rollout status deployment/django-web      │
│     ├─ Alle Pods Running + Ready                         │
│     ├─ Ingress erreichbar                                │
│     ├─ Prometheus-Metriken: Error-Rate < Schwellwert     │
│     └─ Smoke-Test über Ingress                           │
│                                                          │
│  7. Automatischer Rollback (bei Fehler)                  │
│     ├─ Readiness Probe schlägt fehl                      │
│     ├─ progressDeadlineSeconds überschritten (300s)      │
│     ├─ kubectl rollout undo deployment/django-web        │
│     └─ Alter ReplicaSet wird reaktiviert                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Rolling Update-Strategie

In den Kubernetes-Deployments wird eine explizite Update-Strategie definiert:

```yaml
# Deployment: django-web
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1           # Max. 1 zusätzlicher Pod während Update
      maxUnavailable: 0     # Keine Unterbrechung: alter Pod bleibt aktiv
  minReadySeconds: 10       # Pod muss 10s stable sein vor nächstem Update
  revisionHistoryLimit: 5   # Letzte 5 Revisionen für Rollback vorhalten
```

**Für alle Deployments mit >1 Replikas:**

| Deployment | Replicas | maxSurge | maxUnavailable | Effekt |
|---|---|---|---|---|
| `django-web` | 2 | 1 | 0 | Zero-Downtime |
| `api-gateway` | 2 | 1 | 0 | Zero-Downtime |
| `frontend` | 1–2 | 1 | 0 | Zero-Downtime |
| `celery-worker` | 1 | 1 | 0 | Kurze Task-Pause möglich |

**Singletons** (kein Rolling Update):

| Deployment | Strategie | Grund |
|---|---|---|
| `postgres` | `Recreate` | Stateful, nur 1 Instanz (PVC-Lock) |
| `redis` | `Recreate` | Stateful, Persistenz-Flush nötig |

### 4.3 Migrations-Job (vor Rolling Update)

DB-Migrationen werden **separat** und **vor** dem Rolling Update ausgeführt:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: django-migrate-v1-1-0
  namespace: erechnung
spec:
  backoffLimit: 3
  activeDeadlineSeconds: 300
  template:
    spec:
      restartPolicy: OnFailure
      initContainers:
      - name: wait-for-db
        image: busybox
        command: ['sh', '-c', 'until nc -z postgres 5432; do sleep 2; done']
      containers:
      - name: migrate
        image: 192.168.178.80:5000/erechnung-web:v1.1.0
        command:
        - python
        - project_root/manage.py
        - migrate
        - --noinput
        envFrom:
        - configMapRef:
            name: erechnung-config
        - secretRef:
            name: erechnung-secrets
```

**Wichtig**: Der Migrations-Job muss erfolgreich abschließen (Exit-Code 0), bevor die Deployments aktualisiert werden. Bei Fehlschlag wird das Update abgebrochen.

### 4.4 Pod Disruption Budget (PDB)

Um sicherzustellen, dass während eines Updates oder Node-Drains immer genügend Pods verfügbar sind:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: django-web-pdb
  namespace: erechnung
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: django-web
```

### 4.5 Update-Skript: `scripts/update-k3s.sh`

Aufbauend auf dem bestehenden `scripts/k3s-update-images.sh`:

```bash
# Standard-Update
./scripts/update-k3s.sh

# Update auf bestimmte Version
./scripts/update-k3s.sh --version v1.2.0

# Nur Images bauen und pushen (kein Deploy)
./scripts/update-k3s.sh --build-only

# Trockenlauf
./scripts/update-k3s.sh --dry-run
```

**Skript-Ablauf:**

```txt
update-k3s.sh
├── 1. Pre-Flight
│   ├── kubectl cluster-info (Cluster erreichbar?)
│   ├── kubectl get nodes (alle Ready?)
│   ├── Aktuelle Image-Tags aus Deployments lesen
│   └── Version aus pyproject.toml lesen
│
├── 2. Backup
│   ├── kubectl exec postgres-pod -- pg_dump → lokale Datei
│   ├── Optional: VolumeSnapshot (CSI-Driver)
│   └── SHA256-Verifizierung
│
├── 3. Build & Push
│   ├── docker build (alle 5 Images)
│   ├── docker tag v<VERSION>-<SHA>
│   ├── docker push → 192.168.178.80:5000
│   └── kustomization.yaml: newTag aktualisieren
│
├── 4. DB-Migration
│   ├── kubectl apply -f migration-job.yaml
│   ├── kubectl wait --for=condition=complete job/django-migrate
│   ├── Bei Fehler: ABBRUCH (kein Deployment-Update)
│   └── Job-Logs prüfen
│
├── 5. Rolling Update
│   ├── kubectl apply -k infra/k8s/k3s/
│   ├── kubectl rollout status deployment/django-web (Timeout 300s)
│   ├── kubectl rollout status deployment/api-gateway
│   ├── kubectl rollout status deployment/frontend
│   └── kubectl rollout status deployment/celery-worker
│
├── 6. Verification
│   ├── kubectl get pods -n erechnung (alle Running/Ready)
│   ├── curl http://192.168.178.80/api/health/ → 200
│   ├── Prometheus: Error-Rate prüfen
│   └── Smoke-Test
│
└── 7. Cleanup
    ├── Alte Migration-Jobs aufräumen
    ├── Nicht mehr genutzte Images aus Registry löschen
    └── Update-Protokoll in PROGRESS_PROTOCOL.md
```

### 4.6 Canary Deployment (optional, für kritische Updates)

Für besonders kritische Releases kann ein Canary-Deployment-Muster eingesetzt werden:

```txt
Phase 1: Canary (10% Traffic)
├── 1 Pod mit neuer Version deployen
├── Ingress: weighted Routing (90/10)
├── 30 Min. Monitoring: Error-Rate, Latenz, Logs
└── Bei Anomalien: Canary-Pod entfernen

Phase 2: Rollout (100% Traffic)
├── Alle Pods auf neue Version aktualisieren
├── Standard Rolling Update (wie oben)
└── Monitoring für 24h
```

Dies erfordert zusätzlich einen Ingress-Controller mit Traffic-Splitting (z.B. nginx-Ingress mit Canary-Annotations) und wird als optionale Erweiterung betrachtet.

---

## 5. Datenbank-Migrationen bei Updates

### 5.1 Grundprinzip

Jede neue Version kann Django-Migrationen enthalten. Diese werden **immer automatisch** als Teil des Update-Prozesses ausgeführt — nicht manuell.

### 5.2 Klassifizierung

| Migrations-Typ | Risiko | Downtime nötig? | Beispiel |
|---|---|---|---|
| AddField (nullable/default) | Niedrig | Nein | Neues optionales Feld |
| AddIndex (CONCURRENTLY) | Niedrig | Nein | Performance-Index |
| Data-Migration (batch) | Mittel | Nein | Daten transformieren |
| AlterField (Typ-Änderung) | Hoch | Ja (Docker), Nein (K8s mit Expand/Contract) | String → Integer |
| RemoveField | Hoch | Nur Docker | Feld-Entfernung nach 3-Phasen-Pattern |

### 5.3 Migrations-Reihenfolge im Update

```txt
1. Backup (automatisch)
2. Prüfung: `manage.py showmigrations` → Pending Migrations?
3. Prüfung: `manage.py migrate --plan` → Welche Operationen?
4. Ausführung: `manage.py migrate --noinput`
5. Verifikation: `manage.py showmigrations` → Alle [X]?
```

### 5.4 Sicherheitsnetz: Migrations-Kompatibilitätsprüfung

Ein Pre-Update-Check validiert, ob die geplanten Migrationen zum aktuellen Datenbestand passen:

```bash
# Prüft ob Migrationen anwendbar sind ohne sie auszuführen
manage.py migrate --plan --check
```

Wenn dieser Befehl fehlschlägt, wird das Update abgebrochen und der Administrator informiert.

---

## 6. Rollback-Verfahren

### 6.1 Docker-Only Rollback

```bash
# 1. Aktuelle (fehlerhafte) Container stoppen
docker compose -f docker-compose.yml -f docker-compose.production.yml down

# 2. Alte Images wiederherstellen (wurden als :pre-update getaggt)
docker tag erechnung-web:pre-update erechnung-web:latest
docker tag erechnung-frontend:pre-update erechnung-frontend:latest
docker tag erechnung-api-gateway:pre-update erechnung-api-gateway:latest

# 3. Datenbank aus Backup wiederherstellen
./scripts/restore.sh --latest --db-only

# 4. Alte Version starten
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d

# 5. Verifizieren
curl -s https://localhost/api/health/
```

**Automatisiert als Skript:**

```bash
./scripts/rollback-docker.sh           # Rollback auf Pre-Update-Backup
./scripts/rollback-docker.sh --backup <PFAD>  # Rollback auf bestimmtes Backup
```

### 6.2 Kubernetes Rollback

**Automatisch** (bei fehlschlagender Readiness Probe):

```txt
K8s erkennt: Neuer Pod wird nicht Ready
→ progressDeadlineSeconds (300s) läuft ab
→ Rollout wird gestoppt
→ Alter ReplicaSet bleibt aktiv
→ Kein manueller Eingriff nötig
```

**Manuell:**

```bash
# Rollback des letzten Deployments
kubectl -n erechnung rollout undo deployment/django-web
kubectl -n erechnung rollout undo deployment/api-gateway
kubectl -n erechnung rollout undo deployment/frontend
kubectl -n erechnung rollout undo deployment/celery-worker

# Rollback auf eine bestimmte Revision
kubectl -n erechnung rollout history deployment/django-web
kubectl -n erechnung rollout undo deployment/django-web --to-revision=3
```

**DB-Rollback (nur bei fehlgeschlagener Migration):**

```bash
# 1. Migration rückgängig machen
kubectl -n erechnung exec deploy/django-web -- \
  python project_root/manage.py migrate invoice_app <VORHERIGE_MIGRATION>

# 2. Oder: Datenbank aus Backup wiederherstellen
kubectl -n erechnung exec deploy/postgres -- \
  pg_restore -d erechnung /backups/pre-update.dump
```

### 6.3 Rollback-Entscheidungsmatrix

| Symptom | Docker-Only | Kubernetes |
|---|---|---|
| Web-Container startet nicht | Rollback Images + Restore | Automatischer Rollback |
| Health Check schlägt fehl | Rollback Images + Restore | Automatischer Rollback |
| Migration schlägt fehl | Restore aus Backup | Migration rückgängig, Update abbrechen |
| Funktionaler Fehler (nach Start) | Rollback Images + Restore | `rollout undo` + ggf. DB-Restore |
| Performance-Regression | Optional: Rollback | `rollout undo` |

---

## 7. Update-Benachrichtigungen und Release Notes

### 7.1 Release Notes je Version

Jedes Release wird dokumentiert in `CHANGELOG.md` mit folgendem Format:

```markdown
## [1.1.0] — 2026-04-01

### Hinzugefügt
- Import von Eingangsrechnungen (ZUGFeRD PDF)
- Geschäftspartner-Massenimport via CSV

### Geändert
- Steuerberechnung nutzt jetzt EU-One-Stop-Shop-Regeln

### Behoben
- PDF-Export: Fehlende Seitennummern (#42)

### Migrationen
- 0008_incoming_invoice_model (Schema: Neues Model IncomingInvoice)
- 0009_business_partner_import_fields (Schema: Neue Felder auf BusinessPartner)

### Kompatibilität
- Minimale Vorgänger-Version: v1.0.0
- PostgreSQL: 17.x (keine Änderung)
- Breaking Changes: Keine
```

### 7.2 Update-Pfade

Nicht jede Version kann von jeder beliebigen Vorgängerversion aktualisiert werden. Die Dokumentation enthält eine **Update-Pfad-Matrix**:

```txt
v1.0.0 → v1.1.0    ✅ Direktes Update
v1.0.0 → v1.2.0    ✅ Direktes Update (Migrationen sind kumulativ)
v1.0.0 → v2.0.0    ⚠️ Über v1.x.latest, dann auf v2.0.0
v1.1.0 → v2.0.0    ⚠️ Über v1.x.latest, dann auf v2.0.0
```

**Regel**: Innerhalb einer MAJOR-Version ist ein direktes Update auf jede höhere Version möglich (Django-Migrationen sind kumulativ). Bei MAJOR-Version-Sprüngen kann ein Zwischenschritt erforderlich sein.

---

## 8. Checklisten

### 8.1 Checkliste: Vor dem Update (beide Szenarien)

- [ ] Release Notes der Ziel-Version gelesen
- [ ] Kompatibilitätsmatrix geprüft (DB-Version, Redis-Version)
- [ ] Breaking Changes identifiziert und verstanden
- [ ] Aktuelles Backup vorhanden und verifiziert (SHA256)
- [ ] Freier Speicherplatz geprüft (min. 2 GB Docker, 5 GB K8s)
- [ ] Wartungsfenster kommuniziert (Docker-Only)
- [ ] Monitoring-Dashboard geöffnet

### 8.2 Checkliste: Nach dem Update (beide Szenarien)

- [ ] Health-Endpoint erreichbar: `/api/health/` → 200
- [ ] Versions-Endpoint: `/api/version/` → Ziel-Version
- [ ] Alle DB-Migrationen angewandt: `showmigrations` → alle [X]
- [ ] Login funktioniert (Admin + normaler Benutzer)
- [ ] Rechnungsliste wird angezeigt
- [ ] Neue Rechnung kann erstellt werden
- [ ] PDF-Export funktioniert
- [ ] ZUGFeRD-XML ist valide
- [ ] Keine Fehler in Logs (`docker compose logs` / `kubectl logs`)
- [ ] Prometheus error_rate Metrik normal
- [ ] Backup-Pfad des Pre-Update-Backups notiert

### 8.3 Checkliste: Rollback-Kriterien

Rollback wird eingeleitet wenn innerhalb von 30 Minuten nach Update:

- [ ] Health-Endpoint nicht erreichbar
- [ ] Error-Rate > 5% (Prometheus)
- [ ] Kern-Funktionalität (Rechnungen erstellen/ansehen) nicht nutzbar
- [ ] Datenverlust festgestellt
- [ ] Sicherheitslücke in neuer Version entdeckt

---

## 9. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|---|---|---|---|
| Migration schlägt fehl | Mittel | Hoch | Pre-Check (`migrate --plan`), automatisches Backup, reversible Migrationen |
| Neue Version startet nicht | Niedrig | Hoch | Health Checks, automatischer Rollback (K8s), Image-Pre-Tagging (Docker) |
| Datenverlust bei Stop/Start | Sehr niedrig | Kritisch | Named Volumes (Docker), PVCs (K8s), erzwungenes Backup vor Update |
| Inkompatible Migrationen (alter Code + neues Schema) | Mittel | Hoch | Zero-Downtime-Migration-Patterns (siehe MIGRATION_STRATEGY.md), 3-Phasen-Muster |
| Netzwerk-Unterbrechung während Image-Pull | Niedrig | Mittel | Retry-Logik im Update-Skript, lokaler Image-Cache |
| Speicherplatz (Images + Backup + DB) | Mittel | Mittel | Pre-Flight-Check Speicherplatz, Image-Cleanup, Backup-Rotation |
| Redis-Inkompatibilität (Cache-Format) | Sehr niedrig | Niedrig | Redis `FLUSHALL` als Upgrade-Schritt (Cache ist nicht persistent-kritisch) |
| PostgreSQL Major-Version-Upgrade | Niedrig | Hoch | `pg_upgrade` oder Dump/Restore, separater Prozess, nicht im Standard-Update |

---

## 10. Integrationstests für Update-Szenarien

Update-Prozesse sind komplex, zustandsbehaftet und schwer manuell zu verifizieren. Daher sind umfassende Integrationstests zwingend erforderlich — nicht nur für einzelne Module, sondern für den **gesamten Update-Durchlauf** als End-to-End-Prozess. Diese Tests laufen autonom in isolierten Umgebungen und müssen **vor jedem produktiven Update** erfolgreich durchlaufen.

### 10.1 Test-Architektur

```txt
┌──────────────────────────────────────────────────────────────┐
│              Update-Integrations-Test-Pyramide               │
│                                                              │
│  Ebene 4: Full-Stack Update-Simulation (E2E)                │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Komplette Update-Durchläufe mit realen Containern  │      │
│  │ Docker-Only + K3s Szenario, inkl. Rollback         │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  Ebene 3: Komponenten-Integrationstests                      │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Backup → Migrate → Start → Verify → Rollback      │      │
│  │ Jede Phase einzeln + in Kombination                │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  Ebene 2: Migrations-Integrationstests                       │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Schema-Kompatibilität, Datenintegrität,             │      │
│  │ Forward + Backward Migration, Batch-Processing     │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  Ebene 1: Skript-Unit-Tests                                  │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Pre-Flight Checks, Versionserkennung,              │      │
│  │ Backup-Aufruf, Image-Tagging-Logik                 │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 10.2 Technische Umsetzung: Testumgebung

Die Tests nutzen eine **vollständig isolierte, kurzlebige Umgebung** — analog zum bestehenden `backup_restore_test.sh`-Muster.

#### Docker-Compose-Testumgebung

```yaml
# docker-compose.update-test.yml
#
# Isolierte Testumgebung für Update-Integrationstests.
# Nutzt eigenes Netzwerk, eigene Volumes, eigene Ports.
# Wird nach Testlauf vollständig aufgeräumt.

services:
  db-update-test:
    image: erechnung-postgres:${OLD_VERSION:-latest}
    tmpfs: /var/lib/postgresql/data    # RAM-Disk — kein Einfluss auf Prod
    environment:
      POSTGRES_DB: erechnung_update_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    networks: [update-test]
    deploy:
      resources:
        limits: { memory: 256M }

  redis-update-test:
    image: redis:7-alpine
    tmpfs: /data
    networks: [update-test]

  web-old:
    image: erechnung-web:${OLD_VERSION}
    depends_on: [db-update-test, redis-update-test]
    environment:
      DATABASE_URL: postgres://test:test@db-update-test:5432/erechnung_update_test
      REDIS_URL: redis://redis-update-test:6379/0
    networks: [update-test]

  web-new:
    image: erechnung-web:${NEW_VERSION}
    depends_on: [db-update-test, redis-update-test]
    profiles: ["upgrade-phase"]
    environment:
      DATABASE_URL: postgres://test:test@db-update-test:5432/erechnung_update_test
      REDIS_URL: redis://redis-update-test:6379/0
    networks: [update-test]

networks:
  update-test:
    driver: bridge

volumes:
  update-test-backup:            # Temporäres Backup-Volume
```

#### K3s-Testumgebung

Für Kubernetes-Tests wird ein **separater Namespace** mit eigenem State verwendet:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: erechnung-update-test
  labels:
    purpose: integration-test
    pod-security.kubernetes.io/enforce: baseline
```

Alle K3s-Update-Tests deployen in diesen Namespace, verwenden eigene PVCs (tmpfs-backed oder emptyDir) und werden nach Abschluss vollständig bereinigt.

### 10.3 Ebene 1: Skript-Unit-Tests

Jede Funktion der Update-Skripte wird isoliert getestet.

| Test-ID | Testfall | Erwartetes Ergebnis |
|---|---|---|
| S-01 | Pre-Flight: Docker Daemon läuft nicht | Exit-Code 1, verständliche Fehlermeldung |
| S-02 | Pre-Flight: Unzureichender Speicherplatz (< 2 GB) | Exit-Code 1, Angabe des freien/benötigten Speichers |
| S-03 | Pre-Flight: docker-compose.yml nicht gefunden | Exit-Code 1, Pfadhinweis |
| S-04 | Pre-Flight: Ziel-Version identisch mit aktueller Version | Exit-Code 0, Hinweis "Bereits auf Version X" |
| S-05 | Pre-Flight: Cluster nicht erreichbar (K3s) | Exit-Code 1, kubectl-Fehlermeldung |
| S-06 | Pre-Flight: Node NotReady (K3s) | Exit-Code 1, betroffene Nodes auflisten |
| S-07 | Versionserkennung: Version aus laufendem Container lesen | Korrekte SemVer zurückgeben |
| S-08 | Versionserkennung: Version aus Image-Label lesen | Korrekte SemVer zurückgeben |
| S-09 | Image-Tagging: :pre-update Tag wird gesetzt | Altes Image unter :pre-update verfügbar |
| S-10 | Backup-Aufruf: backup.sh wird mit --all aufgerufen | Exit-Code von backup.sh wird durchgereicht |
| S-11 | Backup-Aufruf: Backup-Fehler bricht Update ab | Update wird nicht fortgesetzt |
| S-12 | Kustomization-Update: newTag wird korrekt ersetzt | YAML-Datei enthält neuen Tag, Rest unverändert |

**Implementierung**: Shell-basiert (bats-core Framework) oder Python (pytest + subprocess).

### 10.4 Ebene 2: Migrations-Integrationstests

Diese Tests validieren, dass DB-Migrationen korrekt, vollständig und reversibel angewandt werden — auf realistischen Datenbeständen.

#### 10.4.1 Forward-Migration-Tests

| Test-ID | Testfall | Vorbedingung | Assertion |
|---|---|---|---|
| M-01 | Leere DB → aktuelle Version | Leere PostgreSQL-DB | Alle Migrationen [X], Schema vollständig |
| M-02 | v1.0.0-Schema → v1.1.0 | DB mit v1.0.0-Schema + Testdaten | Neue Felder vorhanden, Altdaten intakt |
| M-03 | Migration mit 10.000 Rechnungen | DB mit Massendaten (Fixtures) | Migration < 60s, keine Locks > 5s |
| M-04 | Migration mit NULL-Werten in neuen Pflichtfeldern | Altdaten ohne Werte für neue Felder | Default-Werte korrekt gesetzt |
| M-05 | Migration mit UTF-8-Sonderzeichen in Geschäftspartner-Namen | Umlaute, CJK, Emoji in Daten | Daten nach Migration bitgenau identisch |
| M-06 | Migration mit maximal langen Feldwerten | Alle VARCHAR-Felder am Limit | Migration erfolgreich, keine Truncation |
| M-07 | Idempotenz: Migration zweimal ausführen | Bereits migrierte DB | Keine Fehler, keine Duplikate |
| M-08 | Data-Migration: Batch-Verarbeitung | 50.000 Datensätze | Daten in Batches à 1000 verarbeitet, Fortschrittsmeldung |

#### 10.4.2 Backward-Migration-Tests (Rollback)

| Test-ID | Testfall | Vorbedingung | Assertion |
|---|---|---|---|
| M-10 | Rollback aktuellste Migration | DB auf neuestem Stand | Vorherige Schema-Version korrekt, Daten bis auf entfernte Felder intakt |
| M-11 | Rollback über mehrere Migrationen | DB auf v1.2.0 | Rollback auf v1.0.0 Schema: alle Zwischen-Rollbacks korrekt |
| M-12 | Rollback einer Data-Migration | Geladene Fixture-Daten | Daten nach Rollback im ursprünglichen Zustand |
| M-13 | Rollback nach fehlgeschlagener Forward-Migration | Migration bricht mittendrin ab | DB in konsistentem Zustand (Transaktion zurückgerollt) |
| M-14 | Ping-Pong: Forward → Rollback → Forward | Beliebiger Stand | Daten nach erneutem Forward identisch mit erstem Forward |

#### 10.4.3 Schema-Kompatibilitätstests

| Test-ID | Testfall | Assertion |
|---|---|---|
| M-20 | Alter Code + neues Schema (nach AddField) | API-Endpoints antworten korrekt, neue Felder ignoriert |
| M-21 | Neuer Code + altes Schema (vor Migration) | Startup schlägt nicht fehl, saubere Fehlermeldung wenn Migration ausstehend |
| M-22 | `migrate --plan` zeigt konsistenten Plan | Geplante Operationen sind alle Zero-Downtime-kompatibel |
| M-23 | Keine unangewandten Migrationen nach Update | `showmigrations` zeigt keine `[ ]` Einträge |

### 10.5 Ebene 3: Komponenten-Integrationstests

Diese Tests validieren die Zusammenarbeit der Update-Phasen (Backup → Migration → Neustart → Verifikation).

#### 10.5.1 Docker-Only Komponententests

| Test-ID | Testfall | Ablauf | Assertion |
|---|---|---|---|
| D-01 | **Happy Path: Vollständiges Update** | Alte Version starten → Testdaten anlegen → Update-Skript ausführen → Verifizieren | Neue Version läuft, Daten intakt, Backup vorhanden |
| D-02 | **Backup-Verifizierung vor Update** | Update starten | Backup erstellt + SHA256-verifiziert bevor irgendein Container gestoppt wird |
| D-03 | **Init-Container-Migration** | Neue Container starten | Init-Container läuft migrate + collectstatic, Exit-Code 0, danach Web startet |
| D-04 | **Health Check nach Update** | Update abgeschlossen | `/api/health/` → 200, `/api/version/` → Ziel-Version |
| D-05 | **Graceful Shutdown** | Web-Container stoppen | Laufende HTTP-Requests werden zu Ende bearbeitet (10s Grace Period) |
| D-06 | **Volume-Persistenz** | Container down → Container up | PostgreSQL-Daten, Redis-Daten, Media-Dateien intakt |
| D-07 | **Static Files nach Update** | collectstatic in Init-Container | Neue CSS/JS-Dateien im API-Gateway verfügbar, alte gecacht |
| D-08 | **Celery-Worker Reconnect** | Worker nach Redis-Neustart | Worker verbindet sich automatisch, pending Tasks werden abgearbeitet |

#### 10.5.2 Kubernetes Komponententests

| Test-ID | Testfall | Ablauf | Assertion |
|---|---|---|---|
| K-01 | **Happy Path: Rolling Update** | kubectl apply mit neuen Image-Tags | Alte Pods laufen bis neue Pods Ready, kein 5xx |
| K-02 | **Migrations-Job vor Rollout** | Job deployen → Warten → Rollout | Job completions=1, danach erst Deployment-Update |
| K-03 | **Rollout Status** | kubectl rollout status | Alle Pods auf neuer Version, Deployment condition=Available |
| K-04 | **Pod Disruption Budget** | Node drain während Update | minAvailable=1 respektiert, mindestens 1 Pod beantwortet Requests |
| K-05 | **Readiness Probe blockiert Traffic** | Neuer Pod startet | Kein Traffic an neuen Pod bevor /health/ → 200 |
| K-06 | **Service Continuity während Rollout** | HTTP-Requests während Update senden | 0% Request-Fehlerrate (gemessen über 100 Requests) |
| K-07 | **ConfigMap/Secret Update** | Konfigurationsänderung | Pods werden neu deployt, neue Konfiguration aktiv |
| K-08 | **PVC bleibt intakt** | Postgres-Pod neustarten | Daten auf PVC nach Restart vorhanden |

### 10.6 Ebene 4: Full-Stack Update-Simulationen (E2E)

Diese Tests simulieren komplette Update-Szenarien von der alten zur neuen Version — inkl. Frontend, API, Datenbank und Gateway.

#### 10.6.1 Docker-Only E2E-Szenarien

**E2E-D-01 — Standard-Update v1.0.0 → v1.1.0**

- Schritte:
  1. v1.0.0 starten, Testdaten anlegen
  2. Rechnungen erstellen (5 Stück)
  3. PDF-Export einer Rechnung
  4. Update-Skript auf v1.1.0 ausführen
  5. Login als Admin + Testuser
- Verifikation: Alle 5 Rechnungen vorhanden, PDFs abrufbar, neue Features verfügbar

**E2E-D-02 — Update mit Rollback**

- Schritte:
  1. v1.0.0 mit Daten
  2. Update auf v1.1.0
  3. Simulierten Fehler auslösen
  4. Rollback-Skript ausführen
- Verifikation: v1.0.0 wieder aktiv, alle Daten aus Pre-Update-Backup wiederhergestellt

**E2E-D-03 — Multi-Step Update v1.0 → v1.1 → v1.2**

- Schritte:
  1. v1.0.0 starten
  2. Update auf v1.1.0
  3. Zwischen-Verifizierung
  4. Update auf v1.2.0
- Verifikation: Alle Migrationen kumulativ angewandt, Daten nach jedem Schritt intakt

**E2E-D-04 — Update mit großem Datenbestand**

- Schritte:
  1. 10.000 Rechnungen + 500 Geschäftspartner anlegen
  2. Update durchführen
- Verifikation: Update-Dauer dokumentiert, Datenintegrität vollständig, kein OOM

**E2E-D-05 — Update bei laufendem Celery-Task**

- Schritte:
  1. Langlebigen Celery-Task starten
  2. Update initiieren
- Verifikation: Task wird zu Ende bearbeitet oder sauber abgebrochen, kein Datenverlust

#### 10.6.2 Kubernetes E2E-Szenarien

**E2E-K-01 — Zero-Downtime Rolling Update**

- Schritte:
  1. v1.0.0 deployen
  2. Kontinuierliche HTTP-Requests starten (Lastgenerator)
  3. Rolling Update auf v1.1.0
  4. Lastgenerator-Ergebnisse auswerten
- Verifikation: 0 fehlgeschlagene Requests, alle Pods auf neuer Version

**E2E-K-02 — Automatischer Rollback bei Health-Fehler**

- Schritte:
  1. v1.0.0 deployen
  2. Image deployen das bei /health/ → 500 antwortet
  3. Warten auf progressDeadlineSeconds
- Verifikation: Alte Pods bleiben aktiv, neue Pods werden nicht Ready, Deployment-Condition: Progressing=False

**E2E-K-03 — Manueller Rollback mit kubectl**

- Schritte:
  1. v1.1.0 deployen
  2. `kubectl rollout undo`
  3. Status prüfen
- Verifikation: v1.0.0 wieder aktiv, Daten intakt

**E2E-K-04 — DB-Migration-Job schlägt fehl → Update blockiert**

- Schritte:
  1. Defekte Migration als Job submiten
  2. Job-Status prüfen
  3. Deployment-Update darf nicht starten
- Verifikation: Job status=Failed, Deployments bleiben auf alter Version

**E2E-K-05 — Paralleler Traffic während Update**

- Schritte:
  1. 10 parallele Clients simulieren
  2. Rolling Update starten
- Verifikation: Keine Verbindungsabbrüche, Session-Cookies bleiben gültig

### 10.7 Edge-Case-Tests

Systematische Absicherung von Grenzfällen, die im Normalbetrieb selten, aber im Fehlerfall kritisch sind.

#### 10.7.1 Infrastruktur-Edge-Cases

| Test-ID | Edge Case | Simulation | Erwartetes Verhalten |
|---|---|---|---|
| EC-01 | **Netzwerk-Abbruch während Image-Pull** | `iptables`-Regel: Docker Hub blockieren nach 50% Download | Retry-Logik greift, Update pausiert mit Meldung, kein korruptes Image |
| EC-02 | **Speicherplatz läuft voll während Update** | tmpfs mit 100 MB Limit | Pre-Flight-Check erkennt Problem VOR dem Update; falls während Update: sauberer Abbruch |
| EC-03 | **Stromausfall / Kill -9 während Migration** | `docker kill` während migrate-Befehl | DB in konsistentem Zustand (Transaktions-Rollback), nächster Start erkennt ausstehende Migration |
| EC-04 | **Paralleles Update (Race Condition)** | Zwei Update-Skripte gleichzeitig starten | Lock-Mechanismus: Zweiter Aufruf bricht ab mit Hinweis auf laufendes Update |
| EC-05 | **Container-OOM während Migration** | Memory-Limit 64M für Migrations-Container | Container wird gekillt, kein Datenverlust (Transaktions-Safety), klarer OOM-Hinweis im Log |
| EC-06 | **DNS-Auflösung fehlerhaft (K3s)** | CoreDNS-Pod löschen während Update | Update schlägt fehl mit klarer Meldung, Rollback auf Netzwerk-Ebene |
| EC-07 | **Registry nicht erreichbar (K3s)** | Lokale Registry (Port 5000) stoppen | Image-Pull schlägt fehl, Pods bleiben auf alter Version, ErrImagePull-Status sichtbar |

#### 10.7.2 Daten-Edge-Cases

| Test-ID | Edge Case | Testdaten | Erwartetes Verhalten |
|---|---|---|---|
| EC-10 | **Leere Datenbank (Erstinstallation → Update)** | DB mit nur Superuser, keine Rechnungen | Migration + Update erfolgreich, kein Division-by-Zero o.Ä. |
| EC-11 | **DB mit manuell geänderten Constraints** | Extra-Index auf invoice-Tabelle | Migration erkennt oder ignoriert unbekannte Objekte, kein Crash |
| EC-12 | **Inkonsistenter Backup-Zustand** | Korruptes Backup (SHA256 stimmt nicht) | Backup-Verifizierung schlägt fehl, Update wird abgebrochen |
| EC-13 | **Alte DB-Version ohne bestimmte Migration** | DB auf Migration 0003, Update erwartet 0005 | Kumulative Migration 0003→0004→0005 korrekt, Reihenfolge gewahrt |
| EC-14 | **Media-Dateien mit Sonderzeichen im Dateinamen** | Rechnungs-PDF mit `Rechnung (Kopie).pdf` | Backup + Restore inkl. Sonderzeichen, keine Pfad-Escaping-Fehler |
| EC-15 | **Concurrent Write während Migration** | Rechnung anlegen WÄHREND migrate läuft | Kein Deadlock, Schreibvorgang wartet oder schlägt verständlich fehl |
| EC-16 | **GoBD-gesperrte Rechnungen** | is_locked=True Rechnungen in DB | Gesperrte Rechnungen nach Update unverändert, content_hash stimmt |

#### 10.7.3 Versions-Edge-Cases

| Test-ID | Edge Case | Szenario | Erwartetes Verhalten |
|---|---|---|---|
| EC-20 | **Downgrade-Versuch (v1.2 → v1.1)** | Ziel-Version < aktuelle Version | Klare Fehlermeldung: "Downgrade nicht unterstützt. Nutzen Sie Rollback." |
| EC-21 | **MAJOR-Version-Sprung ohne Zwischenschritt** | v1.0 direkt auf v2.0 | Warnung mit Verweis auf vorgeschriebenen Update-Pfad |
| EC-22 | **Gleiche Version erneut einspielen** | v1.1.0 → v1.1.0 | No-Op: Meldung "Bereits auf Version 1.1.0", kein Backup, kein Restart |
| EC-23 | **Unbekannte Version angegeben** | --version v9.9.9 (existiert nicht) | Fehlermeldung: "Version v9.9.9 nicht gefunden", kein Download-Versuch |
| EC-24 | **pyproject.toml nicht lesbar** | Datei fehlt oder defekt | Fallback auf Image-Label, Warnung im Log |

### 10.8 Test-Orchestrierung und Ausführung

#### 10.8.1 Skript: `scripts/run-update-tests.sh`

Zentrales Orchestrierungs-Skript für alle Update-Integrationstests:

```bash
# Alle Tests ausführen (Standard vor produktivem Update)
./scripts/run-update-tests.sh --all

# Nur eine Test-Ebene
./scripts/run-update-tests.sh --level 1          # Skript-Unit-Tests
./scripts/run-update-tests.sh --level 2          # Migrations-Tests
./scripts/run-update-tests.sh --level 3          # Komponenten-Tests
./scripts/run-update-tests.sh --level 4          # Full-Stack E2E

# Bestimmte Test-IDs
./scripts/run-update-tests.sh --test M-01,M-02,D-01

# Nur Edge-Cases
./scripts/run-update-tests.sh --edge-cases

# Docker-Only oder nur K3s-Tests
./scripts/run-update-tests.sh --docker-only
./scripts/run-update-tests.sh --k3s-only

# Versionen explizit angeben
./scripts/run-update-tests.sh --old-version v1.0.0 --new-version v1.1.0

# Verbose / Debug-Modus
./scripts/run-update-tests.sh --all --verbose
```

**Ablauf des Orchestrierungs-Skripts:**

```txt
run-update-tests.sh
├── 1. Testumgebung aufbauen
│   ├── docker-compose.update-test.yml hochfahren
│   ├── (K3s) Namespace erechnung-update-test anlegen
│   └── Warten auf DB-Readiness
│
├── 2. Tests ausführen (sequenziell je Ebene)
│   ├── Ebene 1: Skript-Unit-Tests
│   │   └── bats / pytest Testrunner
│   ├── Ebene 2: Migrations-Tests
│   │   └── manage.py migrate + inspect in Temp-DB
│   ├── Ebene 3: Komponenten-Tests
│   │   └── Update-Ablauf in isolierter Umgebung
│   └── Ebene 4: E2E-Tests
│       └── Multi-Container-Szenario (alt → neu)
│
├── 3. Ergebnisse sammeln
│   ├── JUnit-XML Report (CI-kompatibel)
│   ├── HTML Summary Report
│   └── Log-Dateien je Testfall
│
├── 4. Testumgebung aufräumen
│   ├── docker compose -f docker-compose.update-test.yml down -v
│   ├── (K3s) kubectl delete namespace erechnung-update-test
│   └── Temporäre Dateien löschen
│
└── 5. Exit-Code
    ├── 0 = Alle Tests bestanden
    ├── 1 = Mindestens ein Test fehlgeschlagen
    └── 2 = Infrastruktur-Fehler (Testumgebung konnte nicht starten)
```

#### 10.8.2 Einbindung in den Update-Prozess

Die Integrationstests sind ein **obligatorischer Gate** im Update-Ablauf:

```txt
┌───────────────────────────────────────────────────────────────────┐
│                    Update-Prozess mit Test-Gate                   │
│                                                                   │
│  1. Release vorbereiten (neue Version bauen)                      │
│                         │                                         │
│  2. ┌───────────────────▼──────────────────────┐                  │
│     │   run-update-tests.sh --all              │                  │
│     │   --old-version <AKTUELL>                │                  │
│     │   --new-version <ZIEL>                   │                  │
│     └──────────┬──────────────┬────────────────┘                  │
│                │              │                                    │
│           BESTANDEN       FEHLGESCHLAGEN                          │
│                │              │                                    │
│  3. Update     ▼         Abbruch ▼                                │
│     durchführen           → Fehler analysieren                    │
│                           → Fix implementieren                    │
│                           → Tests erneut ausführen                │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

**Für den Docker-Only-Update-Prozess** (Kap. 3.3):

- Tests laufen auf dem gleichen Host vor dem eigentlichen Update
- Nutzen eigene Container und eigenes Netzwerk (kein Einfluss auf Produktion)
- Dauer: ca. 5-15 Minuten je nach Umfang

**Für den K3s-Update-Prozess** (Kap. 4.5):

- Tests laufen im separaten Namespace `erechnung-update-test`
- Nutzen eigene PVCs und Services
- Können auch in einem CI-System (GitHub Actions) ausgeführt werden

#### 10.8.3 CI/CD-Integration

Ein GitHub Actions Workflow führt die Tests automatisch bei jedem Release-Kandidaten aus:

```yaml
# .github/workflows/update-integration-tests.yml
#
# Trigger: Push eines Release-Tags (v*.*.*)
# Oder: Manuell per workflow_dispatch

name: Update Integration Tests
on:
  push:
    tags: ['v*.*.*']
  workflow_dispatch:
    inputs:
      old_version:
        description: 'Quell-Version'
        required: true
      new_version:
        description: 'Ziel-Version'
        required: true

jobs:
  update-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
    steps:
      - uses: actions/checkout@v4
      - name: Run Update Integration Tests
        run: ./scripts/run-update-tests.sh --all
        env:
          OLD_VERSION: ${{ inputs.old_version || 'latest' }}
          NEW_VERSION: ${{ github.ref_name }}
      - name: Upload Test Reports
        uses: actions/upload-artifact@v4
        with:
          name: update-test-reports
          path: test-artifacts/update-tests/
```

### 10.9 Test-Daten-Strategie

Reproduzierbares Testen erfordert definierte Testdaten.

#### 10.9.1 Fixture-Sets

| Fixture-Set | Inhalt | Zweck |
|---|---|---|
| `minimal` | 1 Company, 1 Geschäftspartner, 1 Rechnung | Schnelle Smoke-Tests |
| `standard` | 2 Companies, 10 Partner, 50 Rechnungen (inkl. Positionen, Anhänge) | Reguläre Funktionstests |
| `stress` | 5 Companies, 500 Partner, 10.000 Rechnungen, 2.000 Audit-Einträge | Lasttests und Performance-Migrationen |
| `edge` | Sonderzeichen, max. Feldlängen, GoBD-gesperrte Rechnungen, alle Steuer-Kategorien | Edge-Case-Coverage |
| `empty` | Nur Superuser + Standardkonfiguration | Erstinstallations-Szenarien |

#### 10.9.2 Fixture-Erzeugung

```bash
# Fixtures als JSON exportieren (für Reproduzierbarkeit)
docker compose exec web python project_root/manage.py dumpdata \
  --indent 2 --natural-foreign --natural-primary \
  -e contenttypes -e auth.permission \
  > test-artifacts/update-tests/fixtures/standard.json

# Fixtures laden in Test-DB
docker compose -f docker-compose.update-test.yml exec web-old \
  python project_root/manage.py loaddata \
  test-artifacts/update-tests/fixtures/standard.json
```

Alternativ nutzt die bestehende `generate_test_data`-Management-Command für dynamische Testdaten.

### 10.10 Reporting und Ergebnis-Auswertung

#### Test-Report-Formate

| Format | Datei | Zweck |
|---|---|---|
| JUnit XML | `test-artifacts/update-tests/junit.xml` | CI/CD-Integration (GitHub Actions, Jenkins) |
| HTML Summary | `test-artifacts/update-tests/report.html` | Menschenlesbar, mit Pass/Fail pro Testfall |
| JSON Detail | `test-artifacts/update-tests/results.json` | Maschinell auswertbar, für Trend-Analysen |
| Log-Dateien | `test-artifacts/update-tests/logs/<TEST-ID>.log` | Detailed Debug-Output je Testfall |

#### Beispiel-Output

```txt
╔══════════════════════════════════════════════════════════════════╗
║           Update Integration Test Report                        ║
║           v1.0.0 → v1.1.0 | 17.03.2026 14:32                 ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Ebene 1: Skript-Unit-Tests          12/12 ✅  (8s)            ║
║  Ebene 2: Migrations-Tests           14/14 ✅  (45s)           ║
║  Ebene 3: Komponenten-Tests           8/8  ✅  (3m 12s)        ║
║  Ebene 4: E2E Full-Stack              5/5  ✅  (7m 40s)        ║
║  Edge-Cases                          17/17 ✅  (4m 55s)        ║
║                                                                  ║
║  Gesamt: 56/56 bestanden | Dauer: 16m 40s                      ║
║  Status: ✅ UPDATE FREIGEGEBEN                                  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### 10.11 Erstmalige Validierung der Testsuite

Bevor die Testsuite produktiv genutzt wird, durchläuft sie selbst eine Validierung:

| Phase | Aktion | Erfolgskriterium |
|---|---|---|
| 1. Entwicklung | Tests auf Dev-Umgebung implementieren und debuggen | Alle Tests bestehen auf sauberer Umgebung |
| 2. Negativ-Test | Absichtlich fehlerhafte Updates durchführen | Tests erkennen die Fehler zuverlässig (keine False Positives) |
| 3. Mutationstests | Migrations-Dateien absichtlich manipulieren | Tests schlagen fehl (keine False Negatives) |
| 4. Performance-Baseline | Tests mit `stress`-Fixture-Set auf Referenz-Hardware ausführen | Zeitlimits kalibrieren, Ober- und Untergrenzen festlegen |
| 5. Dokumentation | Test-IDs, Erwartungswerte und Laufzeiten dokumentieren | Testsuite-Handbuch vollständig |

---

## 11. Offene Punkte für Implementierung

### 11.1 Zu implementieren: Skripte

| Priorität | Aufgabe | Beschreibung | Geschätzter Aufwand |
|---|---|---|---|
| **HOCH** | `scripts/update-docker.sh` | Vollautomatisches Docker-Update-Skript (Kap. 3.3) | — |
| **HOCH** | `scripts/rollback-docker.sh` | Docker-Rollback auf Pre-Update-Backup | — |
| **HOCH** | `scripts/update-k3s.sh` | K3s-Update-Skript (erweitert k3s-update-images.sh, Kap. 4.5) | — |
| MITTEL | Pre-Flight-Check-Modul | Wiederverwendbare Prüfungen für beide Szenarien | — |
| MITTEL | Wartungsseite (HTML) | Statische Seite für API-Gateway während Update | — |
| NIEDRIG | Canary-Deployment-Support | Ingress-Annotations für Traffic-Splitting (K8s) | — |

### 11.2 Zu implementieren: Integrationstests

| Priorität | Aufgabe | Beschreibung | Geschätzter Aufwand |
|---|---|---|---|
| **HOCH** | `docker-compose.update-test.yml` | Isolierte Testumgebung für Update-Integrationstests (Kap. 10.2) | — |
| **HOCH** | `scripts/run-update-tests.sh` | Orchestrierungs-Skript für alle Testebenen (Kap. 10.8.1) | — |
| **HOCH** | Ebene 1: Skript-Unit-Tests (S-01 bis S-12) | Unit-Tests für Pre-Flight, Versioning, Backup-Aufruf, Tagging (Kap. 10.3) | — |
| **HOCH** | Ebene 2: Migrations-Tests (M-01 bis M-23) | Forward-, Backward-, Kompatibilitätstests auf realer DB (Kap. 10.4) | — |
| **HOCH** | Ebene 3: Docker Komponententests (D-01 bis D-08) | Update-Phasen einzeln + kombiniert in Containern (Kap. 10.5.1) | — |
| **HOCH** | Ebene 3: K3s Komponententests (K-01 bis K-08) | Rolling Update, PDB, Readiness im Test-Namespace (Kap. 10.5.2) | — |
| **HOCH** | Ebene 4: E2E Docker (E2E-D-01 bis E2E-D-05) | Full-Stack Update-Simulation Docker-Only (Kap. 10.6.1) | — |
| **HOCH** | Ebene 4: E2E K3s (E2E-K-01 bis E2E-K-05) | Full-Stack Update-Simulation Kubernetes (Kap. 10.6.2) | — |
| **HOCH** | Edge-Case-Tests (EC-01 bis EC-24) | Infrastruktur-, Daten- und Versions-Grenzfälle (Kap. 10.7) | — |
| MITTEL | Fixture-Sets (minimal, standard, stress, edge, empty) | Reproduzierbare Testdaten für alle Szenarien (Kap. 10.9) | — |
| MITTEL | CI-Workflow: `update-integration-tests.yml` | GitHub Actions Workflow für automatische Tests bei Releases (Kap. 10.8.3) | — |
| MITTEL | Testsuite-Selbstvalidierung | Negativ-Tests + Mutationstests für die Testsuite selbst (Kap. 10.11) | — |
| MITTEL | Reporting: JUnit XML + HTML Summary | Ergebnis-Reports für CI und manuelle Auswertung (Kap. 10.10) | — |

### 11.3 Zu implementieren: Applikation

| Priorität | Aufgabe | Beschreibung |
|---|---|---|
| **HOCH** | `/api/version/` Endpoint | Gibt aktuelle Applikationsversion zurück (aus pyproject.toml) |
| **HOCH** | `CHANGELOG.md` | Initiales Changelog mit v1.0.0 anlegen |
| MITTEL | Image-Labels | `LABEL version=<VERSION>` im Dockerfile für Versionserkennung |
| MITTEL | Database-Schema-Version-Check | Beim Start prüfen ob alle Migrationen angewandt sind |

### 11.4 Zu implementieren: Kubernetes-Manifeste

| Priorität | Aufgabe | Beschreibung |
|---|---|---|
| **HOCH** | `strategy.rollingUpdate` | In alle Deployments explizite Update-Strategie einfügen |
| **HOCH** | `PodDisruptionBudget` | PDBs für django-web und api-gateway |
| MITTEL | `revisionHistoryLimit` | Auf 5 setzen für Rollback-Historie |
| MITTEL | Migrations-Job-Template | Wiederverwendbares Job-Manifest für DB-Migrationen |
| NIEDRIG | VolumeSnapshot-CRDs | Für Postgres-PVC-Snapshots vor Update |

### 11.5 Zu implementieren: Dokumentation

| Priorität | Aufgabe | Beschreibung |
|---|---|---|
| **HOCH** | Update-Anleitung im User Manual | Kapitel in `docs/USER_MANUAL.md` für Endanwender |
| MITTEL | PostgreSQL Major-Upgrade-Anleitung | Separates Dokument für PG 17 → 18 Upgrade-Pfad |
| NIEDRIG | Disaster-Recovery-Playbook | Schritt-für-Schritt für Total-Ausfall-Szenarien |

---

## Anhang A: Vergleich der beiden Szenarien

| Aspekt | Docker-Only (KMU) | Kubernetes (Enterprise) |
|---|---|---|
| **Downtime** | 2-5 Min (akzeptabel) | Zero-Downtime (Rolling Update) |
| **Automatisierungsgrad** | Skript-gesteuert | Deklarativ (kubectl apply) |
| **Rollback** | Manuell (Skript) | Automatisch (Readiness Probe) |
| **Backup** | pg_dump + tar.gz | pg_dump + VolumeSnapshot |
| **Image-Quelle** | Docker Hub oder lokaler Build | Lokale Registry (192.168.178.80:5000) |
| **Migrations-Ausführung** | Init-Container beim Start | Separater Kubernetes Job |
| **Monitoring-Integration** | Logs + Health Check | Prometheus + Grafana + Alerting |
| **Multi-Version parallel** | Nein | Möglich (Canary) |
| **Update-Trigger** | Admin führt Skript aus | Admin oder CI/CD-Pipeline |
| **Komplexität** | Niedrig | Mittel-Hoch |
| **Voraussetzungen** | Docker + Docker Compose | K3s-Cluster + kubectl + Registry |

---

## Anhang B: Glossar

| Begriff | Bedeutung |
|---|---|
| **Rolling Update** | Pods werden einzeln ersetzt — zu jedem Zeitpunkt sind genug Pods aktiv |
| **Canary Deployment** | Neue Version wird zuerst für kleinen Anteil des Traffics ausgerollt |
| **PDB (Pod Disruption Budget)** | Legt fest, wie viele Pods gleichzeitig offline sein dürfen |
| **Readiness Probe** | Kubernetes prüft ob ein Pod bereit ist, Traffic zu empfangen |
| **Liveness Probe** | Kubernetes prüft ob ein Pod noch lebt (Neustart bei Fehler) |
| **Init-Container** | Container der einmalig vor dem Hauptcontainer läuft (z.B. für Migrationen) |
| **Kustomize** | Kubernetes-natives Tool zum Anpassen von Manifesten ohne Templates |
| **SemVer** | Semantic Versioning — `MAJOR.MINOR.PATCH` |
| **Pre-Flight Check** | Vorab-Prüfungen bevor der eigentliche Update-Prozess startet |
| **Expand/Contract** | 3-Phasen-Pattern für rückwärtskompatible Schema-Änderungen |
