# Software Bill of Materials (SBOM) - eRechnung Django App

**Generated:** 8. Mai 2026
**Format:** CycloneDX 1.6
**Generation Method:** Automated (update_sbom.py)

## Project Overview

**eRechnung Django App** - German e-invoicing system implementing ZUGFeRD/Factur-X standards with PDF/A-3 + embedded XML, modern Vue.js 3 frontend, and comprehensive E2E testing.

- **Repository:** https://github.com/RolfMasfelder/erechnung
- **Version:** 0.2.0
- **License:** AGPL-3.0-only
- **Architecture:** Full-stack Docker-based microservices with SPA frontend

## Core Technologies

### Runtime Environment
- **Backend:** Python 3.13.13
- **Frontend:** Node.js 24 (Alpine)
- **Base OS:** Debian Bookworm (slim) / Alpine Linux
- **Deployment:** Docker Compose

### Backend Framework & Core Libraries
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Django | 5.2.13 | BSD-3-Clause | Web framework |
| Django REST Framework | 3.17.1 | BSD-2-Clause | API framework |
| drf-spectacular | 0.29.0 | BSD-3-Clause | OpenAPI schema generation |
| Gunicorn | 25.3.0 | MIT | WSGI server |
| Celery | 5.6.3 | BSD-3-Clause | Task queue |

### Frontend Framework & Core Libraries
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Vue.js | 3.5.33 | MIT | Progressive JavaScript framework |
| Vue Router | 5.0.6 | MIT | Official router for Vue.js |
| Pinia | 3.0.4 | MIT | State management for Vue.js |
| Axios | 1.16.0 | MIT | Promise-based HTTP client |
| Vite | 8.0.10 | MIT | Next generation frontend build tool |
| Tailwind CSS | 4.2.4 | MIT | Utility-first CSS framework |

### Database & Cache
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| PostgreSQL | 17 | PostgreSQL License | Primary database |
| Redis | 7-alpine | BSD-3-Clause | Cache & message broker |
| psycopg2-binary | 2.9.12 | LGPL-3.0 | PostgreSQL adapter |
| django-redis | 6.0.0 | BSD-3-Clause | Redis backend |

### E-Invoice Processing
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| factur-x | 4.2 | BSD-2-Clause | ZUGFeRD/Factur-X generation |
| WeasyPrint | 68.1 | BSD-3-Clause | HTML to PDF generation |
| pypdf | 6.10.2 | BSD-3-Clause | PDF processing |
| pikepdf | 10.5.1 | MPL-2.0 | PDF manipulation |
| lxml | 6.1.0 | BSD-3-Clause | XML processing |
| xmlschema | 4.3.1 | MIT | XML schema validation |
| Pillow | 12.2.0 | HPND | Image processing |

### Security & Authentication
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| django-allauth | 65.16.1 | MIT | Authentication system |
| django-axes | 8.3.1 | MIT | Brute force protection |
| djangorestframework-simplejwt | 5.5.1 | MIT | JWT authentication |
| django-cors-headers | 4.9.0 | MIT | CORS handling |
| django-csp | 4.0 | BSD-3-Clause | Content Security Policy |

### Infrastructure Services
| Service | Version | Type | Port | Purpose |
|---------|---------|------|------|---------|
| Django Web App | 1.1.0 | Application | 8000 | Main application |
| Vue.js Frontend | 0.1.0 | Application | 5173 | SPA user interface |
| Nginx Alpine | alpine | Infrastructure | 8080 | Nginx API Gateway (image: nginx:alpine) |
| Python Base Image | 3.13.13-slim-bookworm | Infrastructure | - | Backend runtime (image: python:3.13.13-slim-bookworm) |
| PostgreSQL | 17 | Database | 5432 | Data persistence |
| Redis | 7 | Cache | 6379 | Session cache & broker |
| Celery Worker | 5.5.3 | Background | - | Task processing |

### Backend Development & Quality Tools
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| pytest | 9.0.3 | MIT | Testing framework |
| pytest-django | 4.12.0 | BSD-3-Clause | Django testing |
| coverage | 7.13.5 | Apache-2.0 | Code coverage |
| black | 25.1.0 | MIT | Code formatting |
| ruff | 0.15.12 | MIT | Linting |
| pylint | 3.3.8 | GPL-2.0 | Code analysis |
| pre-commit | 4.6.0 | MIT | Git hooks |

### Frontend Development & Testing Tools
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Vitest | 4.1.5 | MIT | Unit testing framework for Vite |
| @vitest/ui | 4.0.8 | MIT | Vitest UI interface |
| @vitest/coverage-v8 | 4.0.8 | MIT | Code coverage for Vitest |
| Playwright | 1.59.1 | Apache-2.0 | End-to-end testing framework |
| @vue/test-utils | 2.4.10 | MIT | Official Vue.js testing utilities |
| happy-dom | 20.0.10 | MIT | DOM implementation for testing |
| @vitejs/plugin-vue | 6.0.1 | MIT | Vite plugin for Vue.js |
| PostCSS | 8.5.6 | MIT | CSS transformation tool |
| Autoprefixer | 10.4.22 | MIT | CSS vendor prefixing |

### Monitoring & Operations
| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Sentry SDK | 2.58.0 | MIT | Error tracking |
| WhiteNoise | 6.12.0 | MIT | Static file serving |
| django-debug-toolbar | 6.0.0 | BSD-3-Clause | Development debugging |

### System Dependencies
| Component | Package Type | Purpose |
|-----------|--------------|---------|
| Ghostscript | System | PDF/A-3 conversion |
| libpq-dev | System | PostgreSQL client library |
| build-essential | System | Compilation tools |
| gettext | System | Internationalization |
