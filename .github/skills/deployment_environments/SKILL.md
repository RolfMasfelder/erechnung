---
name: deployment_environments
display_name: Deployment Environments
version: 1.0.0
author: Rolf Masfelder
description: Two independent deployment environments (Docker Compose dev + Kubernetes production-like)
---

# Deployment Environments

There are **two independent deployments** that must look and function identically:

| Environment | URL | Base | Description |
|-------------|-----|------|-------------|
| **Development** | http://localhost:5173 | Docker Compose | Local development, hot-reload |
| **Kubernetes** | http://192.168.178.80 | K3s | Remote machine, production-like |

## Rules

1. **No dependencies between environments**
   - localhost:5173 MUST NOT depend on 192.168.178.80
   - Each environment has its own DB, Redis, backend

2. **Same functionality in both**
   - Vue.js frontend (German UI)
   - Django REST API
   - JWT authentication

3. **Configuration files:**
   - Docker Compose: `docker-compose.yml`
   - Kubernetes: `infra/k8s/k3s/kustomization.yaml`

4. **API URLs:**
   - Development: `VITE_API_BASE_URL=http://localhost:8000/api`
   - Kubernetes: `VITE_API_BASE_URL=/api` (relative URL via api-gateway)

## Starting Environments

### Development (Docker Compose)

```bash
docker compose up -d
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

### Kubernetes (k3s)

```bash
cd scripts/ && ./setup-k3s-local.sh
# → http://192.168.178.80
export KUBECONFIG=~/.kube/config-k3s-local
kubectl apply -k infra/k8s/k3s/
```

## Deployment Variants

- **Docker-Only**: Small Business (1-5 users), single-host
- **Kubernetes**: Enterprise (>10 users), horizontal scaling
