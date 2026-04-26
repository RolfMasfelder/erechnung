# Umsetzungsplan — Codebase-Audit 26. Feb 2026

> Basiert auf: `docs/CODEBASE_AUDIT_2026-02-26.md`
> Branch: `audit-cleanup-2026-02`
> Stand: 27. Februar 2026 — **Alle 10 Phasen abgeschlossen ✓**

---

## Phase 1: Sicherheit & Git-Hygiene

### 1.1 `.env.bak` aus Git entfernen
- [x] `git rm --cached .env.bak` — Datei aus Git-Tracking entfernen
- [x] `.env.bak` lokal löschen
- [x] `.gitignore` Regel `.env*` verifiziert (Zeile 19 — deckt alle Varianten ab)
- [x] Kein Secret-Rotation nötig (nie produktive Secrets verwendet)

### 1.2 File-Handle-Leaks fixen
- [x] `rest_views.py` `download_pdf`: `open()` in Variable, `FileResponse` separat — Leak vermieden
- [x] `rest_views.py` `download_xml`: analog gefixt

---

## Phase 2: Obsolete Docs archivieren

### 2.1 Verzeichnis `docs/archive/` anlegen
- [x] Angelegt

### 2.2 Folgende 11 Dateien aus `docs/` verschieben
- [x] `DB_API_CLEANUP_PLAN.md`
- [x] `DEPENDENCY_UPDATE_TEST_PLAN.md`
- [x] `DOWNLOAD_FEATURE_IMPLEMENTATION_PLAN.md`
- [x] `E2E_TEST_FIX_PLAN.md`
- [x] `FRONTEND_IMPLEMENTATION_PLAN.md`
- [x] `INVOICE_REFERENCES_IMPLEMENTATION_PLAN.md`
- [x] `ISSUE_9_IMPLEMENTATION_SUMMARY.md`
- [x] `NEXT_SPRINT.md`
- [x] `SCHEMATRON_FIX_SUMMARY.md`
- [x] `SPRINT_NEXT_TODO.md`
- [x] `project_update.md`

### 2.3 Folgende 4 Root-Dateien verschieben
- [x] `BUGFIXES.md` → `docs/archive/`
- [x] `E2E_FIX_SUMMARY.md` → `docs/archive/`
- [x] `DOCUMENTATION_SYNC_REPORT.md` → `docs/archive/`
- [x] `METALLB_CHANGES.md` → `docs/archive/`

### 2.4 Root-Datei löschen
- [x] `incoming_invoice_processor.py.obsolete` — gelöscht (kein Archiv-Wert)

**→ 15 Dateien in `docs/archive/`, 1 gelöscht**

---

## Phase 3: Quick-Fixes im Code

### 3.1 `filter_fields` → `filterset_fields` + DjangoFilterBackend
- [x] `CompanyViewSet`: `filterset_fields` + `DjangoFilterBackend` hinzugefügt
- [x] `BusinessPartnerViewSet`: `filterset_fields` + `DjangoFilterBackend` hinzugefügt

### 3.2 Deprecated Settings entfernen
- [x] `SECURE_BROWSER_XSS_FILTER = True` aus `settings.py` entfernt (deprecated seit Django 4.1)

### 3.3 Docker Compose bereinigen
- [x] `version: '3.8'` aus `docker-compose.frontend.yml` entfernt

---

## Phase 4: openapi.json Korrekturen

### 4.1 Fehltypisierungen korrigiert
- [x] `Invoice.allowance_charges`: `string` → `array` mit `$ref: InvoiceAllowanceCharge`
- [x] `InvoiceLine.allowance_charges`: `string` → `array` mit `$ref: InvoiceAllowanceCharge`
- [x] `Country.vat_rates`: `string` → `object`
- [x] `InvoiceAllowanceCharge.is_line_level`: `string` → `boolean`
- [x] `InvoiceLine.effective_unit_price`: `format: decimal` ergänzt

### 4.2 Fehlende Definition hinzugefügt
- [x] `CountryTaxRate`-Definition zu `definitions` hinzugefügt

### 4.3 Fehlenden Endpoint dokumentiert
- [x] `/health/` Basic-Healthcheck-Endpoint ergänzt

---

## Phase 5: Commit & Push

- [x] Tests bestanden (12/12 OK)
- [x] Alle Änderungen committen (22 Dateien, 200+/53-)
- [x] Push zu `origin` und `github`

---

## Rollback-Hinweise

- **Branch**: `audit-cleanup-2026-02` — bei Problemen zurück zu `main`
- **Phase 1**: Kein Rollback nötig — `.env.bak` hat keinen funktionalen Einfluss
- **Phase 2**: Nur Dateiverschiebungen — bei Bedarf `git checkout main -- <datei>` für einzelne Dateien
- **Phase 3**: Code-Änderungen einzeln revertbar über `git diff` pro Datei
- **Phase 4**: `openapi.json` kann aus dem laufenden System regeneriert werden: `docker compose exec web python project_root/manage.py spectacular --file docs/openapi.json --format openapi-json`

---

## Phase 6: drf-yasg → drf-spectacular Migration

### 6.1 Paket-Migration
- [x] `drf-yasg` → `drf-spectacular 0.29.0` in `requirements.in`
- [x] `INSTALLED_APPS`: `drf_yasg` → `drf_spectacular`
- [x] `REST_FRAMEWORK`: `DEFAULT_SCHEMA_CLASS` = `drf_spectacular.openapi.AutoSchema`
- [x] `SWAGGER_SETTINGS` → `SPECTACULAR_SETTINGS` (JWT, Schema-Config)
- [x] `SWAGGER_USE_COMPAT_RENDERERS` entfernt

### 6.2 URL-Konfiguration
- [x] `urls.py`: `drf_yasg.views.get_schema_view` → `SpectacularAPIView` + `SpectacularSwaggerView`
- [x] `/api/schema/` Endpoint hinzugefügt

### 6.3 View-Dekoratoren
- [x] 9× `@swagger_auto_schema` → `@extend_schema` in `rest_views.py`
- [x] `swagger_info.py` zu Backward-Compat-Shim umgebaut

### 6.4 Serializer-Typ-Annotationen
- [x] `ReadOnlyField()` → typisierte Felder (CharField, DecimalField, BooleanField, DictField)
- [x] `@extend_schema_field` für alle `SerializerMethodField`-Getter
- [x] `@extend_schema` für health-Endpoints (health_detailed, readiness_check)

### 6.5 Script- & Config-Updates
- [x] `scripts/regenerate_openapi.sh`: `generate_swagger` → `spectacular`
- [x] `scripts/check_dependencies.py`: drf-yasg → drf-spectacular
- [x] `scripts/safe_dependency_updater.py`: Kompatibilitätsmatrix aktualisiert
- [x] `api-gateway/api-gateway.conf`: Kommentar aktualisiert

**→ OpenAPI 3.0.3 generiert: 36 Endpunkte, 52 Schemas, 0 Warnungen**

---

## Phase 7: openapi.json Regeneration

- [x] `docs/openapi.json` mit drf-spectacular generiert (257 KB, OpenAPI 3.0.3)
- [x] Swagger 2.0 → OpenAPI 3.0.3 Upgrade (16 Definitionen → 52 Schemas)
- [x] Alle SerializerMethodField korrekt typisiert

---

## Phase 8: Customer → BusinessPartner in Dokumentation

### 8.1 Modell-Referenzen (14 Dateien aktualisiert)
- [x] `docs/DEVELOPMENT_CONTEXT.md` — 2 Modell-Refs
- [x] `docs/INCOMING_INVOICE_SYSTEM_SUMMARY.md` — 1 Modell-Ref
- [x] `docs/FRONTEND_BACKLOG.md` — 3 Modell-Refs
- [x] `docs/GOBD_IMPLEMENTATION.md` — 2 Code-Beispiele
- [x] `docs/INVOICE_TESTING_GUIDE.md` — 4 Code-Beispiele
- [x] `docs/IMPORT_EXPORT_IMPLEMENTATION_PLAN.md` — ~20 Refs (API-Endpoints, Entitäten)
- [x] `docs/FRONTEND_PROTOCOL.md` — ~30 Refs (Komponenten, Tests, Routes)
- [x] `docs/arc42/05-building-block-view.md` — 5 Refs (ASCII-Diagramme)
- [x] `docs/arc42/adrs/ADR-007-data-persistence-strategy.md` — 7 Refs (SQL-Code)
- [x] `docs/arc42/adrs/ADR-009-frontend-architecture-api-first.md` — 1 Ref
- [x] `docs/arc42/adrs/ADR-019-playwright-e2e-testing.md` — 2 Refs
- [x] `README.md` — 7 Refs
- [x] `TODO.md` — 9 Refs
- [x] `.github/copilot-instructions.md` — 1 Ref (model file path)

### 8.2 Nicht geändert (Begründung)
- `PROGRESS_PROTOCOL.md` — historisches Log, Änderung verfälscht History
- `API_SPECIFICATION.md` — enthält korrekte Feldnamen aus openapi.json
- `MISSING_VIEWS_IMPLEMENTATION_PLAN.md` — beschreibt Migration, Customer-Ref korrekt

---

## Phase 9: Weitere Code- & Config-Bereinigung

### 9.1 Hoch-priorisierte Docs
- [x] `docs/CONTRIBUTING.md`: `docker-compose` → `docker compose`, `start_app.sh` entfernt, Linter Black/isort/flake8 → Ruff
- [x] `docs/pdf_xml_handling.md`: ReportLab → WeasyPrint, Ghostscript entfernt (aus Deps-Tabelle), Code-Beispiele aktualisiert

### 9.2 Python-Version vereinheitlicht
- [x] `pyproject.toml`: `target-version = py312` → `py313` (Black + Ruff)

### 9.3 except Exception → spezifische Exceptions
- [x] `rest_views.py`: 8 Blöcke spezifiziert (OSError/ValueError für PDF/XML, DatabaseError für Stats, IntegrityError/KeyError für Imports)
- [x] `health.py`: 8 Blöcke spezifiziert (OperationalError, HealthCheckError, ImportError)
- [x] `middleware/audit.py`: 5 Blöcke spezifiziert (DatabaseError, AttributeError/TypeError/ValueError)
- [x] `services/invoice_service.py`: 2 Blöcke spezifiziert (OSError/ValueError, pikepdf.PdfError/FileNotFoundError)

### 9.4 Dockerfile optimiert
- [x] `build-essential` entfernt (~200MB kleiner)
- [x] Ghostscript beibehalten (wird aktiv für PDF/A-3 verwendet)

### 9.5 .dockerignore erweitert
- [x] `htmlcov`, `test-artifacts`, `docs/archive`, `security-reports` hinzugefügt

---

## Phase 10: Abschluss

- [x] Tests bestanden
- [x] Alle Änderungen committed
- [x] Push zu `origin` und `github`
