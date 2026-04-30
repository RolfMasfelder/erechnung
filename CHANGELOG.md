# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [0.1.6] - 2026-04-29

### Hinzugefügt

- E-Mail-Versand für Rechnungen via SMTP (`POST /api/invoices/{id}/send_email/`),
  IONOS Live-Test bestanden, kill-switch `INVOICE_EMAIL_ENABLED`,
  DRAFT→SENT Auto-Transition, Mailpit-Service für Dev (TODO 3.5)
- Frontend `SendInvoiceModal.vue` mit Empfänger-Vorbefüllung aus Geschäftspartner
- Tracking-Felder `last_emailed_at` und `last_email_recipient` (Migration 0013)
- Hybrid-Audit-Log für Imports (CSV-Geschäftspartner / Produkte)
- GDPdU/IDEA-Export-Endpoint für Steuer-Audits (TODO 1.6)
- User-Settings + Passwort-Änderung + System-Info-Endpoints (TODO 2.8)
- `SettingsView` mit Tabs und `PasswordChangeModal`
- Persistenter OfflineBanner + `useNetworkStatus` Singleton-Composable
- ErrorBoundary-Komponente, `console.log` auf DEV-Builds beschränkt (TODO 3.15)
- Pessimistischer Edit-Lock für gleichzeitige Rechnungsbearbeitung (ADR-024)
- Drei Namespaces in K3s: `erechnung`, `erechnung-staging`, `monitoring`;
  E2E-Tests laufen gegen Staging
- CodeQL- und Trufflehog-Workflows für Public-Repo-Security-Scanning
- Issue- und Pull-Request-Templates

### Geändert

- `create_test_data` → `generate_test_data` Refactoring, K3s-Staging-Overlay
- Ruff auf `0.15.12` über pre-commit, CI und requirements vereinheitlicht
- PDF/A-3 mit eingebetteter ZUGFeRD-XML als Default-Anhang beim E-Mail-Versand;
  separate XML nur opt-in
- GoBD: `pdf_file` und `xml_file` zu `allowed_lock_fields` hinzugefügt

### Behoben

- Schematron BR-16 / BR-CO-26 in Tests, Dependabot-Python-Version gepinnt
- Stale Tests nach Model-Refactoring (`test_stats`, `test_version`)
- E2E `workers=1` und `networkidle` für stabile DOM-Counts
- Media-PVC + nginx-Alias für Downloads, Credit-Note-Serial-Tests

## [0.1.1] - 2026-03-17

### Hinzugefügt

- ZUGFeRD/Factur-X Rechnungserstellung (EN16931-konform)
- PDF/A-3b Erzeugung mit eingebettetem XML
- Geschäftspartner- und Produktverwaltung
- Dashboard mit Statistiken und KPIs
- JWT-Authentifizierung (Access + Refresh Token)
- DSGVO-Modul (Betroffenenrechte, Verarbeitungsverzeichnis, DSFA, Einwilligungen)
- GoBD-Compliance (Audit-Trail, Integritätsprüfung, Aufbewahrungsmanagement)
- CSV-Import für Geschäftspartner und Produkte
- Vue.js 3 Frontend mit Tailwind CSS
- Docker Compose Deployment (Entwicklung + Produktion)
- Kubernetes (K3s) Deployment mit Kustomize
- PostgreSQL 17 mit pgTAP-Tests
- Redis 7 für Celery Task-Queue
- nginx API-Gateway mit RBAC
- Prometheus-Metriken mit Business-KPIs
- Health-Check-Endpoints (liveness, readiness, detailed)
- OpenAPI 3.0 Schema (drf-spectacular)
- E2E-Tests mit Playwright
- Anti-Corruption Layer für UI↔API Feldmapping
