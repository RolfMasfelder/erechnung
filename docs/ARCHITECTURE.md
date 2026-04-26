# Architecture Overview

High-level architecture of the eRechnung application. For detailed architecture documentation (arc42 format), see the [arc42/](arc42/) directory.

---

## System Components

```
┌──────────────────────────────────────────────────────┐
│                    Client Browser                    │
└──────────────┬──────────────────────┬────────────────┘
               │                      │
         Port 5173 (dev)        Port 443 (prod)
               │                      │
               ▼                      ▼
┌──────────────────────┐  ┌───────────────────────────┐
│  Vite Dev Server     │  │  nginx API Gateway        │
│  (Vue.js 3 SPA)      │  │  Rate Limiting + Headers  │
└──────────┬───────────┘  └─────────┬─────────────────┘
           │ /api proxy             │
           ▼                        ▼
┌──────────────────────────────────────────────────────┐
│              Django Backend (DRF)                    │
│  REST API + JWT Auth + RBAC + Admin                  │
├──────────────────┬──────────────┬────────────────────┤
│  Invoice Service │  PDF/XML     │  Health Checks     │
│  CRUD + Business │  WeasyPrint  │  Liveness/Ready    │
│  Logic           │  + pikepdf   │                    │
└────────┬─────────┴──────┬───────┴────────────────────┘
         │                │
    ┌────▼────┐     ┌─────▼─────┐
    │PostgreSQL│     │   Redis   │
    │   17     │     │     7     │
    └──────────┘     └───────────┘
```

---

## Technology Stack

### Backend

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.13+ (Container: 3.14) | Runtime |
| Django | 5.2.x | Web framework |
| Django REST Framework | 3.16+ | REST API |
| drf-spectacular | latest | OpenAPI schema generation |
| PostgreSQL | 17 | Primary database |
| Redis | 7 | Caching + Celery broker |
| WeasyPrint | latest | HTML → PDF rendering |
| pikepdf | latest | PDF/A-3 XML embedding |
| lxml + xmlschema | latest | ZUGFeRD XML generation + XSD validation |
| saxonche | latest | EN16931 Schematron validation (XPath 2.0+) |

### Frontend

| Component | Version | Purpose |
|-----------|---------|---------|
| Vue.js | 3.5.x | UI framework (Composition API) |
| Vite | 8.x | Build tool + dev server |
| Vue Router | 5.x | Client-side routing |
| Pinia | 3.x | State management |
| Axios | 1.14.x | HTTP client with JWT interceptors |
| Tailwind CSS | 4.x | Utility-first styling |

### Testing

| Tool | Purpose |
|------|---------|
| pytest | Backend unit + integration tests |
| Vitest | Frontend unit tests |
| Playwright | E2E tests (containerized) |

### Infrastructure

| Component | Purpose |
|-----------|---------|
| Docker + Docker Compose | Container orchestration (single host) |
| k3s | Lightweight Kubernetes (horizontal scaling) |
| nginx | API gateway with rate limiting + security headers |
| Linkerd | Service mesh with mTLS (k3s only) |
| Prometheus + Grafana + Loki | Monitoring + alerting + log aggregation |
| Falco | Runtime security monitoring (k3s only) |

---

## Project Directory Structure

```
eRechnung_Django_App/
├── .github/                    # CI/CD workflows, AI coding instructions
├── docs/                       # Documentation (this directory)
│   ├── arc42/                  # Full arc42 architecture docs
│   ├── openapi.json            # API schema (single source of truth)
│   ├── API_SPECIFICATION.md    # API quick reference
│   ├── SECURITY.md             # Security policies
│   └── ...                     # See docs/README.md
│
├── frontend/                   # Vue.js 3 Single Page Application
│   └── src/
│       ├── api/                # Axios client + field mappings (ACL)
│       ├── components/         # Reusable Vue components (Base*)
│       ├── composables/        # Vue composables (useAuth, useConfirm, ...)
│       ├── stores/             # Pinia state management
│       ├── views/              # Page components
│       └── tests/              # Unit tests (Vitest)
│
├── project_root/               # Django backend
│   ├── invoice_app/            # Main Django application
│   │   ├── admin/              # Admin interface (RBAC-secured)
│   │   ├── api/                # REST API (serializers, views, permissions)
│   │   ├── models/             # Data models (Company, Invoice, RBAC, ...)
│   │   ├── services/           # Business logic (InvoiceService, PDF/XML)
│   │   ├── tests/              # Backend tests
│   │   ├── utils/              # Utilities
│   │   │   └── xml/            # ZUGFeRD/Factur-X generator + validator
│   │   └── views/              # Django views + health checks
│   ├── invoice_project/        # Django settings + URL config
│   ├── media/                  # User uploads (PDFs, XML)
│   ├── static/                 # Collected static files
│   └── templates/              # Django templates (PDF HTML templates)
│
├── infra/                      # Infrastructure configuration
│   ├── k8s/                    # Kubernetes manifests
│   │   ├── k3s/                # k3s-specific configs
│   │   └── kind/               # Local testing with kind
│   ├── api-gateway/            # nginx configuration
│   ├── postgres/               # PostgreSQL setup
│   └── backups/                # Backup configs
│
├── schemas/                    # Official ZUGFeRD/Factur-X XSD schemas
├── scripts/                    # Utility scripts (see OPERATIONS.md)
│
├── docker-compose.yml          # Base Docker Compose configuration
├── docker-compose.*.yml        # Compose variants (dev, prod, e2e, monitoring)
├── Dockerfile                  # Multi-stage backend container
├── pyproject.toml              # Python project config (Ruff, pytest)
├── requirements.in             # Python dependency ranges
└── requirements.txt            # Pinned Python dependencies (lock file)
```

---

## Key Architecture Patterns

### Anti-Corruption Layer (ACL)

All fields crossing the UI ↔ API boundary are declared in `frontend/src/api/fieldMappings.js`. No Vue component accesses API field names directly. This decouples the frontend from backend schema changes.

See [ACL_FIELD_MAPPING.md](ACL_FIELD_MAPPING.md) for details.

### API Contract: openapi.json

`docs/openapi.json` is the **single source of truth** for API field names, data types, and endpoint structure. When code conflicts with `openapi.json`, the schema wins. Field or type changes must start in `openapi.json` and propagate to code.

### RBAC (Role-Based Access Control)

Six predefined roles control access to all views and API endpoints:

- Models: `UserRole`, `UserProfile`, `SystemConfig`
- Enforced in Django Admin, DRF views, and frontend routing
- See the [User Manual](USER_MANUAL.md) for role descriptions

### PDF/A-3 Pipeline

1. **HTML Template** → WeasyPrint renders to PDF
2. **ZUGFeRD XML** → Generated from invoice data (UN/CEFACT CII format)
3. **Embedding** → pikepdf embeds the XML as a PDF/A-3 attachment
4. Supports BASIC, COMFORT, and EXTENDED profiles

### Health Check Tiers

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `/health/` | Container liveness | No |
| `/health/detailed/` | DB + Redis + disk status | Yes |
| `/health/readiness/` | Kubernetes readiness probe | No |

---

## Deployment Modes

| Aspect | Docker Compose | Kubernetes (k3s) |
|--------|---------------|-------------------|
| Scaling | Vertical (more CPU/RAM) | Horizontal (more pods) |
| Load Balancing | nginx (single instance) | Ingress controller |
| Service Mesh | — | Linkerd (mTLS) |
| Runtime Security | — | Falco |
| Monitoring | Optional Compose stack | Prometheus + Grafana via Ingress |
| Backup | Script-based | Script-based |
| Target | Small teams, development | Production, larger teams |

See [INSTALLATION.md](INSTALLATION.md) for setup instructions for each mode.

---

## Further Reading

- [arc42 Architecture Documentation](arc42/) — Full arc42 template
- [API Specification](API_SPECIFICATION.md) — REST API reference
- [Security](SECURITY.md) — Security policies and threat model
- [Security Implementation](SECURITY_IMPLEMENTATION.md) — Implementation roadmap
- [ZUGFeRD Conformance](ZUGFERD_CONFORMANCE.md) — XML compliance details
- [GoBD Implementation](GOBD_IMPLEMENTATION.md) — German bookkeeping compliance
