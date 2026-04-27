# AI Coding Agent Instructions

## Critical Rules

**Context Efficiency**: Load files ONLY when needed. Use grep_search for overview, read_file for specific sections only.
**Git Commits**: Concise one-line format (feat/fix/refactor). NO long descriptions. Push to BOTH remotes for all commits.
**Docker-First**: ALL commands via `docker compose exec web python project_root/manage.py [cmd]`
**Environment**: Django app with PostgreSQL + Redis in containers.
**npm**: Only for frontend tests, run inside container. NO npm on host machine.
**No `:latest` Tags**: All container images MUST use explicit versioned tags. k8s manifests use `:KUSTOMIZE` (overridden by `kustomization.yaml`). Build scripts use `v<version>-<git-sha>` from `pyproject.toml` + `git rev-parse --short HEAD`.

> **`docs/openapi.json` is the single source of truth** for API field names, data types, and endpoint structure.
> On conflicts between code, docs, or serializers — `openapi.json` always wins.
> Field name or type changes **must start in `openapi.json`** — then propagate to code.

## Two Independent Deployments

Two separate installations that must look and function identically.
**Details**: see `skills/deployment_environments/SKILL.md` (load only when working on deployment).

- **Development**: `docker compose up -d` → http://localhost:5173 (frontend), http://localhost:8000 (backend)
- **Kubernetes**: `kubectl apply -k infra/k8s/k3s/` → http://192.168.178.80
- **No cross-dependencies** — each environment has its own DB, Redis, backend

## Documentation Language Policy — "Outside English, Inside German"

| Document type | Language | Examples |
|---|---|---|
| Public-facing / GitHub entry points | **English** | `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `openapi.json`, `ARCHITECTURE.md` |
| Domain-specific / legal / tax content | **German** | `GOBD_*.md`, `ZUGFERD_*.md`, `USER_MANUAL.md`, `Zertifikate.md` |
| Internal / operational | **German** | `PROGRESS_PROTOCOL.md`, `TODO*.md`, arc42 docs |
| Code comments & docstrings | **English** | all source files |
| Mixed documents | Fix language on next touch — no big-bang rewrites |

**Rule for new content**: When creating or editing a document, follow the language of that document's category above. Never mix languages within a single document.

## Script Files
- All shell scripts (*.sh, *.bat) must be placed in `scripts/` directory
- Small utility python scripts (e.g., `extract_pdf_xml.py`) go to `scripts/`
- No scripts in project root

## Quick Commands
- Backend Tests: `cd scripts && ./run_tests_docker.sh`
- Shell: `docker compose exec web python project_root/manage.py shell`
- E2E Tests (container-only): `cd scripts && ./run_e2e_container.sh`
  - E2E tests run ONLY in containers. Do NOT install anything on host.

## Project Type
- Django 5.2 + DRF (ZUGFeRD/Factur-X invoice system)
- Vue.js 3 frontend (Vite + Pinia + Tailwind)
- PostgreSQL 17 + Redis 7
- nginx API Gateway with RBAC

## Anti-Corruption Layer (UI ↔ API)

> **All fields** crossing the UI ↔ API boundary **must** be declared in `frontend/src/api/fieldMappings.js` — including 1:1 fields.
> No direct access to API field names in components or stores.
> Details: `docs/ACL_FIELD_MAPPING.md`

## Key Paths (load only when relevant)
- **Models**: `invoice_app/models/` (invoice.py, business_partner.py, country.py, user.py, config.py)
- **Services**: `invoice_app/services/` (business logic)
- **API**: `invoice_app/api/` (DRF serializers, views, permissions)
- **Frontend**: `frontend/src/` (Vue components, stores, composables)
- **Field Mappings**: `frontend/src/api/fieldMappings.js` (ACL — UI↔API Feldnamen)
- **Django Root**: `/app/project_root/`
- **Fixtures**: `invoice_app/fixtures/` (countries.json with EU VAT rates)
- **Security**: `docs/SECURITY_IMPLEMENTATION.md` (Security roadmap for both deployment types)

## Git Workflow
- `origin` → Local mirror (always push)
- `github` → GitHub with Actions (always push, USE for CI/PRs)
- Push to BOTH remotes for all commits
- **Merging to main**: Load `skills/git_merge_workflow/SKILL.md` — pull from BOTH remotes before merge

## Where to Find Information (load only when needed)

- **Data Models**: `invoice_app/models/*.py`
- **API Fields** *(Single Source of Truth)*: `docs/openapi.json` (see `skills/openapi/SKILL.md`)
- **API Reference**: `docs/API_SPECIFICATION.md`
- **UI↔API Field Mapping**: `docs/ACL_FIELD_MAPPING.md`
- **Tasks**: `TODO.md`
- **Progress**: `docs/PROGRESS_PROTOCOL.md` (see `skills/progress_protocol/SKILL.md`)
- **Security**: `docs/SECURITY_IMPLEMENTATION.md`
- **Deployment**: `skills/deployment_environments/SKILL.md`
- **GitHub Actions**: `skills/github_actions/SKILL.md` (action versions & workflow conventions)
- **Initial Start / Clone**: `skills/initial_start/SKILL.md` (Pflichtschritte nach erstem Clone: TLS-Certs, Verzeichnisse, SELinux, node_modules)
- **Concurrent Access / Edit-Lock**: `skills/concurrent_access/SKILL.md` (Pflichtmuster für parallele Bearbeitung, 423-Fehler, Heartbeat)
