# Production & Operations Guide

> **Letzte Aktualisierung:** 14. März 2026
> **Quellen:** DISASTER_RECOVERY.md, HTTPS_SETUP.md, KUBERNETES_DEPLOYMENT_OPTIONS.md, SAFE_UPDATE_STRATEGY.md (konsolidiert)

---

## Inhalt

1. [Deployment-Umgebungen](#1-deployment-umgebungen)
2. [HTTPS / TLS Setup](#2-https--tls-setup)
3. [Backup & Disaster Recovery](#3-backup--disaster-recovery)
4. [Dependency-Update-Strategie](#4-dependency-update-strategie)
5. [Monitoring & Alerting](#5-monitoring--alerting)
6. [Incident Response](#6-incident-response)
7. [Compliance-Betrieb](#7-compliance-betrieb)

---

## 1. Deployment-Umgebungen

Zwei unabhängige Installationen mit identischer Funktionalität:

| Umgebung | URL | Basis | Beschreibung |
|----------|-----|-------|--------------|
| **Entwicklung** | http://localhost:5173 | Docker Compose | Lokale Entwicklung, Hot-Reload |
| **Kubernetes** | http://192.168.178.80 | k3s (lokal) | Remote-Rechner, produktionsnah |

### Entwicklung starten (Docker Compose)

```bash
docker compose up -d
# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
```

### Kubernetes starten (k3s)

```bash
export KUBECONFIG=~/.kube/config-k3s-local
kubectl apply -k infra/k8s/k3s/
# Zugriff: http://192.168.178.80
```

**Wichtig:** Die Umgebungen sind vollständig getrennt — eigene DB, eigener Redis, eigenes Backend.
Keine gegenseitigen Abhängigkeiten.

### Kubernetes-Setup (k3s auf 192.168.178.80)

k3s ist die empfohlene Variante für produktionsnahes Testing (kostenlos, volle MetalLB-Unterstützung).

```bash
# Erstinstallation auf 192.168.178.80
curl -sfL https://get.k3s.io | sh -

# kubeconfig exportieren
sudo cat /etc/rancher/k3s/k3s.yaml > ~/.kube/config-k3s-local
sed -i 's|127.0.0.1|192.168.178.80|g' ~/.kube/config-k3s-local

# MetalLB installieren
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml
kubectl apply -f infra/k8s/k3s/metallb-lan-config.yaml
```

MetalLB vergibt IPs aus dem Pool `192.168.178.200–192.168.178.210` (LAN).

**Cloud-Alternativen** (nur falls k3s lokal nicht ausreicht):
- **Hetzner CX21 + k3s**: ~€0.007/Stunde, pausierbar (~€0.50/Monat bei Stopp)
- **IONOS Managed K8s**: ~€90/Monat, nicht empfohlen für gelegentliche Tests

---

## 2. HTTPS / TLS Setup

Das API-Gateway (nginx) übernimmt die TLS-Terminierung. Interne Dienste kommunizieren unverschlüsselt.

### Zertifikate generieren (Entwicklung)

```bash
cd infra/api-gateway
./generate-certs.sh
docker compose restart api-gateway
```

Selbst-signierte Zertifikate für `localhost` (RSA 2048-bit, 10 Jahre, SANs: `localhost`, `api-gateway`, `*.localhost`, `127.0.0.1`, `::1`).

### Zertifikat im Browser akzeptieren

**Firefox:** Einstellungen → Datenschutz & Sicherheit → Zertifikate → Zertifizierungsstellen → Importieren → `infra/api-gateway/certs/localhost.crt`

**Chrome/Chromium:** Einstellungen → Datenschutz → Sicherheit → Zertifikate verwalten → Zertifizierungsstellen → Importieren

**Linux system-weit (optional):**
```bash
sudo cp infra/api-gateway/certs/localhost.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

### URLs

| Umgebung | Frontend | API | Admin |
|----------|----------|-----|-------|
| Entwicklung (Vite) | http://localhost:5173 | https://localhost/api | https://localhost/admin |
| Produktion (Build) | https://localhost | https://localhost/api | https://localhost/admin |

### Django HTTPS-Einstellungen

In `project_root/invoice_project/settings.py` sind bereits gesetzt:

```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

### Troubleshooting

| Problem | Lösung |
|---------|--------|
| `NET::ERR_CERT_AUTHORITY_INVALID` | Zertifikat im Browser importieren (s. o.) |
| API-Anfragen schlagen fehl | `docker logs erechnung_api-gateway` |
| Nginx-Konfigurationsfehler | `docker exec erechnung_api-gateway nginx -t` |

---

## 3. Backup & Disaster Recovery

### Recovery-Ziele

| Metrik | Zielwert | Beschreibung |
|--------|----------|--------------|
| **RTO** | < 4 Stunden | Maximale Ausfallzeit |
| **RPO** | < 1 Stunde | Maximaler Datenverlust |
| **MTTR** | < 2 Stunden | Durchschnittliche Wiederherstellungszeit |

### Zu sichernde Komponenten

| Komponente | Kritikalität | Backup-Methode |
|------------|--------------|----------------|
| PostgreSQL Datenbank | **KRITISCH** | `pg_dump` (gzip) |
| Media-Verzeichnis (PDF/XML) | **HOCH** | tar.gz |
| Django Konfiguration (.env) | **HOCH** | Manuell / Git |
| Redis | NIEDRIG | Nicht gesichert (transient) |

### Backup durchführen

```bash
# Vollbackup (DB + Media)
./scripts/backup.sh

# Nur Datenbank
./scripts/backup.sh --db-only

# Via Django Management Command
docker compose exec web python project_root/manage.py backup_database
```

### Backup-Zeitplan (Empfehlung)

| Frequenz | Typ | Retention |
|----------|-----|-----------|
| **Täglich** (02:00) | DB + Media | 30 Tage |
| **Wöchentlich** (So) | Vollbackup | 12 Wochen |
| **Monatlich** | Archiv | 10 Jahre (GoBD) |

**Cron einrichten:**
```bash
# /etc/cron.d/erechnung-backup
0 2 * * * root cd /path/to/eRechnung_Django_App && ./scripts/backup.sh >> /var/log/erechnung-backup.log 2>&1
```

### Backup-Verzeichnisstruktur

```
infra/backups/
├── 20260314/
│   ├── db_20260314_020000.sql.gz
│   ├── db_20260314_020000.sql.gz.sha256
│   ├── media_20260314_020000.tar.gz
│   └── backup_20260314_020000.meta.json
└── pre_restore_20260314_120000/   # Automatischer Sicherheits-Snapshot vor Restore
```

### Restore

```bash
# Neuestes Backup
./scripts/restore.sh --latest

# Bestimmtes Datum
./scripts/restore.sh infra/backups/20260314

# Nur Datenbank
./scripts/restore.sh --db-only infra/backups/20260314

# Dry-Run (prüft ohne zu schreiben)
./scripts/restore.sh --dry-run infra/backups/20260314
```

**Manueller Restore auf neuer Instanz:**
```bash
# 1. DB + Redis starten
docker compose up -d db redis
docker compose exec db pg_isready -U postgres

# 2. Backup einspielen
zcat infra/backups/20260314/db_20260314_020000.sql.gz | \
    docker compose exec -T db psql -U postgres -d erechnung_ci

# 3. Anwendung starten + Migrationen
docker compose up -d web celery frontend
docker compose exec web python project_root/manage.py migrate --noinput
docker compose exec web python project_root/manage.py check --database default
```

### Backup-Restore-Test

```bash
# Vollautomatischer Test (eigener tmpfs-Container, berührt keine Produktiv-DB)
./scripts/backup_restore_test.sh

# Container nach Test behalten (Debug)
./scripts/backup_restore_test.sh --keep

# Bestehendes Backup testen (kein neues Backup)
./scripts/backup_restore_test.sh --skip-backup
```

Empfohlener Testrhythmus: wöchentlich automatisch, monatlich manuell, quartalsweise voller DR-Drill.

### Fehlerbehandlung

| Symptom | Ursache | Lösung |
|---------|---------|--------|
| "Database container not running" | DB-Container gestoppt | `docker compose up -d db` |
| "Checksum FAILED" | Backup-Datei korrupt | Älteres Backup verwenden |
| Django-Migrationen schlagen fehl | Versions-Mismatch | `manage.py migrate` manuell |

**Rollback nach fehlerhaftem Restore:**
```bash
# Pre-Restore-Backup wurde automatisch erstellt:
ls infra/backups/pre_restore_*/
./scripts/restore.sh --force --skip-pre-backup infra/backups/pre_restore_20260314_120000
```

### Kubernetes-spezifische Hinweise

- **PersistentVolumeClaim** für Backup-Storage verwenden
- **CronJob** statt Host-Cron (siehe `infra/k8s/k3s/`)
- Secrets separat sichern (nicht im DB-Dump enthalten)

### Disaster Recovery Drill — Checkliste

- [ ] Backup-Script manuell ausführen und Output prüfen
- [ ] Checksum manuell verifizieren: `sha256sum -c backup.sql.gz.sha256`
- [ ] Automatisierten Restore-Test ausführen: `./scripts/backup_restore_test.sh`
- [ ] Manuellen Restore auf frischer Instanz durchführen
- [ ] Django-Admin nach Restore erreichbar?
- [ ] Frontend-Login nach Restore funktioniert?
- [ ] GoBD-Audit: `docker compose exec web python project_root/manage.py gobd_audit`
- [ ] Recovery-Zeiten dokumentieren (RTO/MTTR messen)

---

## 4. Dependency-Update-Strategie

Abhängigkeiten **nie alle auf einmal** aktualisieren — phasenweise nach Risikoklasse vorgehen.

### Risikoklassen

| Phase | Klasse | Pakete | Risiko |
|-------|--------|--------|--------|
| 1 | Dev-Tools | black, pytest, ruff, coverage, … | Niedrig |
| 2 | Utility-Libs | python-dotenv, whitenoise, sentry-sdk, … | Mittel |
| 3 | Django-Ökosystem | Django (nur Patch!), DRF, debug-toolbar, … | Mittel |
| 4 | Authentifizierung | django-allauth (inkrementell!), django-axes | Hoch |
| 5 | Infrastruktur | celery, redis, gunicorn, psycopg2-binary | Hoch |
| 6 | PDF/XML-Verarbeitung | lxml, pypdf, factur-x, xmlschema | Kritisch |

### Vorgehen pro Phase

```bash
# 1. Backup erstellen
./scripts/backup.sh

# 2. Phase anwenden (requirements.in anpassen)
pip-compile requirements.in

# 3. Im Container installieren
docker compose exec web pip install -r requirements.txt

# 4. Tests laufen lassen — alle müssen grünen bleiben
cd scripts && ./run_tests_docker.sh

# 5. Nur wenn Tests grün: nächste Phase
```

### Bekannte Fallstricke

| Paket | Problem |
|-------|---------|
| Django 5.2.x | Breaking Changes — erst auf 5.1.x (Patch) bleiben |
| django-allauth 65.x+ | Vollständig neues API — nur inkrementell |
| factur-x 3.x | Kann ZUGFeRD-Kompatibilität brechen |
| lxml 6.x | Breaking Changes in XML-Verarbeitung |
| xmlschema 4.x | Validierungsverhalten ändert sich |

---

## 5. Monitoring & Alerting

### Health-Checks

- **Anwendung:** Liveness- und Readiness-Probes
- **Datenbank:** Connection-Pool, Query-Performance
- **Infrastruktur:** CPU/RAM-Auslastung, Netzwerk
- **Sicherheit:** Fehlgeschlagene Logins, ungewöhnliche Aktivitäten

### Log-Management

- **Zentralisiertes Logging:** ELK Stack (im Monitoring-Compose-Override: `docker-compose.monitoring.yml`)
- **Log-Retention:** 13 Monate Audit-Logs, 3 Monate Anwendungs-Logs
- **Audit-Compliance:** Tamper-evident Logging für regulatorische Anforderungen

### Kritische Alerts

| Ereignis | SLA |
|----------|-----|
| Service komplett ausgefallen | Sofortige Eskalation |
| Datenintegritätsproblem | 5-Minuten-SLA |
| Performance-Degradation | Proaktives Scaling |

---

## 6. Incident Response

### Klassifizierung

| Klasse | Beschreibung |
|--------|--------------|
| **P0 (Kritisch)** | Service ausgefallen, Datenpanne |
| **P1 (Hoch)** | Erhebliche Degradation, Sicherheitsvorfall |
| **P2 (Mittel)** | Kleinere Probleme, Performance |
| **P3 (Niedrig)** | Dokumentation, unkritische Bugs |

### Ablauf

1. **Erkennung** — Monitoring-Alert oder Nutzer-Meldung
2. **Eskalation** — Incident-Verantwortlichen benennen
3. **Bewertung** — Impact und Schwere einschätzen
4. **Eindämmung** — Sofortmaßnahmen
5. **Behebung** — Root-Cause-Analyse und Fix
6. **Post-Mortem** — Lessons learned, Verbesserungsmaßnahmen

### Sicherheitsvorfall

1. **Eindämmung:** Betroffene Systeme sofort isolieren
2. **Forensik:** Analyse mit Chain of Custody
3. **Benachrichtigung:** Kunden und Behörden (sofern gesetzlich erforderlich)
4. **Wiederherstellung:** Sichere Restauration der Dienste
5. **Review:** Sicherheitskontrollen verbessern

---

## 7. Compliance-Betrieb

### GoBD

- Automatisierte 10-Jahres-Archivierung
- Kryptografische Prüfsummen der Audit-Trail-Integrität
- Jährliche Compliance-Verifizierung: `docker compose exec web python project_root/manage.py gobd_audit`

### DSGVO

- Auskunfts-/Löschanfragen: 30-Tage-SLA
- Verarbeitungsverzeichnis wird automatisch gepflegt
- Datenschutz-Folgeabschätzungen für neue Features

### ZUGFeRD

- 100 % automatisierte Schema-Validierung beim Rechnungserzeugen
- Vierteljährliches Review auf Standard-Updates
- Monatliche End-to-End-Validierung
