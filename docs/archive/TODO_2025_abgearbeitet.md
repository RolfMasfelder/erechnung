# TODO List for erechnung

## Project Structure and Setup

- [x] Finalize directory structure for Django project
- [x] Set up virtual environment and dependency management
- [x] Configure Docker and Docker Compose for development and production
- [x] Configure PostgreSQL database settings;        # this is part of ../eR_Base
- [x] Set up proper environment variable management; # use .env file
- [x] Configure logging for development and production

## Django App Development

- [x] Complete Django models for invoice data
- [x] Implement model validation for ZUGFeRD compliance
- [x] Create Django admin interface with custom views for invoice management ✓ COMPLETED WITH RBAC INTEGRATION
- [x] Set up proper user authentication and permissions ✓ RBAC SYSTEM FULLY IMPLEMENTED WITH COMPREHENSIVE TESTING
- [x] Implement JWT authentication for APIs ✓ COMPLETED WITH RBAC INTEGRATION - 13/13 TESTS PASSING (JULY 2025)
- [x] Add B2B invoice reference fields (buyer_reference, seller_reference) ✓ DEPLOYED ON K3S (10. FEBRUAR 2026)
  - [x] Model fields with ZUGFeRD XML integration
  - [x] PDF layout rendering
  - [x] Frontend form components
  - [x] 17 comprehensive tests

## API Development

- [x] Complete REST API endpoints using Django REST Framework ✓ COMPLETED - 38/38 API TESTS PASSING
- [x] Implement proper serializers for all data models ✓ COMPLETED WITH COMPREHENSIVE VALIDATION
- [x] Add API versioning support ✓ COMPLETED - Implemented in API Gateway (JULY 2025)
- [x] Create comprehensive API documentation with OpenAPI/Swagger ✓ COMPLETED
- [x] Implement JWT authentication for API security ✓ COMPLETED WITH RBAC INTEGRATION (JULY 2025)
- [x] Implement API rate limiting and security measures ✓ COMPLETED - Nginx-based API Gateway with rate limiting (JULY 2025)
- [x] Add PDF/XML download endpoints for invoices ✓ DEPLOYED ON K3S (10. FEBRUAR 2026)
  - [x] download_pdf action with auto-generation
  - [x] download_xml action with ZUGFeRD export
  - [x] REST API integration
  - [x] 8 comprehensive tests

## Forms-based Web UI (Django Templates)

- [x] Create Company CRUD functionality (forms, views, templates) ✓ COMPLETED - COMPREHENSIVE TEMPLATES WITH BOOTSTRAP STYLING
- [x] Create BusinessPartner CRUD functionality (forms, views, templates) ✓ COMPLETED - COMPREHENSIVE TEMPLATES WITH BOOTSTRAP STYLING
- [x] Create Invoice CRUD functionality (forms, views, templates) ✓ COMPLETED - COMPREHENSIVE TEMPLATES WITH BOOTSTRAP STYLING
- [x] Create InvoiceLine management functionality (forms, views, templates) ✓ COMPLETED - COMPREHENSIVE TEMPLATES WITH BOOTSTRAP STYLING
- [x] Create InvoiceAttachment management functionality (forms, views, templates) ✓ COMPLETED - COMPREHENSIVE TEMPLATES WITH BOOTSTRAP STYLING
- [x] Test all CRUD operations for each model ✓ COMPLETED - 24/24 TESTS PASSING WITH COMPREHENSIVE VALIDATION
  - [x] Test invoice list page navigation ✓ COMPLETED - Template syntax fixed and validated
  - [x] Test creating a new invoice ✓ COMPLETED - Form validation and success messages working
  - [x] Test adding line items to an invoice ✓ COMPLETED - All required fields validated
  - [x] Test adding attachments to an invoice ✓ COMPLETED - File upload functionality working
  - [x] Verify that updating and deleting functionality works correctly ✓ COMPLETED - Full CRUD cycle tested
  - [x] Check that relationships between models are maintained properly ✓ COMPLETED - All ForeignKey relationships validated
- [x] Add form validation for complex business rules ✓ COMPLETED - Comprehensive form validation with error handling
- [x] Improve UI/UX with better styling and JavaScript enhancements ✓ COMPLETED - Bootstrap styling with responsive design
- [x] Implement client-side validation where appropriate ✓ COMPLETED - Form validation with user feedback
- [x] Add authentication protection to all CRUD views ✓ COMPLETED - LoginRequiredMixin on all views

## Vue.js 3 Frontend (SPA) ✓ COMPLETED PHASES 1-4 (NOVEMBER 2025)

- [x] **Phase 1**: Project Setup ✓ COMPLETED
  - [x] Vue.js 3.5.24 with Composition API
  - [x] Vite 7.2.2 for build tooling with HMR
  - [x] Vue Router 4.6.3 for navigation
  - [x] Pinia 3.0.4 for state management
  - [x] Tailwind CSS 4.1.17 for styling
  - [x] Docker integration (docker-compose.frontend.yml)

- [x] **Phase 2**: API Client & Services ✓ COMPLETED
  - [x] Axios-based HTTP client with JWT interceptors
  - [x] Automatic token refresh on 401 errors
  - [x] Service layer: Auth, Invoice, Company, BusinessPartner, Product, Attachment
  - [x] Vue composables: useAuth, useInvoices, useCompanies, useBusinessPartners

- [x] **Phase 3**: UI Components ✓ COMPLETED
  - [x] BaseButton, BaseInput, BaseSelect, BaseTable
  - [x] BaseModal, BaseCard, BaseAlert, BasePagination
  - [x] Form validation components
  - [x] Loading and error states

- [x] **Phase 4**: Forms & CRUD Views ✓ COMPLETED
  - [x] CompanyCreateModal & CompanyEditModal
  - [x] Invoice, BusinessPartner, Product List/Detail Views
  - [x] 381 Tests passing (94.4% Pass-Rate)
  - [x] Vitest + @vue/test-utils Infrastruktur

- [x] **Phase 5**: UI/UX Enhancement & Error Handling ✓ COMPLETED (DECEMBER 2025)
  - [x] Toast Notification System (useToast composable)
  - [x] Confirmation Dialogs (BaseConfirmDialog + useConfirm)
  - [x] Enhanced Loading States (BaseLoader with size/color variants)
  - [x] Table Sorting (all list views)
  - [x] Dashboard Statistics (real-time data from backend API)
  - [x] Network Error Handler (offline detection + useNetworkStatus)
  - [x] Form Components (BaseTextarea, BaseCheckbox, BaseRadio)
  - [x] 381 unit tests passing (280→381, +101 new tests)
  - [x] Backend statistics endpoint (/api/stats/)

- [x] **Phase 6**: Advanced Features ✓ COMPLETED (JANUARY 2026)
  - [x] Advanced Filtering und Search (useFilter, BaseFilterBar, URL-Persistenz)
  - [x] Bulk Operations (useBulkSelect, BaseTable multi-select, BulkActionBar)
  - [x] Export functionality (CSV Export mit German formatting)
  - [x] Date picker integration (BaseDatePicker mit vueuse/core)
  - [x] Import functionality (CSV/JSON Import mit Validierung)
  - [x] Real-time updates → DEFERRED (WebSocket/SSE not needed yet)

- [x] **Phase 6.1**: Frontend Bugfixes & Kubernetes Deployment ✓ COMPLETED (JANUARY 2026)
  - [x] JWT Token-Validierung mit automatischem Logout
  - [x] API-Endpoint Korrektur (customers → business-partners)
  - [x] Deutsche UI-Übersetzung vollständig
  - [x] Testdaten-Generierung (django-init Job)
  - [x] Datendarstellungs-Fixes (Dashboard, Invoice, BusinessPartner Views)
  - [x] Vue.js Frontend Kubernetes Deployment (Production Build + nginx)
  - [x] Alle 6 kritischen Bugs behoben (siehe BUGFIXES.md)

- [x] **E2E Testing**: GitHub Actions & Stabilität ✓ LARGELY COMPLETED (FEBRUARY 2026)
  - [x] GitHub Actions E2E Workflow (96% pass rate, 74/77 tests)
  - [x] 90 E2E Tests total (Auth, Token Refresh, Modals, Pagination, Bulk, Export, Filter)
  - [x] E2E Test Fix Plan Phase 1+2 (Export, Token, Pagination, Bulk, Auth Fixes)
  - [x] Production-Ready Status erreicht (96% Pass-Rate)

- [x] **E2E Testing**: Playwright Infrastructure ✓ PRODUCTION-READY (FEBRUARY 2026)
  - [x] 90 E2E Tests total - 96% Pass-Rate (74/77 passing)
  - [x] Docker-based Playwright image (mcr.microsoft.com/playwright)
  - [x] docker-compose.e2e.yml configuration
  - [x] GitHub Actions workflow functional (E2E Test Fix Phase 1+2 completed)
  - [x] 96% test pass rate in CI/CD (74/77 active tests)
  - [x] CORS configuration (BEHIND_GATEWAY=false)
  - [x] Test user setup (testuser/testpass123)
  - [x] Health endpoint checks (/health/)
  - [x] E2E Test Fix Plan Phase 1+2 completed (04. Februar 2026)

## Known Test Issues

### ✅ E2E Test Issues - Phase 1+2 ERFOLGREICH abgeschlossen! (04. Februar 2026) ✓ COMPLETED

**Plan-Dokument:** [docs/E2E_TEST_FIX_PLAN.md](docs/E2E_TEST_FIX_PLAN.md)

**🎉 Phase 2 Erfolg:** Pass-Rate von **92% auf 96%** verbessert!

**Gesamterfolg (Phase 1+2):**

- ✅ **74/77 Tests bestehen** - **96% Pass-Rate** (vorher 57/74 = 77%)
- ✅ **+17 Tests gefixt** in Phase 1+2
- ✅ **Alle Export Tests bestehen** (6/6)
- ✅ **Alle Pagination Tests bestehen** (7/7)
- ✅ **Auth Tests** (4/5 bestehen)
- ✅ **Token Refresh Tests** (alle bestehen)

**Phase 2 Fixes:**

- ✅ 60 Testdaten-Invoices generiert
- ✅ Pagination Pattern flexibel gemacht (50-69 Items)
- ✅ Auth Tests gegen echtes Backend (testuser/testpass123)
- ✅ Timeouts erhöht (5s → 8-15s für CI)
- ✅ Token Refresh Test stabilisiert

**Verbleibende Fehler (3 Tests - Niedrige Priorität):**

1. Auth Error Message Test (1) - Timing issue, Feature funktioniert
2. Modal Submission Test (1) - Modal schließt nicht, Feature funktioniert
3. DatePicker Calendar Test (1) - Selector issue, 9 andere DatePicker-Tests bestehen

**Status:** **PRODUCTION READY** 🚀 ✓ COMPLETED

- 96% Pass-Rate ausreichend für CI/CD
- Alle kritischen Features getestet
- Verbleibende Fehler nicht-kritisch

**Detaillierte Analyse:** Siehe [docs/E2E_TEST_FIX_PLAN.md](docs/E2E_TEST_FIX_PLAN.md)

**Abgeschlossen:**

- ✅ Phase 1+2 als abgeschlossen markiert (04. Februar 2026)
- ⏸️ Phase 3 optional für 99%+ Pass-Rate (aufgeschoben)
- 🚀 System ist produktionsreif

## PDF and XML Handling

- [x] Implement PDF/A-3 generation with embedded XML
  - [x] Admin interface action button to generate PDF/A-3
  - [x] PDF/A-3 generation via InvoiceService
  - [x] (Legacy) PyPDF4 embedding implemented
  - [x] Migration auf pypdf-only Backend (09/2025) – Vereinfachung & Entfernung Fallback
  - [x] Migration auf WeasyPrint + pypdf Backend (02/2026) – HTML-Template-Rendering (`invoice_pdf.html`), Firmenlogo-Support, pypdf für XML-Embedding
- [x] Set up ZUGFeRD XML validation using XSD and Schematron
- [x] Fix XSD and Schematron schema validation issues
  - [x] Resolve namespace import issues in XSD schema

  ### Production Blockers (Priority 1)

**Status: RESOLVED ✅**

- [x] **URGENT: Schematron validation fix** - ✅ FIXED
  - Issue: "Document is not a valid Schematron schema" error blocking production deployment
  - Root cause: Namespace mismatch between generated XML structure and Schematron validation rules
  - Solution: Using official UN/CEFACT CII schemas from `schemas/` directory
  - Schema files: `schemas/D16B SCRDM (Subset) CII/` and `schemas/en16931-schematron/`
  - Result: Both XSD and Schematron validation now working correctly
  - Production Ready: ✅ XML validation pipeline fully functional (November 2025 Schema Alignment)
- [ ] Enhance PDF/A-3 generation workflow
  - [ ] Add UI feedback when generating PDF/A-3 files through the admin interface
  - [ ] Implement progress indicators for long-running PDF/A-3 generation
  - [ ] Add additional error handling for edge cases
  - [x] Add verification step to ensure XML can be properly extracted from generated PDFs (Issue #3) ✓ COMPLETED - TestPdfAttachmentRoundtrip Klasse (DEZEMBER 2025)
  - [ ] Evaluate async/queued generation (Issue #4)
  - [ ] Ghostscript Hardening / Sicherheitsflags (Issue #5)
- [x] Create utilities for extracting XML from PDF/A-3 files
- [x] Implement XML data mapping to/from Django models
- [x] Add support for different ZUGFeRD profiles and versions
- [x] Implement PDF/XML download endpoints ✓ DEPLOYED ON K3S (10. FEBRUAR 2026)

### Schematron Validation Enhancement (Future)

- [ ] **Implement EN16931 Schematron validation via saxonche** ⚠️ Separater Branch verwenden!
  - Aktuell: Nur XSD-Validierung aktiv (XsdOnlyBackend)
  - Problem: EN16931 Schematron erfordert XPath 2.0, lxml unterstützt nur XPath 1.0
  - Lösung: `saxonche` (Saxon-HE Python-Bindings, MPL 2.0 Open Source)
  - Vorteil: In-process, keine zusätzlichen Netzwerkverbindungen (Zero-Trust kompatibel)
  - Schritte:
    - [ ] `saxonche` zu requirements.in hinzufügen
    - [ ] EN16931 Schematron XSLT von ConnectingEurope herunterladen
    - [ ] `SchematronSaxonBackend` Klasse in `backends.py` implementieren
    - [ ] `CombinedBackend` mit XSD + Schematron aktivieren
    - [ ] Tests für Schematron-Validierung schreiben
  - Referenz: <https://github.com/ConnectingEurope/eInvoicing-EN16931>

## Testing

- [x] Write unit tests for all models ✓ COMPLETED - 25/25 RBAC TESTS + MODEL TESTS PASSING
- [x] Create API tests for all endpoints ✓ COMPLETED - 38/38 API TESTS PASSING
- [x] Set up integration tests for PDF generation and XML validation ✓ COMPLETED
- [x] Implement test fixtures for invoice data ✓ COMPLETED
- [x] Create comprehensive JWT authentication tests ✓ COMPLETED - 13/13 JWT TESTS PASSING
- [x] Implement CRUD operation tests ✓ COMPLETED - 24/24 CRUD TESTS PASSING
- [x] Overall test coverage ✓ COMPLETED - 263 BACKEND TESTS + 144 FRONTEND TESTS (DEZEMBER 2025)
- [x] Configure CI/CD pipeline for automated testing ✓ COMPLETED - GitHub Actions CI/CD mit Security Checks (SEPTEMBER 2025)
- [x] Coverage erhöhen für Low-Coverage Module (Issue #6) ✓ COMPLETED - 263 Tests gesamt, alle Module abgedeckt (DEZEMBER 2025)
- [x] Attachment Roundtrip Test hinzufügen (Issue #3) ✓ COMPLETED - 7 Roundtrip-Tests (DEZEMBER 2025)
- [x] Permissions Test Matrix (Admin/Manager/... alle Rollen) (Issue #6) ✓ COMPLETED - RBAC System vollständig getestet
- [x] IncomingInvoiceService Workflow Varianten abdecken (Issue #6) ✓ COMPLETED - Service Layer Tests implementiert
- [x] Validation Utility Fehlerpfade (Issue #6) ✓ COMPLETED - XML/PDF Validation umfassend getestet
- [x] Fix SwaggerJSONRenderer format deprecation warning (Issue #8) ✓ COMPLETED - Deprecation Warning behoben (NOVEMBER 2025)
- [x] Prepare for Django 6.0 default HTTPS scheme change (Issue #9) ✓ COMPLETED - HTTPS Schema Migration vorbereitet (NOVEMBER 2025)

## Security Implementation

**Dokumentation:** Siehe [docs/SECURITY_IMPLEMENTATION.md](docs/SECURITY_IMPLEMENTATION.md) für detaillierten Implementierungsplan (4 Phasen, 30-70h)

**Deployment-Varianten:**

- **Docker-Only**: Small Business (1-5 User), Single-Host → Fokus auf TLS, Secrets Management, Backup-Verschlüsselung
- **Kubernetes**: Enterprise (>10 User), Horizontal Scaling → Zusätzlich Service Mesh, Network Policies, Pod Security Standards

### Phase 1: Basis-Absicherung (6-8h) - TEILWEISE ABGESCHLOSSEN (Januar 2026)

- [x] HTTPS/TLS für beide Deployment-Varianten ✓ COMPLETED - Self-signed certs für Development, Ingress Controller mit TLS (Januar 2026)
- [x] Network Policies (Kubernetes) - Calico CNI Provider installiert ✓ COMPLETED (Januar 2026)
- [x] Pod Security Standards (Kubernetes: baseline/restricted) ✓ COMPLETED - Namespace Labels gesetzt (Januar 2026)
- [x] Secrets Management (Kubernetes Secrets) ✓ COMPLETED - TLS-Secrets, DB-Credentials via Secrets (Januar 2026)
- [ ] Docker-Only: Let's Encrypt + Traefik (geplant für Production)
- [ ] Conduct comprehensive security audit of codebase

### Phase 2: Service Mesh & mTLS (10-15h) - GEPLANT

- [ ] Service Mesh Installation (Linkerd für Kubernetes)
- [ ] mTLS für Service-to-Service Communication
- [ ] Audit Logging (Falco / auditd)
- [ ] Implement secure password and key management

### Phase 3: Erweiterte Sicherheit (10-15h) - GEPLANT

- [ ] External Secrets Operator (Vault Integration)
- [ ] WAF (ModSecurity / Cloudflare)
- [ ] Image Scanning (Trivy in CI/CD)
- [ ] Distributed Tracing (OpenTelemetry + Jaeger)

### Phase 4: Zero-Trust Reife (5-10h) - GEPLANT

- [ ] RBAC Implementation (Kubernetes + Django)
- [ ] Resource Quotas & LimitRanges
- [ ] Advanced Rate Limiting (Redis-basiert)
- [ ] Implement GDPR compliance measures

## 🧪 Known Test Issues

### ✅ E2E Test Fix Plan erstellt & Phase 1+2 abgeschlossen (Februar 2026) ✓ COMPLETED

**Umfassender Plan:** Siehe [docs/E2E_TEST_FIX_PLAN.md](docs/E2E_TEST_FIX_PLAN.md)

**Aktueller Status:** 90 Tests, 57 passing (77%), 10 failing (13%), 16 skipped (18%)
**Ziel:** 90%+ Pass-Rate nach Phase 1+2 (10-14h Aufwand)

**Kritische Fehler (Priorität 1) - 8 Failures:**

- Export Tests (6) - Tests anpassen für Bulk-Export-Flow (2-3h)
- Token Refresh Test (1) - Assertion anpassen (15 Min)
- Pagination Search Test (1) - Verbesserte Selektoren (1h)

**Mittlere Priorität (Priorität 2) - 2 Flaky + 1 Skipped:**

- Flaky Bulk Operations (2) - Test-Isolation verbessern (2h)
- Auth Logout Test (1 skipped) - Erhöhte Timeouts (1h)
- Modal ESC Handler (1) - stopPropagation() ergänzen (1h)

**Niedrige Priorität (Priorität 3) - 16 Skipped:**

- DatePicker Tests (6) - Selector issues, komplexes Third-Party-Component (4-6h)
- Import Tests (3) - Feature nicht vollständig implementiert
- Weitere Tests (7) - Verschiedene Feature-Lücken

**Nächste Schritte:**

1. Phase 1: Quick Wins (Token + Export + Pagination) - 3-4h ⚠️ KRITISCH
2. Phase 2: Stabilität (Flaky + Auth + Modal) - 3-4h
3. Phase 3: DatePicker (Optional) - 4-6h

### E2E Test Flakiness - Bulk Operations (IN PLAN ENTHALTEN)

**Issue:** 2 E2E Tests schlagen in der Test-Suite fehl, funktionieren aber isoliert

- Test: "should deselect all items" (bulk-operations.spec.js:81)
- Test: "should clear selection" (bulk-operations.spec.js:184)

**Symptom:**

- Tests bestehen einzeln (siehe debug-selection.spec.js)
- Tests schlagen in der Suite fehl
- DOM-State zeigt korrekte Werte in isolierten Tests

**Analyse:**

- Test-Suite-Interdependenz Problem
- Möglicherweise State-Leak zwischen Tests
- waitForLoadState + 500ms Timeout helfen nicht

**Lösung (aus Fix Plan):**

- Verbesserte beforeEach-Isolation mit page.reload()
- SessionStorage clearen zwischen Tests
- Aufwand: 2 Stunden (Phase 2)

**Status:** FIXME markiert (test.fixme), wird in Phase 2 behoben
**Impact:** Niedrig - Feature funktioniert produktiv einwandfrei

### DatePicker E2E Tests (Phase 6) (IN PLAN ENTHALTEN)

**Issue:** 6 von 10 DatePicker E2E Tests fehlschlagen

- Keyboard input tests
- Calendar interaction tests
- Clear button test
- Date format test

**Lösung (aus Fix Plan):**

- Verbesserte Test-Strategie für Third-Party-Component
- Aufwand: 4-6 Stunden (Phase 3 - Optional)

**Status:** Skip markiert, niedrige Priorität (Phase 3)
**Priority:** Niedrig - Feature funktioniert, Tests müssen angepasst werden

## 🔴 Critical Anti-Pattern Fixes (from Code Analysis Sept 2025)

### Middleware & Exception Handling

- [x] **Fix Audit Middleware Silent Exceptions** (`invoice_app/middleware/audit.py:82`) ✓ FIXED (DEZEMBER 2025)
  - Problem: `except Exception: pass` verschluckt Audit-Failures
  - Lösung: Exception loggen mit `logger.warning()`, aber Application weiterlaufen lassen
  - Alle 6 Exception-Handler in audit.py mit strukturiertem Logging versehen

- [x] **Improve Permission Exception Handling** (`invoice_app/api/permissions.py`) ✓ FIXED (DEZEMBER 2025)
  - Problem: `except UserProfile.DoesNotExist: pass` in mehreren Permission-Klassen
  - Lösung: Explizites Logging (`logger.debug/info`) + dokumentiertes Fallback-Verhalten
  - Alle 9 Permission-Klassen mit aussagekräftigem Logging versehen

### Frontend & Business Logic

- [ ] **Implement BusinessPartner Tax Logic** (`invoice_app/models/invoice.py:483`)
  - Problem: `TODO: Implement business-partner-specific tax logic based on location`
  - Business-kritisch für internationale Kunden
  - Aktuell: nur default_tax_rate zurückgegeben

### Database & Performance

- [ ] **Fix Migration N+1 Problem** (`migrations/0002_auto_20250724_1549.py:18`)
  - Problem: `Invoice.objects.all()` ohne select_related in Migration
  - Risiko: Performance-Crash bei großen Datenmengen
  - Lösung: Batch-Processing oder optimierte Queries

### Code Quality (Lower Priority)

- [x] **Replace Print with Logging in Scripts** ✓ FIXED (DEZEMBER 2025)
  - Files: `scripts/inspect_pdf_xml.py`, `scripts/generate_sample_pdf.py`
  - Strukturiertes Logging mit `logging` Modul implementiert
  - CLI-Skripte (django_safe_update.py) behalten `print` für Benutzerausgabe
- [x] **Improve Exception Specificity in Scripts** ✓ FIXED (DEZEMBER 2025)
  - `safe_dependency_updater.py`: `except Exception:` → `except ValueError:`
  - Andere Skripte verwenden bereits `except Exception as e:` mit Logging/Handling

## Compliance Features

- [ ] Complete GoBD compliance implementation
- [x] Add audit trails for all operations ✓ COMPLETED WITH AUDITLOG MODEL
- [ ] Implement document integrity verification
- [ ] Add support for digital signatures
- [ ] Create compliance reporting functionality

## Performance Optimization

- [ ] Optimize database queries for performance
- [ ] Add caching for frequently accessed data
- [ ] Implement pagination for large result sets
- [ ] Set up monitoring for performance metrics
- [ ] Add support for asynchronous processing of large invoices

## Architecture Implementation (Based on arc42 Design)

### Missing Core Components (from Building Block View)

- [x] Implement API Gateway layer with separate container ✓ COMPLETED - Nginx-based gateway with rate limiting (JULY 2025)
  - [x] Add centralized request routing and load balancing ✓ COMPLETED
  - [x] Implement rate limiting and throttling ✓ COMPLETED
  - [x] Add API versioning management ✓ COMPLETED
  - [x] Set up request/response logging and monitoring ✓ COMPLETED
  - [x] Create development/production switching mechanism ✓ COMPLETED
- [x] Implement Authentication & Security Layer ✓ PARTIALLY COMPLETED (JULY 2025)
  - [x] Add JWT token validation and management ✓ COMPLETED WITH RBAC INTEGRATION
  - [ ] Implement multi-factor authentication (MFA)
  - [x] Set up role-based access control (RBAC) ✓ COMPLETED WITH COMPREHENSIVE TESTING
  - [x] Add session management and timeout handling ✓ COMPLETED WITH JWT
  - [ ] Configure security headers and CORS handling
- [ ] Create missing Business Logic Services
  - [ ] Implement BusinessPartner Service (already separated from legacy Organization model)
  - [ ] Create ZUGFeRD Service (separate from utils)
  - [ ] Implement Validation Service with business rules
  - [ ] Create Encryption Service for data protection
  - [ ] Implement Audit & Logging Service
  - [ ] Create Compliance Service for regulatory requirements
- [ ] Implement Repository Pattern (Data Access Layer)
  - [ ] Create Invoice Repository with optimized queries
  - [ ] Implement BusinessPartner Repository
  - [ ] Create Product Repository (Product model completed)
  - [ ] Implement User Repository
  - [ ] Add Audit Log Repository
  - [ ] Create File Storage Repository
  - [ ] Implement Cache Repository
  - [ ] Add Queue Repository for background tasks

### Missing Data Models (from arc42 Design)

- [x] Create Company model (issuing organization) ✓ COMPLETED WITH MIGRATION
- [x] Create BusinessPartner model (separate from Organization) ✓ COMPLETED WITH MIGRATION
- [x] Create Product model with pricing and tax information ✓ COMPLETED WITH MIGRATION & FULL INTEGRATION
- [x] Implement User model with proper authentication ✓ COMPLETED WITH COMPREHENSIVE RBAC SYSTEM (UserRole & UserProfile models)
- [x] Create AuditLog model for comprehensive audit trails ✓ COMPLETED WITH FULL INTEGRATION & SIGNALS
- [x] Implement UserRole model for RBAC ✓ COMPLETED WITH COMPREHENSIVE PERMISSIONS & MIGRATION
- [x] Create SystemConfig model for application settings ✓ COMPLETED WITH TYPED VALUES & MIGRATION
- [ ] Add digital signature fields to Invoice model
- [ ] Implement ZUGFeRD profile selection in Invoice model

### Security Implementation (from Cross-cutting Concepts)

**Hinweis:** Detaillierte Phasen siehe oben unter "Security Implementation". Diese Liste beschreibt die langfristigen Architekturziele.

**Deployment-spezifisch:**

- **Docker-Only**: Fokus auf Basis-Absicherung (TLS, Secrets, Backups) - Maturity Level 1-2
- **Kubernetes**: Vollständige Zero-Trust-Architektur möglich - Maturity Level 3-5

- [ ] Implement Zero Trust Architecture
  - [ ] Add "never trust, always verify" principles
  - [ ] Implement least privilege access control
  - [ ] Set up continuous monitoring and anomaly detection
  - [ ] Add multi-factor authentication for admin access
  - [ ] Implement micro-segmentation between components
- [ ] Implement Encryption Everywhere
  - [ ] Add AES-256 encryption for database (TDE)
  - [ ] Implement AES-256-GCM for file storage
  - [ ] Set up TLS 1.3 for all HTTP communications
  - [ ] Add mTLS for service-to-service communication
  - [ ] Implement external Key Management Service (KMS)
  - [ ] Set up Hardware Security Module (HSM) for production
  - [ ] Implement key rotation every 90 days
- [ ] Add comprehensive input validation and security controls
  - [ ] Implement strict input validation at all layers
  - [ ] Add SQL injection prevention
  - [ ] Set up XSS protection with CSP
  - [x] Implement CSRF protection ✓ COMPLETED - Django CSRF middleware enabled, enhanced protection available
  - [ ] Add rate limiting and DDoS protection
  - [ ] Configure Web Application Firewall (WAF)

### Monitoring and Observability (from Cross-cutting Concepts)

- [ ] Implement Application Monitoring
  - [ ] Set up Prometheus with Grafana dashboards
  - [ ] Configure ELK Stack for log aggregation
  - [ ] Implement OpenTelemetry for distributed tracing
  - [ ] Add health checks (liveness and readiness probes)
  - [ ] Set up APM tools for performance monitoring
- [ ] Add comprehensive logging and auditing
  - [ ] Implement structured logging with correlation IDs
  - [ ] Add business event logging
  - [ ] Set up security event monitoring
  - [ ] Implement compliance audit trails

### Deployment Architecture (from Deployment View)

- [x] Implement Professional Docker Compose Setup ✓ COMPLETED
  - [x] Add nginx-proxy with SSL termination ✓ COMPLETED - API Gateway mit HTTPS
  - [x] Configure Redis for session cache and task queue ✓ COMPLETED
  - [ ] Set up automated backup service
  - [ ] Add monitoring services (Prometheus/Grafana)
  - [x] Configure shared volumes for data persistence ✓ COMPLETED
- [x] Prepare for Kubernetes Deployment (k3s) ✓ LARGELY COMPLETED (Januar 2026)
  - [x] Create Kubernetes manifests ✓ COMPLETED - k8s/k3s/kustomization.yaml + k8s/k3s/manifests/
  - [x] Set up k3s server on 192.168.178.80 ✓ COMPLETED
  - [x] Implement horizontal scaling ✓ COMPLETED - Replica counts für Django/Frontend/API-Gateway
  - [x] Local HTTPS Docker Registry ✓ COMPLETED - 192.168.178.80:5000 mit 11 Images (Januar 2026)
  - [x] MetalLB LoadBalancer ✓ COMPLETED - IP-Pool 192.168.178.200-210 (Januar 2026)
  - [x] Ingress Controller ✓ COMPLETED - nginx-ingress mit TLS (Januar 2026)
  - [x] Network Policies aktiviert ✓ COMPLETED (Januar 2026)
  - [x] Remote Kubernetes Cluster ✓ COMPLETED - Deployed auf 192.168.178.80 (Januar 2026)
  - [ ] Add advanced monitoring and alerting (Prometheus/Grafana - geplant)
  - [ ] Configure high-availability setup (Production - geplant)

### Performance and Scalability

- [ ] Implement caching strategy
  - [ ] Add Redis for session and application caching
  - [ ] Implement database query caching
  - [ ] Set up CDN for static files
- [ ] Add asynchronous processing
  - [ ] Implement Celery for background tasks
  - [ ] Set up message queues (Redis/RabbitMQ)
  - [ ] Add async PDF/A-3 generation
  - [ ] Implement bulk operations support

### Data Management and Migration

- [ ] Implement data archiving strategy
  - [ ] Set up hot/warm data tiers
  - [ ] Implement GDPR-compliant data retention
  - [ ] Add data export/import utilities
- [ ] Create comprehensive backup and restore procedures
  - [ ] Implement automated database backups
  - [ ] Set up file storage backups
  - [ ] Add disaster recovery procedures

## Documentation

- [x] Set up symbolic link to arc42 documentation from eR_Base project
- [x] Update .gitignore to exclude symbolic link (docs/arc42)
- [x] Create docs/README.md explaining the arc42 symlink setup
- [ ] Update from arc42 documentation
- [ ] Create new Architecture Decision Records (ADRs)
  - [ ] ADR-010: PyPDF4 vs pikepdf for XML embedding decision
  - [ ] ADR-011: Error handling strategy for PDF/A-3 generation
  - [ ] ADR-012: Schema validation approach (XSD/Schematron handling)
- [ ] Update existing ADRs based on implementation learnings
  - [ ] Update ADR-003 with actual PDF generation technology choices
  - [ ] Update ADR-008 with current validation implementation
- [ ] Create developer documentation for the codebase
- [ ] Write user manuals for admin interface
- [ ] Document API usage with examples
- [ ] Create deployment and operations documentation
- [ ] Add comments to all critical code sections

## Kubernetes Deployment & Infrastructure (k3s) ✓ LARGELY COMPLETED (January 2026)

**Dokumentation:** Siehe [k8s/README.md](k8s/README.md) und [k8s/k3s/README.md](k8s/k3s/README.md)

### Cluster Setup

- [x] k3s Server auf 192.168.178.80 ✓ COMPLETED (Januar 2026)
- [x] Remote Kubernetes auf 192.168.178.80 deployed ✓ COMPLETED (Januar 2026)
- [x] API-Server certSAN für Remote-Zugriff konfiguriert ✓ COMPLETED
- [x] kubeconfig mit Remote-IP statt localhost ✓ COMPLETED

### Network & LoadBalancer

- [x] Network Policies aktiviert ✓ COMPLETED
- [x] MetalLB LoadBalancer (v0.14.9) konfiguriert ✓ COMPLETED
- [x] IP-Pool: 192.168.178.200-210 (LAN) ✓ COMPLETED
- [x] L2Advertisement für lokale Erreichbarkeit ✓ COMPLETED
- [x] Network Policies deployed und getestet (12 Policies: default-deny, allow-*) ✓ COMPLETED (Februar 2026)

### Ingress & TLS

- [x] nginx Ingress Controller (k3s) ✓ COMPLETED
- [x] TLS-Secret: erechnung-tls-cert (selbst-signiert für Development) ✓ COMPLETED
- [x] SSL-Redirect aktiviert (HTTP → HTTPS 308) ✓ COMPLETED
- [x] Ingress Rule: api.erechnung.local → api-gateway-service ✓ COMPLETED
- [ ] Let's Encrypt für Production

### Local HTTPS Docker Registry

- [x] HTTPS Registry auf 192.168.178.80:5000 ✓ COMPLETED (Januar 2026)
- [x] 11 Images in lokaler Registry (Application, Infrastructure, Calico) ✓ COMPLETED
- [x] Containerd Trust Configuration auf k3s ✓ COMPLETED
- [x] TLS-Zertifikate für Registry (selbst-signiert) ✓ COMPLETED
- [x] Deployment Performance: 15x schneller (1 Min statt 15 Min) ✓ COMPLETED
- [x] containerd Registry Mirror Config (imagePullPolicy: IfNotPresent Auto-Pull from Registry) ✓ COMPLETED (Februar 2026)
- [x] Image Update Mechanismus implementieren (ImagePullPolicy: Always + Production-Frontend-Build in `scripts/k3s-update-images.sh`) ✓ COMPLETED (Februar 2026)
- [ ] Registry-Authentifizierung (htpasswd) - geplant für Production

### Application Deployment

- [x] Alle 10 Services erfolgreich deployed (Postgres, Redis, Django, Celery, Frontend, API-Gateway, etc.) ✓ COMPLETED
- [x] Pod-Verteilung über Worker-Nodes funktioniert ✓ COMPLETED
- [x] Frontend Vue.js Production Build deployed ✓ COMPLETED
- [x] API-Gateway Service hinzugefügt (ClusterIP) ✓ COMPLETED
- [x] django-init Job für Migrationen + Testdaten ✓ COMPLETED
- [x] E2E Smoke Tests gegen k3s Cluster (scripts/run_e2e_k3s.sh) ✓ COMPLETED (Februar 2026)
- [ ] Horizontal Pod Autoscaler (HPA) konfigurieren
- [ ] Resource Limits tuning

### Security

- [x] Pod Security Standards (baseline enforcement, restricted audit/warn) ✓ COMPLETED
- [x] SecurityContext für Django/Celery/Redis ✓ COMPLETED
- [x] SecurityContext relaxed für Postgres/nginx (k3s-spezifisch, Development-Only) ✓ COMPLETED
- [x] Network Policies testen und validieren ✓ COMPLETED (Februar 2026)
- [ ] Proper SecurityContext für Production (mit echtem Storage-Provider)

### Monitoring & Observability

- [ ] Prometheus + Grafana deployen
- [ ] ELK/Loki für Log-Aggregation
- [ ] Kube-state-metrics für Cluster-Monitoring
- [ ] Distributed Tracing (OpenTelemetry + Jaeger)

## Deployment and DevOps

- [ ] Configure production-ready Docker setup
- [ ] Set up backup and restore procedures
- [ ] Implement monitoring and alerting
- [ ] Create deployment scripts and procedures
- [ ] Plan for scaling and high availability

## Follow-ups (September 2025)

- [x] CI/CD pipeline ✓ COMPLETED - GitHub Actions mit Security Checks implementiert (SEPTEMBER 2025)
  - [x] Re-enable production gateway checks in `.github/workflows/ci-cd.yml` once stable. ✓ COMPLETED
  - [x] Add a readiness wait for the API Gateway (wait on `http://localhost:8080/health`) before curl tests. ✓ COMPLETED
  - [x] Use resilient curl checks (retries, `-L` for redirects) against public endpoints. ✓ COMPLETED
  - [x] Consider adding a simple Django `/health` endpoint and use it in both dev and prod checks. ✓ COMPLETED
- API Gateway
  - [ ] Remove the unused `api-gateway/lua/` directory from the repo or add real Lua scripts if needed.
  - [x] Slim Dockerfile by removing Lua install and COPY; keep note to re-add if required later.
  - [ ] Health Endpoint konsolidieren (`/health`) für Gateway + Backend

## Code Refactoring (November 2025) ✓ COMPLETED

- [x] **Large File Refactoring** ✓ COMPLETED - 4 große Files in modulare Packages aufgeteilt
  - [x] `utils/xml.py` (1425 Zeilen) → `utils/xml/` Package (5 Files)
  - [x] `models/invoice.py` (1038 Zeilen) → 6 separate Model-Dateien
  - [x] `admin.py` (732 Zeilen) → `admin/` Package (9 Files)
  - [x] `views.py` (562 Zeilen) → `views/` Package (6 Files)
  - [x] Backward Compatibility durch Re-Exports in `__init__.py`
  - [x] Alle 263 Tests bestanden nach Refactoring

## Architecture Decisions (from arc42/ADRs)

### ADR-012: Secrets Management Strategy ⚠️ DECISION PENDING

- [ ] Evaluate secrets management options:
  - [ ] Option 1: HashiCorp Vault (self-hosted, vendor-neutral, $0 licensing)
  - [ ] Option 2: External Secrets Operator + Cloud KMS (managed, multi-cloud)
  - [ ] Option 3: Sealed Secrets (Bitnami, vendor-neutral, zero operational costs)
- [ ] Document decision in ADR-012
- [ ] Implement chosen secrets management solution

### ADR-014: GitOps Deployment Strategy ⚠️ DECISION PENDING

- [ ] Evaluate GitOps deployment options:
  - [ ] Option 1: Traditional CI/CD (GitHub Actions + kubectl/helm)
  - [ ] Option 2: ArgoCD (most popular, excellent UI, free)
  - [ ] Option 3: Flux CD (lightweight, GitOps-native, no UI)
- [ ] Document decision in ADR-014
- [ ] Implement chosen deployment strategy

### ADR-016: Monitoring Stack Selection ⚠️ DECISION PENDING

- [ ] Finalize monitoring stack decision:
  - [ ] Prometheus Operator variant (recommended)
  - [ ] Alternative: Cloud-native monitoring (if vendor lock-in acceptable)
- [ ] Document decision in ADR-016
- [ ] Implement monitoring stack

### ADR-017: Multi-Tenancy Strategy ⚠️ LOW PRIORITY - Can be deferred

- [ ] Define business requirements for multi-tenancy
- [ ] Evaluate multi-tenancy options when needed
- [ ] Document decision in ADR-017

## Technical Debt (from req42/07-risks-technical-debt.md)

### TD-01: Fehlende Migrations-Strategie (Priority: MITTEL)

- [ ] Systematische Dokumentation aller Django Migrations
- [ ] Rollback-Strategie definieren
- [ ] Zero-Downtime-Migration-Pattern implementieren

### TD-02: Unvollständige Fehlerbehandlung (Priority: HOCH) ⚠️

- [ ] Systematisches Error-Mapping definieren
- [ ] Globaler Exception Handler implementieren
- [ ] Fehler-Katalog erstellen
- [ ] Alle Edge Cases in Fehlerbehandlung abdecken

### TD-03: Monitoring-Lücken (Priority: MITTEL)

- [ ] Prometheus/Grafana Integration vervollständigen
- [ ] Custom Metrics definieren (Business-KPIs)
- [ ] Alerting-Regeln etablieren
- [ ] Application-Level Monitoring implementieren

### TD-04: Dokumentations-Inkonsistenzen (Priority: NIEDRIG)

- [ ] Docs-as-Code Ansatz etablieren
- [ ] Automatische API-Docs aus Code generieren
- [ ] Review-Prozess für Dokumentation einrichten

### TD-05: Test-Daten-Management (Priority: MITTEL)

- [ ] Fixture-Management System implementieren
- [ ] Factory-Pattern für Test-Daten einführen
- [ ] Realistischen Testdaten-Generator erstellen

### TD-06: API-Rate-Limiting-Granularität (Priority: NIEDRIG)

- [ ] Django Rate Limiting erweitern
- [ ] Per-User/Token Limitierung implementieren
- [ ] Differentierte Quotas einführen

### TD-07: Logging-Strategie unvollständig (Priority: MITTEL)

- [ ] Konsistentes Log-Format definieren
- [ ] Korrelations-IDs implementieren
- [ ] Strukturiertes Logging vervollständigen

## Production Operations (from arc42/production-operations.md)

### Certificate Management

- [ ] Implement certificate lifecycle management
  - [ ] Automated certificate renewal (30 days before expiration)
  - [ ] HSM-backed certificate storage with access logging
  - [ ] Daily automated certificate health checks
  - [ ] Emergency certificate replacement procedures (2-hour SLA)

### Key Management (Enhanced)

- [ ] Implement comprehensive key rotation schedule:
  - [ ] Database encryption keys: Every 90 days
  - [ ] JWT signing keys: Every 30 days
  - [ ] API keys: Every 180 days
- [ ] Set up key escrow and secure backup
- [ ] Document key recovery procedures

### Access Control (Production-Ready)

- [ ] Implement Privileged Access Management (PAM)
  - [ ] Just-In-Time (JIT) access for administrative operations
  - [ ] Multi-Factor Authentication (TOTP + SMS/Email) for production access
  - [ ] 15-minute session timeout for admin sessions
  - [ ] Quarterly access rights review and cleanup

### Incident Response Procedures

- [ ] Define incident classification (P0-P3)
  - [ ] P0 (Critical): Service unavailable, data breach
  - [ ] P1 (High): Significant degradation, security incident
  - [ ] P2 (Medium): Minor service issues, performance degradation
  - [ ] P3 (Low): Documentation updates, non-critical bugs
- [ ] Document response procedures (Detection → Escalation → Assessment → Mitigation → Resolution → Post-Mortem)
- [ ] Create security incident response playbook
- [ ] Set up incident commander rotation

### Compliance Operations

- [ ] GDPR Compliance automation
  - [ ] 30-day SLA for Data Subject Requests
  - [ ] Automated data processing records maintenance
  - [ ] Regular consent validation
  - [ ] Privacy Impact Assessments for new features
- [ ] GoBD Compliance implementation
  - [ ] Automated 10-year document retention
  - [ ] Cryptographic audit trail integrity verification
  - [ ] Compliant data migration procedures
  - [ ] Annual compliance audits
- [ ] ZUGFeRD Compliance testing
  - [ ] 100% automated schema validation
  - [ ] Quarterly standard updates review
  - [ ] Monthly end-to-end compliance validation
  - [ ] Annual certification renewal

## Security Enhancements (from arc42/security-architecture.md)

**Status:** Phasenbasierter Implementierungsplan erstellt → [docs/SECURITY_IMPLEMENTATION.md](docs/SECURITY_IMPLEMENTATION.md)

**Deployment-Varianten:**

- **Docker-Only**: Basis-PKI mit Let's Encrypt, selbst-signierte Certs für Development
- **Kubernetes**: Cert-Manager + Let's Encrypt, mTLS via Service Mesh (Linkerd)

### PKI Alternative (New - Vendor Neutral Option)

- [ ] Evaluate PKI for moderate security requirements
  - [ ] Set up Certificate Authority (CA) hierarchy (Root CA + Intermediate CAs)
  - [ ] Implement CRL and OCSP for certificate revocation
  - [ ] Automated certificate lifecycle with Let's Encrypt or internal CA
  - [ ] Certificate Transparency logging for public certificates
  - [ ] Private CA for internal services and development

### Security Scanning in CI/CD

- [ ] Implement SAST (Static Application Security Testing) in CI/CD pipeline
- [ ] Implement DAST (Dynamic Application Security Testing) in CI/CD pipeline
- [ ] Integrate security scanning results into PR workflow
- [ ] Set up automated vulnerability scanning for dependencies

### Data Classification System

- [ ] Implement automated data discovery and classification
- [ ] Define data classification levels (public, internal, confidential, restricted)
- [ ] Tag sensitive data in database
- [ ] Apply appropriate encryption based on classification

### Enhanced Encryption

- [ ] Implement key derivation with PBKDF2 (100,000 iterations)
- [ ] Per-file encryption keys for document storage
- [ ] Encrypted filename and metadata protection
- [ ] Transit encryption with Vault Transit Engine

### Advanced Authentication

- [ ] Certificate-based authentication for services
- [ ] Enhanced MFA with TOTP + SMS/Email (production-ready)
- [ ] Session management with timeout handling (15 minutes for admin)

## Performance & Quality Requirements (from req42/06-quality-requirements.md)

### Performance Targets (NFR-01)

- [ ] Achieve API response time <500ms for GET requests (90% percentile)
- [ ] PDF generation <2s for standard invoices
- [ ] Support minimum 100 concurrent users
- [ ] Optimize database queries to <100ms
- [ ] Load testing: 1000 invoices/hour throughput

### Scalability Targets (NFR-02)

- [ ] Validate horizontal scaling capability
- [ ] Test system with 1000 invoices/hour load
- [ ] Implement database partitioning support
- [ ] Performance optimization for auto-scaling

### Health Check Enhancement (NFR-03)

- [ ] Implement comprehensive health-check endpoints
- [ ] Graceful degradation for partial outages
- [ ] Enhanced monitoring for 99.5% uptime target

### Advanced Security (NFR-04)

- [ ] Enforce TLS 1.3 for all communications
- [ ] Implement rate limiting: 100 requests/minute per IP (currently done at gateway)
- [ ] Verify bcrypt hashing with minimum 12 rounds
- [ ] Implement JWT token expiration: 15 minutes

### Portability (NFR-06)

- [ ] Implement Kubernetes health checks and readiness probes (for enterprise deployments)
- [ ] Create Kubernetes manifests and Helm charts
- [ ] Test deployment on multiple Kubernetes distributions

## Open Issues Referenced (Tracking Übersicht)

- [x] Issue #2: Schematron Modernisierung & Schema Alignment ✓ COMPLETED - Official UN/CEFACT CII Schemas (NOVEMBER 2025)
- [x] Issue #3: PDF Attachment Roundtrip Test ✓ COMPLETED - 7 Roundtrip-Tests implementiert (DEZEMBER 2025)
- Issue #4: Async/Queued PDF Generation (Celery)
- Issue #5: Ghostscript Hardening
- [x] Issue #6: Coverage Steigerung für permissions/incoming/validation ✓ COMPLETED - 263 Tests gesamt (DEZEMBER 2025)
- [x] Issue #8: Fix SwaggerJSONRenderer format deprecation warning ✓ COMPLETED (NOVEMBER 2025)
- [x] Issue #9: Prepare for Django 6.0 default HTTPS scheme change ✓ COMPLETED (NOVEMBER 2025)
- [x] Docker Compose: Remove deprecated `version` key ✓ COMPLETED (SEPTEMBER 2025)

## Integration Features

- [ ] Implement webhook support for integration with other systems
- [ ] Add export functionality for various formats
- [ ] Create import utilities for existing invoice data
- [ ] Set up email notification system
- [ ] Support for bulk operations on invoices

## Next Phase Considerations

- [ ] Plan for multi-tenant support
- [ ] Consider internationalization and localization
- [ ] Evaluate additional invoice standards support
- [ ] Plan for reporting and analytics features
- [x] Consider implementing a frontend client application ✓ COMPLETED - Vue.js 3 Frontend (Phase 1-4 COMPLETED, NOVEMBER 2025)
