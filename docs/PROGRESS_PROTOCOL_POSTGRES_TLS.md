# Progress Protocol — PostgreSQL TLS Encryption

## 2026-04-09 - PostgreSQL TLS für inter-Service-Kommunikation 🔄

### Summary
Absicherung der PostgreSQL-Verbindung mit nativem TLS (Application-Level). Motivation: Bei Multi-Node-Kubernetes-Deployments fließt DB-Traffic über das Netzwerk — Credentials und Rechnungsdaten im Klartext. PostgreSQL-natives TLS ist infrastruktur-unabhängig und funktioniert in Docker Compose, k3s und Cloud-Umgebungen gleichermaßen.

### Scope
- PostgreSQL-Image um TLS-Support erweitern
- Django `settings.py` um `sslmode` erweitern
- k3s: cert-manager Certificate für PostgreSQL, Cert-Mounts in allen Consumer-Pods
- Docker Compose: selbstsignierte Zertifikate für Entwicklungsumgebung
- Tests für beide Umgebungen

### Nicht im Scope
- Redis TLS (geringeres Risiko, nur Celery-Broker, keine persistenten Daten)
- Linkerd mTLS (infrastruktur-abhängig, nicht portabel)

---

### Durchgeführte Änderungen

#### 1. Analyse Ist-Zustand (abgeschlossen)
- **PostgreSQL Image**: `postgres:17` mit pgTAP + pg_stat_statements (Dockerfile in `infra/postgres/`)
- **Verbindung**: Plain TCP auf Port 5432, kein `sslmode` in Django settings
- **Consumer-Pods**: django-web (2 Replicas), celery-worker (1 Replica), django-init Job, django-migrate Job
- **cert-manager**: v1.17.1 mit self-signed CA (`erechnung-ca-issuer`) bereits vorhanden
- **Docker Compose**: `db` Service baut `./infra/postgres`, kein TLS

#### 2. PostgreSQL Image TLS-fähig gemacht
- `infra/postgres/Dockerfile`: TLS-Setup-Script (`setup-tls.sh`) als entrypoint-initdb hinzugefügt
- `infra/postgres/setup-tls.sh`: Kopiert gemountete Zertifikate mit korrekten Permissions (600 für key)
- `scripts/generate-pg-certs.sh`: Generiert selbstsignierte Dev-Zertifikate (CA + Server)
- `infra/postgres/certs/.gitignore`: Private Keys von Git ausgeschlossen

#### 3. Django settings.py erweitert
- Neue Env-Variablen: `DATABASE_SSL_MODE` (default: `prefer`) und `DATABASE_SSL_CA`
- `sslmode` wird nur gesetzt wenn nicht `disable`
- CA-Pfad nur gesetzt wenn `DATABASE_SSL_CA` vorhanden
- Abwärtskompatibel: ohne Env-Variablen verhält sich alles wie bisher

#### 4. k3s Kubernetes Manifeste angepasst
- `manifests/13-cert-postgres-tls.yaml`: cert-manager Certificate mit `erechnung-ca-issuer`, 1 Jahr Laufzeit, auto-renewal
- `manifests/30-deploy-postgres.yaml`: SSL-Args, TLS-Secret als Volume gemountet
- `manifests/10-configmap-erechnung-config.yaml`: `DATABASE_SSL_MODE=verify-ca`, `DATABASE_SSL_CA=/etc/ssl/postgres/ca.crt`
- `manifests/50-deploy-django-web.yaml`: CA-Cert Volume + Mount
- `manifests/52-deploy-celery-worker.yaml`: CA-Cert Volume + Mount
- `manifests/40-job-django-init.yaml`: CA-Cert Volume + Mount
- `manifests/41-job-django-migrate-template.yaml`: CA-Cert Volume + Mount
- `kustomization.yaml`: Neues Manifest `13-cert-postgres-tls.yaml` eingebunden

#### 5. Docker Compose angepasst
- `docker-compose.yml`: PostgreSQL command mit SSL-Flags, Cert-Verzeichnis gemountet
- Dev-Zertifikate generiert unter `infra/postgres/certs/`

---

### Tests

#### Docker Compose TLS Tests (7/7 bestanden)
```
=== PostgreSQL TLS Test Suite (Docker Compose) ===
  ✅ PASS: TLS certificates present in infra/postgres/certs/
  ✅ PASS: PostgreSQL reports SSL=true for TCP connection
  ✅ PASS: PostgreSQL ssl = on
  ✅ PASS: Django connects to PostgreSQL with SSL
  ✅ PASS: Django DATABASE_SSL_MODE = require
  ✅ PASS: TLS 1.2 or 1.3 in use
  ✅ PASS: Non-SSL fallback works (pg_isready compatibility)
Results: 7 passed, 0 failed
```

#### Django Regression Tests (684/684 bestanden)
```
Ran 684 tests in 464.442s
OK
```
Keine Regression durch die TLS-Änderungen.

#### k3s TLS Tests (8/9 bestanden)
```
=== PostgreSQL TLS Test Suite (k3s) ===
Namespace: erechnung

  ✅ PASS: cert-manager Certificate 'postgres-tls' is Ready
  ✅ PASS: Secret 'postgres-tls-certs' contains ca.crt, tls.crt, tls.key
  ✅ PASS: PostgreSQL ssl = on
  ✅ PASS: PostgreSQL reports SSL=true for TLS connection
  ✅ PASS: TLS 1.2 or 1.3 in use ( TLSv1.3 | TLS_AES_256_GCM_SHA384 | 256)
  ✅ PASS: Django connects to PostgreSQL with SSL (SSL=True, Version=TLSv1.3, Cipher=TLS_AES_256_GCM_SHA384)
  ❌ FAIL: Django sslmode not properly set (output: sslmode=NOT_SET)
  ✅ PASS: Celery worker connects to PostgreSQL with SSL (SSL=True, Version=TLSv1.3)
  ✅ PASS: CA certificate mounted at /etc/ssl/postgres/ca.crt
Results: 8 passed, 1 failed
```
**Anmerkung Test 5 (sslmode):** Das deployed Django-Image wurde vor den `settings.py`-Änderungen
gebaut. Die SSL-Verbindung funktioniert trotzdem (PostgreSQL erzwingt SSL serverseitig), aber Django
meldet `sslmode=NOT_SET` weil der Code im Image veraltet ist. Wird durch Neubauen des Images mit
versioniertem Tag behoben (siehe separater Branch `fix/image-versioning`).

#### k3s Manuelle Verifizierung (bestanden)
```bash
# PostgreSQL TLS 1.3 aktiv
kubectl exec deploy/postgres -- psql "host=localhost user=postgres dbname=erechnung sslmode=require" \
  -c "SELECT ssl, version, cipher FROM pg_stat_ssl WHERE pid = pg_backend_pid();"
#  t | TLSv1.3 | TLS_AES_256_GCM_SHA384

# Django→PG SSL bestätigt
kubectl exec deploy/django-web -- python manage.py shell -c "..."
# SSL=True, Version=TLSv1.3, Cipher=TLS_AES_256_GCM_SHA384

# Celery→PG SSL bestätigt
kubectl exec deploy/celery-worker -- python -c "..."
# SSL=True, Version=TLSv1.3
```

---

### Bekannte Einschränkungen
- **`latest`-Tag Anti-Pattern**: Alle k3s-Manifeste verwenden `:latest`. Wird in separatem Branch `fix/image-versioning` mit `git describe`-basierter Versionierung behoben.
- **Redis**: Kein TLS (nur Celery-Broker, keine persistenten Daten, keine Credentials im Transit). Geringes Risiko.

### Status: ✅ Abgeschlossen (Code)
Code-Änderungen komplett. Docker Compose vollständig verifiziert (7/7 Tests + 684 Regression).
k3s TLS funktional verifiziert (PostgreSQL, Django, Celery alle via TLS 1.3 verbunden).
Vollständige k3s-Verifikation nach Image-Neubau mit versioniertem Tag ausstehend.
