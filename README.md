# eRechnung

Electronic invoice management system compliant with ZUGFeRD/Factur-X (EN 16931). Full-stack application with Django REST backend, Vue.js SPA frontend, and PDF/A-3 generation with embedded XML.

## Quick Start

```bash
git clone <repository-url> && cd erechnung
cd scripts && ./generate-secrets.sh && cd ..
cd scripts && ./start_app.sh
```

Open http://localhost:5173 (frontend) or http://localhost:8000/admin/ (Django admin).

See [Installation Guide](docs/INSTALLATION.md) for full setup instructions.

## Features

- **Invoice Management** — Create, edit, and manage invoices, companies, and business partners
- **ZUGFeRD/Factur-X** — Compliant XML generation (ZUGFeRD 2.3, UN/CEFACT CII) with XSD + Schematron validation
- **PDF/A-3** — PDF generation via WeasyPrint with embedded ZUGFeRD XML (pikepdf)
- **Profile Support** — BASIC, COMFORT, and EXTENDED profiles
- **REST API** — Full CRUD API with JWT authentication and OpenAPI/Swagger documentation
- **RBAC** — Role-Based Access Control with 6 predefined roles
- **API Gateway** — nginx with rate limiting and security headers
- **Health Monitoring** — Three-tier health checks (liveness, detailed, readiness)
- **GoBD Compliance** — German digital bookkeeping requirements

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.13+, Django 5.2, Django REST Framework, PostgreSQL 17, Redis 7 |
| **Frontend** | Vue.js 3.5, Vite 8, Pinia 3, Vue Router 5, Tailwind CSS 4, Axios |
| **PDF/XML** | WeasyPrint, pikepdf, lxml, xmlschema, saxonche |
| **Testing** | pytest, Vitest, Playwright (E2E) |
| **Infrastructure** | Docker Compose, k3s (Kubernetes), nginx, Prometheus, Grafana |

## Deployment Modes

| Mode | Use Case | Scaling | Setup |
|------|----------|---------|-------|
| **Docker Compose** | Single host, small teams | Vertical | `cd scripts && ./start_app.sh` |
| **Kubernetes (k3s)** | On-premise / cloud, larger teams | Horizontal | `cd scripts && ./setup-k3s-local.sh` |

Both modes run identical application code. See [Installation Guide](docs/INSTALLATION.md) for details.

## Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/INSTALLATION.md) | Setup for Docker Compose and Kubernetes deployments |
| [Operations Guide](docs/OPERATIONS.md) | Day-to-day commands, backups, updates, monitoring |
| [Architecture](docs/ARCHITECTURE.md) | System components, directory structure, design patterns |
| [API Specification](docs/API_SPECIFICATION.md) | REST API endpoints and authentication |
| [Developer Guide](docs/DEVELOPER_GUIDE.md) | Development workflow, testing, coding conventions |
| [User Manual](docs/USER_MANUAL.md) | End-user guide for the web interface |
| [Security](docs/SECURITY.md) | Security policies, threat model, hardening |
| [Security Implementation](docs/SECURITY_IMPLEMENTATION.md) | Security roadmap and implementation status |
| [ZUGFeRD Conformance](docs/ZUGFERD_CONFORMANCE.md) | XML compliance with EN 16931 |
| [GoBD Implementation](docs/GOBD_IMPLEMENTATION.md) | German bookkeeping compliance |
| [arc42 Architecture](docs/arc42/) | Full arc42 architecture documentation |
| [Contributing](docs/CONTRIBUTING.md) | How to contribute to this project |
| [Progress Protocol](docs/PROGRESS_PROTOCOL.md) | Project milestones and changelog |

## API Contract

`docs/openapi.json` is the **single source of truth** for API field names, data types, and endpoint structure. Regenerate after changes:

```bash
cd scripts && ./regenerate_openapi.sh
```

## SBOM

Software Bill of Materials in CycloneDX 1.6 format: [`SBOM.json`](SBOM.json) (machine-readable) and [`SBOM.md`](docs/SBOM.md) (human-readable).

## License

See [LICENSE](LICENSE) for details.
