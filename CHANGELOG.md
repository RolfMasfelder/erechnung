# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [1.0.0] - 2026-03-17

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
