# Software Bill of Materials (SBOM) - eRechnung Django App

**Generated:** 12. November 2025
**Format:** CycloneDX 1.6
**Generation Method:** Manual Analysis

## Project Overview

**eRechnung Django App** - German e-invoicing system implementing ZUGFeRD/Factur-X standards with PDF/A-3 + embedded XML, modern Vue.js 3 frontend, and comprehensive E2E testing.

- **Repository:** https://github.com/RolfMasfelder/eRechnung_Django_App
- **Version:** 1.1.0
- **License:** MIT
- **Architecture:** Full-stack Docker-based microservices with SPA frontend

## Core Technologies

### Runtime Environment
- **Backend:** Python 3.12.11
- **Frontend:** Node.js 20 (Alpine)
- **Base OS:** Debian Bookworm (slim) / Alpine Linux
- **Deployment:** Docker Compose

### Backend Framework & Core Libraries
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Django | 5.1.12 | BSD-3-Clause | Web framework |
| Django REST Framework | 3.15.2 | BSD-2-Clause | API framework |
| Gunicorn | 23.0.0 | MIT | WSGI server |
| Celery | 5.5.3 | BSD-3-Clause | Task queue |

### Frontend Framework & Core Libraries
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Vue.js | 3.5.24 | MIT | Progressive JavaScript framework |
| Vue Router | 4.6.3 | MIT | Official router for Vue.js |
| Pinia | 3.0.4 | MIT | State management for Vue.js |
| Axios | 1.13.2 | MIT | Promise-based HTTP client |
| Vite | 7.2.2 | MIT | Next generation frontend build tool |
| Tailwind CSS | 4.1.17 | MIT | Utility-first CSS framework |

### Database & Cache
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| PostgreSQL | 17 | PostgreSQL License | Primary database |
| Redis | 7-alpine | BSD-3-Clause | Cache & message broker |
| psycopg2-binary | 2.9.10 | LGPL-3.0 | PostgreSQL adapter |
| django-redis | 6.0.0 | BSD-3-Clause | Redis backend |

### E-Invoice Processing
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| factur-x | 3.8 | BSD-2-Clause | ZUGFeRD/Factur-X generation |
| ReportLab | 4.4.3 | BSD-3-Clause | PDF generation |
| pikepdf | 9.11.0 | MPL-2.0 | PDF manipulation |
| lxml | 6.0.1 | BSD-3-Clause | XML processing |
| xmlschema | 4.1.0 | MIT | XML schema validation |
| Pillow | 11.3.0 | HPND | Image processing |

### Security & Authentication
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| django-allauth | 65.11.2 | MIT | Authentication system |
| django-axes | 8.0.0 | MIT | Brute force protection |
| djangorestframework-simplejwt | 5.5.1 | MIT | JWT authentication |
| django-cors-headers | 4.8.0 | MIT | CORS handling |
| django-csp | 4.0 | BSD-3-Clause | Content Security Policy |

### Infrastructure Services
| Service | Version | Type | Port | Purpose |
|---------|---------|------|------|---------|
| Django Web App | 1.1.0 | Application | 8000 | Main application |
| Vue.js Frontend | 0.1.0 | Application | 5173 | SPA user interface |
| API Gateway | 1.0.0 | Infrastructure | 8080 | Nginx reverse proxy |
| PostgreSQL | 17 | Database | 5432 | Data persistence |
| Redis | 7 | Cache | 6379 | Session cache & broker |
| Celery Worker | 5.5.3 | Background | - | Task processing |

### Backend Development & Quality Tools
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| pytest | 8.4.2 | MIT | Testing framework |
| pytest-django | 4.11.1 | BSD-3-Clause | Django testing |
| coverage | 7.10.6 | Apache-2.0 | Code coverage |
| black | 25.1.0 | MIT | Code formatting |
| ruff | 0.13.0 | MIT | Linting |
| pylint | 3.3.8 | GPL-2.0 | Code analysis |
| pre-commit | 4.3.0 | MIT | Git hooks |

### Frontend Development & Testing Tools
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Vitest | 4.0.8 | MIT | Unit testing framework for Vite |
| @vitest/ui | 4.0.8 | MIT | Vitest UI interface |
| @vitest/coverage-v8 | 4.0.8 | MIT | Code coverage for Vitest |
| Playwright | 1.56.1 | Apache-2.0 | End-to-end testing framework |
| @vue/test-utils | 2.4.6 | MIT | Official Vue.js testing utilities |
| happy-dom | 20.0.10 | MIT | DOM implementation for testing |
| @vitejs/plugin-vue | 6.0.1 | MIT | Vite plugin for Vue.js |
| PostCSS | 8.5.6 | MIT | CSS transformation tool |
| Autoprefixer | 10.4.22 | MIT | CSS vendor prefixing |

### Monitoring & Operations
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Sentry SDK | 2.38.0 | MIT | Error tracking |
| WhiteNoise | 6.10.0 | MIT | Static file serving |
| django-debug-toolbar | 6.0.0 | BSD-3-Clause | Development debugging |

### System Dependencies
| Component | Package Type | Purpose |
|-----------|--------------|---------|
| Ghostscript | System | PDF/A-3 conversion |
| libpq-dev | System | PostgreSQL client library |
| build-essential | System | Compilation tools |
| gettext | System | Internationalization |

## Security Considerations

### Implemented Security Features
- **RBAC (Role-Based Access Control):** 6 predefined user roles with granular permissions
- **API Gateway:** Nginx with rate limiting (API: 100/min, Auth: 20/min, Admin: 10/min)
- **Brute Force Protection:** django-axes for login protection
- **Content Security Policy:** django-csp implementation
- **CORS Protection:** Configured cross-origin handling
- **JWT Authentication:** Token-based API security

### Recommended Security Reviews
- Regular dependency updates via `pip-audit`
- Container image security scanning
- Database access review
- API endpoint security audit

## Compliance & Standards

### German E-Invoicing Standards
- **ZUGFeRD:** Compliant XML generation
- **Factur-X:** International standard support
- **PDF/A-3:** Archival quality with embedded XML
- **XSD Validation:** Schema validation implemented
- **Schematron:** Syntax validation (TODO: fix syntax issues)

## Architecture Notes

### Docker Services
```yaml
Services:
  - web (Django app)
  - frontend (Vue.js + Vite)
  - frontend-e2e (Playwright testing)
  - db (PostgreSQL 17)
  - redis (Redis 7-alpine)
  - celery (Background worker)
  - api-gateway (Nginx - production only)
```

### Environment Configurations
- **Development:**
  - Backend: Direct Django access (localhost:8000)
  - Frontend: Vite dev server (localhost:5173)
  - E2E Testing: Playwright container with HTML reports (localhost:9323)
- **Production:**
  - API Gateway only (localhost:8080)
  - Static frontend build served by Nginx
- **Shared:** PostgreSQL and Redis services

### Key Business Logic
```
InvoiceService → ZugferdXmlGenerator → PdfA3Generator
              ↓
          XML validation (XSD/Schematron) → PDF/A-3 with embedded XML
```

## Test Coverage

- **Backend Tests:** 87+ passing tests
  - Models: 25/25 RBAC + validation tests
  - CRUD: 24/24 web interface tests
  - API: 38/38 REST API tests
  - Integration: PDF/XML generation tests

- **Frontend Tests:**
  - Unit Tests: Vitest with Vue Test Utils
  - E2E Tests: 35 Playwright tests (5/6 passing - 83%)
    - Authentication flow tests
    - Token refresh tests
    - Modal interaction tests
    - Pagination component tests

- **Test Coverage Areas:**
  - Backend: Django models, views, API endpoints, services
  - Frontend: Vue components, composables, stores, routing
  - Integration: Full stack invoice workflow
  - E2E: User journeys through web interface

## Maintenance & Updates

### Update Strategy
- **Python Dependencies:** Regular updates via pip-compile
- **Node.js Dependencies:** npm audit and updates
- **Docker Images:** Automated security updates
- **Database:** PostgreSQL 17 (latest stable)
- **Security Patches:** Continuous monitoring via Sentry

### Latest Updates (November 2025)
- ✅ Added Vue.js 3 SPA frontend with Vite
- ✅ Implemented Pinia state management
- ✅ Added Tailwind CSS for styling
- ✅ Integrated Playwright E2E testing
- ✅ Added Vitest unit testing framework
- ✅ Created comprehensive testing infrastructure

---

**Last Updated:** 12. November 2025
**Next Review:** February 2026

### Development Tools
- **Git Hooks:** Pre-commit formatting and linting
- **CI/CD:** GitHub Actions (on `github` remote)
- **Code Quality:** Black, Ruff, Pylint, Coverage
- **Testing:** pytest with Django integration

---

**Note:** This SBOM represents the current state as of November 12, 2025. For the most up-to-date dependency information, refer to `requirements.txt`, `frontend/package.json`, and the project's CI/CD pipeline.
