# Operations Guide

Day-to-day commands for running, maintaining, and administering the eRechnung application.

For initial setup, see [INSTALLATION.md](INSTALLATION.md).

---

## Starting and Stopping

### Docker Compose

```bash
# Start all backend services
docker compose up -d

# Start with frontend dev server
docker compose -f docker-compose.frontend.yml up -d

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes database data)
docker compose down -v

# View logs
docker compose logs -f web          # Backend logs
docker compose logs -f --tail=100   # Last 100 lines, all services
```

### Kubernetes (k3s)

```bash
export KUBECONFIG=~/.kube/config-k3s

# Check status
cd scripts && ./k3s-status.sh

# Scale the Django backend
kubectl scale deployment django-web -n erechnung --replicas=3

# View logs
kubectl logs -n erechnung deployment/django-web -f
```

---

## Docker Compose Files Reference

| File | Purpose | Usage |
|------|---------|-------|
| `docker-compose.yml` | **Base configuration** — core services: Django backend, PostgreSQL, Redis | `docker compose up -d` |
| `docker-compose.dev.yml` | **Development** — Django exposed directly (no API Gateway, faster iteration) | `docker compose -f docker-compose.dev.yml up -d` |
| `docker-compose.dev-volumes.yml` | **Development overlay** — adds host volume mounts for live code reload | `docker compose -f docker-compose.yml -f docker-compose.dev-volumes.yml up -d` |
| `docker-compose.frontend.yml` | **Frontend dev server** — Vite dev server + API Gateway with HTTPS | `docker compose -f docker-compose.frontend.yml up -d` |
| `docker-compose.production.yml` | **Production** — API Gateway, Docker Secrets support, production hardening | `docker compose -f docker-compose.production.yml up -d` |
| `docker-compose.secrets.yml` | **Production with GitHub Secrets** — reads credentials from `secrets/` directory | `docker compose -f docker-compose.secrets.yml up -d` |
| `docker-compose.monitoring.yml` | **Monitoring overlay** — adds Prometheus, Grafana, Loki to any stack | `docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d` |
| `docker-compose.e2e.yml` | **E2E tests** — Playwright container, uses existing backend services | `cd scripts && ./run_e2e_container.sh` |
| `docker-compose.backup-test.yml` | **Backup testing** — isolated PostgreSQL instance for restore verification | `cd scripts && ./backup_restore_test.sh` |
| `docker-compose.update-test.yml` | **Update tests** — fully isolated environment (own ports/network/volumes) | `cd scripts && ./run-update-tests.sh` |

> Overlay files (`dev-volumes`, `monitoring`) always require the base `docker-compose.yml` to be included first with `-f`.

---

## Django Management Commands

All commands must run inside the Docker container:

```bash
# Run migrations
docker compose exec web python project_root/manage.py migrate

# Create a superuser
docker compose exec web python project_root/manage.py createsuperuser

# Collect static files
docker compose exec web python project_root/manage.py collectstatic --noinput

# Open Django shell
docker compose exec web python project_root/manage.py shell

# Check system status
docker compose exec web python project_root/manage.py check
```

> **Never** run `python manage.py` directly on the host. Always use `docker compose exec web`.

---

## Testing

### Backend Tests

```bash
cd scripts && ./run_tests_docker.sh
```

Or run a specific test module:

```bash
docker compose exec web python project_root/manage.py test invoice_app.tests.<module>
```

### Frontend Tests

```bash
# Unit tests (run inside container)
docker compose -f docker-compose.frontend.yml exec frontend npm test

# With coverage
docker compose -f docker-compose.frontend.yml exec frontend npm run test:coverage
```

### E2E Tests

E2E tests run exclusively in containers. Do not install Playwright or browsers on the host.

```bash
cd scripts && ./run_e2e_container.sh
```

For k3s environments:

```bash
cd scripts && ./run_e2e_k3s.sh
```

See [E2E_TESTING.md](E2E_TESTING.md) for details.

---

## Backups and Restore

### Create a Backup

```bash
cd scripts && ./backup.sh
```

Backups are stored in the `backups/` directory.

### Restore from Backup

```bash
cd scripts && ./restore.sh <backup-file>
```

### Test Backup/Restore

```bash
cd scripts && ./backup_restore_test.sh
```

---

## Updates

### Docker Compose

```bash
cd scripts && ./update-docker.sh
```

This script pulls new images, rebuilds containers, runs migrations, and restarts services.

### Kubernetes (k3s)

```bash
cd scripts && ./update-k3s.sh
```

### Rollback (Docker)

```bash
cd scripts && ./rollback-docker.sh
```

---

## PDF Generation

### Generate a Sample Invoice PDF

```bash
docker compose exec web python scripts/generate_sample_pdf.py
```

The generated PDF/A-3 file contains embedded ZUGFeRD XML. Output shows the file path and backend used.

### Generate a Real Invoice

```bash
docker compose exec web python scripts/generate_real_invoice.py
```

### Inspect PDF XML Content

```bash
docker compose exec web python scripts/inspect_pdf_xml.py <path-to-pdf>
```

### Extract XML from PDF

```bash
docker compose exec web python scripts/extract_pdf_xml.py <path-to-pdf>
```

---

## Monitoring

### Docker Compose

Start the monitoring stack alongside the application:

```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

| URL | Service |
|-----|---------|
| http://localhost:3000 | Grafana dashboards |
| http://localhost:9090 | Prometheus metrics & alerts |

Monitoring ports are bound to `127.0.0.1` — accessible only from the local host.

### Kubernetes

| URL | Service |
|-----|---------|
| `http://<k3s-server-ip>/grafana/` | Grafana |
| `http://<k3s-server-ip>/prometheus/` | Prometheus |

### Health Endpoints

The application provides three health endpoints:

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `/health/` | Simple liveness check | No |
| `/health/detailed/` | Component status (DB, Redis, disk) | Yes |
| `/health/readiness/` | Kubernetes readiness probe | No |

---

## OpenAPI Schema Regeneration

When models, serializers, or views change, regenerate the OpenAPI schema:

```bash
cd scripts && ./regenerate_openapi.sh
```

The schema at `docs/openapi.json` is the single source of truth for the API contract.

---

## Dependency Management

### Check for Outdated Dependencies

```bash
docker compose exec web python scripts/check_dependencies.py
```

### Safe Dependency Update

```bash
docker compose exec web python scripts/safe_dependency_updater.py
```

### Update SBOM

```bash
docker compose exec web python scripts/update_sbom.py
```

---

## Security Operations

### Linkerd mTLS (k3s only)

```bash
export KUBECONFIG=~/.kube/config-k3s

# Verify mTLS status
cd scripts && ./verify-linkerd-mtls.sh

# Open Linkerd dashboard
linkerd viz dashboard &
```

### Falco Runtime Monitoring (k3s only)

```bash
# View alerts
kubectl logs -n falco -l app.kubernetes.io/name=falco -f

# eRechnung-specific alerts
kubectl logs -n falco -l app.kubernetes.io/name=falco | grep erechnung
```

### Kubernetes Audit Logs

```bash
ssh <k3s-server> 'sudo tail -20 /var/log/kubernetes/audit/audit.log | jq .'
```

See [SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md) for the full security roadmap.

---

## Useful Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/start_app.sh` | Start application (with `--dev` option) |
| `scripts/run_tests_docker.sh` | Run backend tests |
| `scripts/run_e2e_container.sh` | Run E2E tests in container |
| `scripts/backup.sh` | Create database backup |
| `scripts/restore.sh` | Restore database from backup |
| `scripts/update-docker.sh` | Update Docker deployment |
| `scripts/update-k3s.sh` | Update k3s deployment |
| `scripts/rollback-docker.sh` | Rollback Docker deployment |
| `scripts/generate-secrets.sh` | Generate or rotate secrets |
| `scripts/regenerate_openapi.sh` | Regenerate OpenAPI schema |
| `scripts/k3s-status.sh` | Check k3s cluster status |
| `scripts/generate_sample_pdf.py` | Generate sample invoice PDF |
