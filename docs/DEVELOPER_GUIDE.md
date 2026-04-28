# Developer Guide — eRechnung

> Letztes Update: 14. März 2026

Dieser Guide richtet sich an Entwickler:innen, die am Projekt mitarbeiten.
Für allgemeine Beitragsregeln siehe [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Inhaltsverzeichnis

1. [Voraussetzungen & Setup](#1-voraussetzungen--setup)
2. [Projektstruktur](#2-projektstruktur)
3. [Wichtige Befehle](#3-wichtige-befehle)
4. [Architektur-Überblick](#4-architektur-überblick)
5. [Backend — Django](#5-backend--django)
6. [Frontend — Vue.js](#6-frontend--vuejs)
7. [Tests](#7-tests)
8. [Code-Konventionen](#8-code-konventionen)
9. [Weiterlesen](#9-weiterlesen)

---

## 1. Voraussetzungen & Setup

**Benötigt:** Docker, Docker Compose, Git

```bash
git clone <repo-url>
cd erechnung

# Beide Remotes setzen
git remote set-url origin <local-mirror-url>
git remote add github <github-url>

# Umgebung starten
docker compose up -d

# Superuser anlegen
docker compose exec web python project_root/manage.py createsuperuser

# Fixtures laden (Länderdaten mit EU-MwSt-Sätzen)
docker compose exec web python project_root/manage.py loaddata invoice_app/fixtures/countries.json
```

Nach dem Start:

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000/api/
- **Swagger UI:** http://localhost:8000/api/docs/
- **Django Admin:** http://localhost:8000/admin/

### Umgebungsvariablen

Konfiguration über `.env` (Basis: `.env.example`). Wichtigste Variablen:

```bash
DEBUG=True
SECRET_KEY=...
DATABASE_URL=postgres://erechnung:erechnung@db:5432/erechnung
REDIS_URL=redis://redis:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## 2. Projektstruktur

```
erechnung/
├── project_root/              # Django-Root (alles Manage-py-Bezogene)
│   ├── manage.py
│   ├── invoice_project/       # Django-Projektkonfiguration (settings, urls, wsgi)
│   └── invoice_app/           # Haupt-App
│       ├── models/            # Datenbankmodelle (aufgeteilt nach Domäne)
│       │   ├── invoice_models.py   # Rechnung, Rechnungszeile, Anhang
│       │   ├── business_partner.py
│       │   ├── company.py
│       │   ├── product.py
│       │   ├── user.py        # UserProfile, RBAC-Rollen
│       │   ├── audit.py       # AuditLog (GoBD)
│       │   └── country.py
│       ├── api/               # Django REST Framework
│       │   ├── serializers.py
│       │   ├── views/         # API-ViewSets
│       │   ├── permissions.py # RBAC-Permissions
│       │   └── exception_handlers.py  # Einheitliche Fehler-Antworten
│       ├── services/          # Business-Logik (kein HTTP-Bezug)
│       │   ├── invoice_service.py  # PDF/ZUGFeRD-Erzeugung
│       │   ├── tax_service.py
│       │   ├── integrity_service.py  # GoBD-Integritätsprüfung
│       │   └── gdpr_service.py
│       ├── tests/             # Alle Tests (~40 Testdateien)
│       ├── fixtures/          # Stammdaten (countries.json)
│       ├── management/        # Custom Management-Commands
│       └── migrations/        # Django-Datenbankmigrationen
├── frontend/                  # Vue.js 3 Frontend
│   ├── src/
│   │   ├── api/
│   │   │   └── fieldMappings.js    # ⚠️ ACL: UI↔API Feldnamen
│   │   ├── stores/            # Pinia Stores
│   │   ├── components/        # Vue-Komponenten
│   │   └── views/             # Seitenkomponenten
│   └── tests/                 # Frontend-Unit-Tests
├── infra/
│   ├── api-gateway/           # nginx Gateway-Konfiguration
│   ├── k8s/                   # Kubernetes-Manifeste (k3s)
│   └── backups/               # Backup-Verzeichnis
├── scripts/                   # Shell-Scripts (alle hier, nicht im Root)
├── docs/                      # Dokumentation
│   ├── openapi.json           # ⚠️ Single Source of Truth für API
│   ├── arc42/                 # Architekturdokumentation (arc42)
│   │   └── adrs/              # Architecture Decision Records
│   └── req42/                 # Anforderungen
└── docker-compose.yml         # Standard-Entwicklungsumgebung
```

---

## 3. Wichtige Befehle

> ⚠️ **Docker-First:** Alle Django-Befehle immer via `docker compose exec web`.

```bash
# Migrationen erstellen + anwenden
docker compose exec web python project_root/manage.py makemigrations
docker compose exec web python project_root/manage.py migrate

# Alle Tests ausführen
cd scripts && ./run_tests_docker.sh

# Einzelnes Test-Modul
docker compose exec web python project_root/manage.py test invoice_app.tests.test_api

# Django-Shell
docker compose exec web python project_root/manage.py shell

# openapi.json regenerieren (nach API-Änderungen!)
cd scripts && ./regenerate_openapi.sh

# Backup erstellen
cd scripts && ./backup.sh

# Backup-Restore-Test
cd scripts && ./backup_restore_test.sh

# Logs
docker compose logs -f web
docker compose logs -f frontend

# Container-Status
docker compose ps
```

### Frontend-Befehle (im Container)

```bash
# Nur wenn nötig — Unit-Tests
docker compose exec frontend npm run test:unit

# E2E-Tests (eigener Compose-Override)
cd scripts && ./run_e2e_container.sh
```

### Git-Workflow

```bash
# Immer in beide Remotes pushen
git push origin main
git push github main
```

---

## 4. Architektur-Überblick

```txt
Browser
  └── Vue.js 3 (localhost:5173)
        └── fieldMappings.js  ← ACL-Schicht (UI↔API)
              └── HTTP/JWT → nginx API-Gateway (:8000)
                    ├── Django REST API
                    │     ├── Serializers (Layer 2 Validation)
                    │     ├── Services (Business-Logik)
                    │     │     ├── InvoiceService → pypdf + factur-x → ZUGFeRD PDF/A-3
                    │     │     └── IntegrityService → GoBD Audit-Trail
                    │     └── PostgreSQL 17
                    └── Celery (Async-Tasks) ← Redis 7
```

**Zwei Deployment-Varianten:**

- **Docker Compose** (Entwicklung/Small Business): `docker compose up -d`
- **Kubernetes k3s** (Enterprise): `kubectl apply -k infra/k8s/k3s/`

Details: [arc42/production-operations.md](arc42/production-operations.md)

---

## 5. Backend — Django

### Modelle

Alle Modelle unter `invoice_app/models/`. Die wichtigsten:

| Modell | Datei | Beschreibung |
|--------|-------|--------------|
| `Invoice` | `invoice_models.py` | Rechnung (Kopf + Status) |
| `InvoiceLine` | `invoice_models.py` | Rechnungszeile |
| `BusinessPartner` | `business_partner.py` | Kunden/Lieferanten |
| `Company` | `company.py` | Eigene Firmen |
| `UserProfile` | `user.py` | RBAC-Rollen (ADMIN/MANAGER/ACCOUNTANT/VIEWER) |
| `AuditLog` | `audit.py` | GoBD-konformer Audit-Trail |

### Services

Business-Logik gehört **immer in Services**, nicht in Views oder Serializer:

```python
# ✅ Richtig
from invoice_app.services.invoice_service import InvoiceService
service = InvoiceService()
pdf_bytes = service.generate_pdf_a3(invoice)

# ❌ Falsch: PDF-Logik in einem ViewSet
```

### API — Fehlerformat

Alle API-Fehler folgen dem einheitlichen Format (→ `exception_handlers.py`):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Fehlerbeschreibung",
    "details": { "field": ["Fehlermeldung"] }
  }
}
```

### RBAC — Berechtigungen

Rollen: `ADMIN > MANAGER > ACCOUNTANT > VIEWER`

```python
# Berechtigung in View prüfen
from invoice_app.api.permissions import RBACPermission

class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, RBACPermission]
```

### openapi.json — Single Source of Truth

**Nach jeder API-Änderung** (neues Feld, neuer Endpoint, geänderter Typ) muss `docs/openapi.json` regeneriert werden:

```bash
cd scripts && ./regenerate_openapi.sh
```

Bei Widersprüchen zwischen Code und openapi.json gilt **immer openapi.json**.

---

## 6. Frontend — Vue.js

### Anti-Corruption Layer (ACL)

Alle Felder zwischen UI und API **müssen** über `frontend/src/api/fieldMappings.js` deklariert sein:

```javascript
// ✅ Richtig
import { mapToApi, mapFromApi } from '@/api/fieldMappings'
const apiData = mapToApi(formData, 'invoice')

// ❌ Falsch: direkter API-Feldname in Komponente
axios.post('/api/invoices/', { invoice_number: ... })
```

Details: [ACL_FIELD_MAPPING.md](ACL_FIELD_MAPPING.md)

### State-Management

Pinia Stores unter `frontend/src/stores/`. Jede Ressource hat einen eigenen Store.

### Konfiguration

```bash
# .env.development (Vite)
VITE_API_BASE_URL=http://localhost:8000/api

# .env.production (Kubernetes)
VITE_API_BASE_URL=/api
```

---

## 7. Tests

Das Projekt hat ~40 Testdateien. Alle unter `invoice_app/tests/`:

| Datei | Beschreibung |
|-------|--------------|
| `test_models.py` | Modell-Unit-Tests |
| `test_api.py` | REST API Integration-Tests |
| `test_rbac_models.py` | RBAC/Berechtigungs-Tests |
| `test_invoice_service.py` | PDF/XML-Erzeugung |
| `test_xml_utils.py` | ZUGFeRD XML-Validierung |
| `test_gobd_compliance.py` | GoBD-Compliance-Tests |
| `test_exception_handler.py` | Fehler-Response-Format |

```bash
# Alle Tests (empfohlen)
cd scripts && ./run_tests_docker.sh

# Mit Coverage-Report
docker compose exec web python project_root/manage.py test invoice_app.tests \
  --with-coverage --cover-html

# Einzelner Test
docker compose exec web python project_root/manage.py test \
  invoice_app.tests.test_api.InvoiceApiTests.test_create_invoice
```

**Neue Features brauchen Tests.** Mindest-Coverage: 90%.

---

## 8. Code-Konventionen

- **Python:** PEP 8, Black-Formatierung, Ruff-Linting
- **Commits:** Conventional Commits (`feat/fix/refactor/docs/test(scope): beschreibung`)
- **ADRs:** Architekturentscheidungen in `docs/arc42/adrs/ADR-NNN-*.md` dokumentieren
- **Scripts:** Alle Shell-Scripts in `scripts/`, keine Scripts im Root
- **Keine Business-Logik in Views/Serialisern** — alles in Services

```bash
# Linting lokal prüfen
docker compose exec web ruff check project_root/
docker compose exec web black --check project_root/
```

---

## 9. Weiterlesen

| Dokument | Inhalt |
|----------|--------|
| [docs/openapi.json](openapi.json) | API-Vertrag (Single Source of Truth) |
| [docs/API_SPECIFICATION.md](API_SPECIFICATION.md) | API-Referenz + curl-Beispiele |
| [docs/ACL_FIELD_MAPPING.md](ACL_FIELD_MAPPING.md) | Frontend↔API Feldnamen-Mapping |
| [docs/arc42/](arc42/) | Architektur-Dokumentation (arc42) |
| [docs/arc42/adrs/](arc42/adrs/) | Architecture Decision Records |
| [docs/arc42/production-operations.md](arc42/production-operations.md) | Deployment, Backup, HTTPS |
| [docs/SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md) | Sicherheitsimplementierung |
| [docs/CONTRIBUTING.md](CONTRIBUTING.md) | Beitragsregeln, Branching-Strategie |
| [SBOM.json](../SBOM.json) | Software Bill of Materials |
