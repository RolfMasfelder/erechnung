# Codebase & Dokumentations-Audit — 26. Februar 2026

## 1. Zusammenfassung

Umfassende Analyse der Codebasis und aller Dokumentationsdateien im Verzeichnis `docs/`.
Ergebnis: **16 obsolete Dateien** zum Archivieren, **14 Dateien** mit Aktualisierungsbedarf,
**6 Inkonsistenzen** in `openapi.json`, und **mehrere Anti-Patterns/veraltete Praktiken** im Code.

---

## 2. Dokumentations-Status

### 2.1 Aktuell & relevant (13 Dateien — kein Handlungsbedarf)

| Datei | Beschreibung |
|-------|-------------|
| `API_SPECIFICATION.md` | REST-API-Referenz, zuletzt 2026-02-21 aktualisiert |
| `DJANGO_6_HTTPS_MIGRATION_ANALYSIS.md` | Django 6.0 noch nicht released — Phasen 2-5 offen |
| `GOBD_IMPLEMENTATION.md` | GoBD-Compliance-Plan, alle Phasen bei 0% |
| `GOBD_PROTOCOL.md` | Fortschritts-Tracking GoBD |
| `HTTPS_SETUP.md` | HTTPS-Anleitung für Dev-Umgebung |
| `KUBERNETES_DEPLOYMENT_OPTIONS.md` | k3s-Entscheidung dokumentiert, aktuell |
| `MISSING_VIEWS_IMPLEMENTATION_PLAN.md` | CompanyDetailView/SettingsView-Plan |
| `PROGRESS_PROTOCOL.md` | Master-Fortschrittslog, aktiv gepflegt |
| `PROGRESS_PROTOCOL_TEMPLATE.md` | Wiederverwendbare Vorlage |
| `docs/README.md` | Index-Datei |
| `SECURITY.md` | Sicherheitsrichtlinien, Jan 2026 aktualisiert |
| `SECURITY_IMPLEMENTATION.md` | Security-Roadmap, Phase 0 done, Phase 1 bei 40% |
| `E2E_TESTING.md` (Root) | Praktische E2E-Anleitung, aktuell |

### 2.2 Obsolet → nach `docs/archive/` verschieben (16 Dateien)

| Datei | Grund |
|-------|-------|
| `DB_API_CLEANUP_PLAN.md` | Alle 13 Änderungen ✅ ERLEDIGT |
| `DEPENDENCY_UPDATE_TEST_PLAN.md` | Einmaliger Testplan für PR aus Nov 2025 |
| `DOWNLOAD_FEATURE_IMPLEMENTATION_PLAN.md` | Download-Endpoints ✅ deployed seit 10. Feb 2026 |
| `E2E_TEST_FIX_PLAN.md` | Phase 1+2 abgeschlossen (96% Pass-Rate) |
| `FRONTEND_IMPLEMENTATION_PLAN.md` | Alle Phasen 1-6 ✅ ABGESCHLOSSEN |
| `INVOICE_REFERENCES_IMPLEMENTATION_PLAN.md` | Alle 7 Phasen ✅ COMPLETED |
| `ISSUE_9_IMPLEMENTATION_SUMMARY.md` | Issue #9 (Django 6.0 Prep) erledigt |
| `NEXT_SPRINT.md` | Tasks 1-6 ✅ FERTIG, nur Task 7 offen |
| `SCHEMATRON_FIX_SUMMARY.md` | Fix abgeschlossen, XML-Struktur seitdem geändert |
| `SPRINT_NEXT_TODO.md` | Superseded durch NEXT_SPRINT.md |
| `project_update.md` | Frühphasen-Dokument, komplett überholt |
| `BUGFIXES.md` (Root) | Alle 6 Bugs ✅ Erledigt |
| `E2E_FIX_SUMMARY.md` (Root) | Fix-Zusammenfassung abgeschlossen |
| `DOCUMENTATION_SYNC_REPORT.md` (Root) | Einmaliger Sync-Report, Änderungen angewendet |
| `METALLB_CHANGES.md` (Root) | Referenziert veraltete `k8s/kind/`-Pfade |
| `incoming_invoice_processor.py.obsolete` (Root) | Bereits als obsolete markiert |

### 2.3 Aktualisierung erforderlich (14 Dateien)

| Datei | Problem | Priorität |
|-------|---------|-----------|
| **`DEVELOPMENT_CONTEXT.md`** | Migration bei 0007 (jetzt viel höher), 87 Tests (jetzt 263+), referenziert `Customer`-Model | **Hoch** |
| **`CONTRIBUTING.md`** | Referenziert `./start_app.sh`, `Customer`-Model, `docker-compose` (alt) | **Hoch** |
| **`pdf_xml_handling.md`** | Nennt ReportLab als PDF-Engine (jetzt WeasyPrint) | **Hoch** |
| **`ZUGFERD_CONFORMANCE.md`** | Referenziert `Invoice.customer` statt `business_partner` | **Mittel** |
| **`ANTI_PATTERN_ANALYSIS.md`** | Score/Referenzen von Sep 2025 veraltet | **Mittel** |
| **`FRONTEND_BACKLOG.md`** | Items 3-8 teilweise implementiert, Backlog nicht aktualisiert | **Mittel** |
| **`FRONTEND_PROTOCOL.md`** | Deckt nur frühe Phasen ab, Überlappung mit PROGRESS_PROTOCOL | **Mittel** |
| **`INCOMING_INVOICE_SYSTEM_SUMMARY.md`** | Referenziert `Customer`, Prozessor als `.obsolete` markiert | **Mittel** |
| **`INVOICE_TESTING_GUIDE.md`** | Alte Model-Namen, Shell-Beispiele veraltet | **Mittel** |
| **`IMPORT_EXPORT_IMPLEMENTATION_PLAN.md`** | Plan detaillierter als tatsächliche Implementierung | **Niedrig** |
| **`METALLB_MIGRATION.md`** | `k8s/kind/`-Pfade → jetzt `k8s/k3s/` | **Niedrig** |
| **`SAFE_UPDATE_STRATEGY.md`** | Versionshinweise veraltet (Django 5.1→5.2) | **Niedrig** |
| **`DEPENDENCY_TOOLS.md`** | Beispielausgaben veraltet, Kern-Anleitung ok | **Niedrig** |
| **`CODE_OF_CONDUCT.md`** | Platzhalter `[INSERT CONTACT METHOD]` nicht ausgefüllt | **Niedrig** |

### 2.4 Übergreifend: `Customer` → `BusinessPartner`

**20 Dokumentdateien** referenzieren noch das alte `Customer`-Model (umbenannt zu `BusinessPartner`).
Betroffen sind auch arc42-Architekturdokumente:

- `docs/arc42/05-building-block-view.md`
- `docs/arc42/adrs/ADR-009-frontend-architecture-api-first.md`
- `docs/arc42/adrs/ADR-006-zugferd-profile-selection.md`
- `docs/arc42/production-operations.md`

---

## 3. openapi.json — Inkonsistenzen

Die Datei `docs/openapi.json` verwendet **Swagger 2.0**-Format (nicht OpenAPI 3.0+),
was eine Limitation von `drf-yasg` ist.

### 3.1 Fehltypisierungen

| Feld | openapi.json | Tatsächlicher Typ | Schwere |
|------|-------------|-------------------|---------|
| `Invoice.allowance_charges` | `string` | `array<InvoiceAllowanceCharge>` | **Hoch** |
| `InvoiceLine.allowance_charges` | `string` | `array<InvoiceAllowanceCharge>` | **Hoch** |
| `Country.vat_rates` | `string` | `object` (Dict mit Steuersätzen) | **Mittel** |
| `InvoiceAllowanceCharge.is_line_level` | `string` | `boolean` | **Mittel** |
| `InvoiceLine.effective_unit_price` | `string` (ohne format) | `string` mit `format: decimal` | **Niedrig** |

**Ursache**: `drf-yasg` kann `SerializerMethodField` nicht introspektieren und typisiert alle als `string`.

### 3.2 Fehlende Definition

`CountryTaxRate` wird als Serializer verwendet (Endpoint `/api/countries/{code}/tax-rates/`),
hat jedoch **keine zugehörige Definition** in openapi.json.

### 3.3 Fehlender Endpoint

`/health/` (Basic-Healthcheck) ist als Django-View registriert, fehlt aber in openapi.json.
Nur `/health/detailed/` und `/health/readiness/` sind dokumentiert.

### 3.4 Empfehlung

Migration von `drf-yasg` → `drf-spectacular` (OpenAPI 3.0/3.1) löst die meisten
Typisierungsprobleme und ermöglicht `@extend_schema`-Dekoratoren für `SerializerMethodField`.

---

## 4. Anti-Patterns & veraltete Praktiken

### 4.1 Schwere: Hoch

| Problem | Ort | Empfehlung |
|---------|-----|-----------|
| **`.env.bak` mit Real-Secrets in Git** | Root `.env.bak` (git-tracked!) | Sofort aus Git entfernen, Secrets rotieren. Datei enthält `DJANGO_SECRET_KEY`, DB-Passwörter und einen auskommentierten GitHub-Secret. |
| **`open()` ohne Context Manager** | `rest_views.py` Zeile 482, 527 | `FileResponse(open(pdf_path, "rb"), ...)` — Ressourcen-Leak bei Exceptions. Mit `with` oder explizitem Close absichern. |

### 4.2 Schwere: Mittel

| Problem | Ort | Empfehlung |
|---------|-----|-----------|
| **`drf-yasg` (Maintenance Mode)** | `requirements.in`, `settings.py`, `urls.py`, `rest_views.py` | Swagger 2.0-only, kein OpenAPI 3.x. Migration zu `drf-spectacular` planen. |
| **`filter_fields` deprecated & nicht funktional** | `rest_views.py` — `CompanyViewSet`, `BusinessPartnerViewSet` | `filter_fields` ohne `DjangoFilterBackend` in `filter_backends` → Filterung ist **wirkungslos**. Zu `filterset_fields` umbenennen und `DjangoFilterBackend` hinzufügen. |
| **50+ `except Exception` Blöcke** | Gesamte Codebasis (rest_views, services, utils) | Zu breite Exception-Behandlung verschleiert spezifische Fehler. In API-Views und Services spezifischere Exceptions fangen (`FileNotFoundError`, `ValidationError`, etc.). |
| **`build-essential` im Production-Image** | `Dockerfile` | ~200MB unnötige Build-Tools. Da `psycopg2-binary` als Wheel kommt, ist `build-essential` nicht nötig. |

### 4.3 Schwere: Niedrig

| Problem | Ort | Empfehlung |
|---------|-----|-----------|
| **Python-Version Mismatch** | Dockerfile: `3.13`, pyproject.toml: `py312`, requirements.txt: kompiliert mit 3.12 | Auf 3.13 vereinheitlichen |
| **`SECURE_BROWSER_XSS_FILTER = True`** | `settings.py` Zeile 65 | Seit Django 4.1 deprecated, hat keine Wirkung. Entfernen. |
| **`version: '3.8'`** in Compose-Datei | `docker-compose.frontend.yml` | Docker Compose V2 ignoriert `version:` — Zeile entfernen |
| **`autoprefixer`** im Frontend | `frontend/package.json` | Mit Tailwind CSS v4 möglicherweise nicht mehr nötig |
| **Keine `.dockerignore` für `htmlcov/`** | Root `.dockerignore` | `htmlcov/`, `test-artifacts/`, `docs/` fehlen in `.dockerignore` |

---

## 5. Empfohlene Maßnahmen (priorisiert)

### Sofort (Sicherheit)

1. **`.env.bak` aus Git löschen** und History bereinigen (`git filter-branch` oder `git filter-repo`), Secrets rotieren
2. File-Handle-Leaks in `download_pdf`/`download_xml` fixen

### Kurzfristig (Sprint)

3. 16 obsolete Dateien nach `docs/archive/` verschieben
4. `filter_fields` → `filterset_fields` + `DjangoFilterBackend` (CompanyViewSet, BusinessPartnerViewSet)
5. `SECURE_BROWSER_XSS_FILTER` aus settings.py entfernen
6. openapi.json Fehltypisierungen korrigieren (`allowance_charges`, `is_line_level`, `vat_rates`)
7. `CountryTaxRate`-Definition zu openapi.json hinzufügen

### Mittelfristig (nächster Sprint)

8. Hoch-priorisierte Docs aktualisieren (DEVELOPMENT_CONTEXT, CONTRIBUTING, pdf_xml_handling)
9. `Customer` → `BusinessPartner` in allen 20 betroffenen Docs ersetzen
10. Python-Version auf 3.13 vereinheitlichen

### Langfristig (Backlog)

11. Migration `drf-yasg` → `drf-spectacular` (OpenAPI 3.0)
12. Audit: `except Exception` Blöcke auf spezifischere Exceptions einschränken
13. Dockerfile optimieren (build-essential entfernen)
14. Restliche niedrig-priorisierte Docs aktualisieren

---

## 6. Positiv-Befunde

- **openapi.json Endpoints sind vollständig** — alle 36 Pfade stimmen mit den registrierten Django-URLs überein
- **Serializer-Felder** stimmen mit den openapi.json-Definitionen überein (abgesehen von SerializerMethodField-Typen)
- **Frontend-Stack aktuell**: Vue 3.5, Pinia 3, Vite 7, Vitest 4, Tailwind 4
- **Saubere Import-Patterns**: `isort` + `ruff` konfiguriert, zirkuläre Imports korrekt mit Lazy-Imports gelöst
- **Docker Compose V2**: Hauptdatei nutzt korrekt kein `version:`-Key
- **SECRET_KEY korrekt externalisiert**: `os.getenv()` mit `ValueError` bei fehlendem Key
- **DEBUG Default: False**: Sichere Standardkonfiguration
- **Non-Root Docker User**: Security Best Practice implementiert
- **arc42 + req42 Architekturdokumentation** vorhanden und strukturiert
