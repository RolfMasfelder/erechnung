# ADR 020: Local HTTPS Docker Registry for Kubernetes Image Management

## Status

Accepted (January 2026)

## Date

2026-01-29

## Context

With Kubernetes deployments (ADR-010), we face challenges with external Docker registry dependencies:

1. **External Dependencies**: Pulling images from Docker Hub/Quay during deployment
2. **Rate Limits**: Docker Hub enforces pull rate limits (100 pulls/6h for anonymous, 200 pulls/6h for free accounts)
3. **Deployment Speed**: PostgreSQL:17 takes >12 minutes to pull from Docker Hub
4. **Network Requirements**: Internet connectivity required for every deployment
5. **Reproducibility**: External registries can remove or change images
6. **Offline Capability**: Cannot deploy without external network access

### Requirements

1. **Full Local Control**: All images (application + infrastructure) available locally
2. **Fast Deployments**: Image pulls should be <30 seconds
3. **HTTPS Support**: Secure communication between Kubernetes nodes and registry
4. **Offline Capable**: Deployments work without external internet
5. **CI/CD Integration**: GitHub Actions can push to local registry
6. **Reproducibility**: Exact same images for development and production

## Decision

**We deploy a local HTTPS Docker Registry (v2) on the Kubernetes host for complete image management control.**

### Architecture

```txt
┌─────────────────────────────────────────────────────────────────┐
│                  Host: 192.168.178.80                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │   Docker Registry (Registry 2)                          │   │
│  │   Port: 5000 (HTTPS)                                    │   │
│  │   Storage: /var/lib/registry                            │   │
│  │   TLS: Self-signed certificate                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │   kind Kubernetes Cluster                               │   │
│  │                                                         │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │   │
│  │   │ Control-     │  │ Worker       │  │ Worker       │ │   │
│  │   │ Plane        │  │ Node 1       │  │ Node 2       │ │   │
│  │   │              │  │              │  │              │ │   │
│  │   │ containerd   │  │ containerd   │  │ containerd   │ │   │
│  │   │ + hosts.toml │  │ + hosts.toml │  │ + hosts.toml │ │   │
│  │   └──────────────┘  └──────────────┘  └──────────────┘ │   │
│  │         │                  │                  │         │   │
│  │         └──────────────────┼──────────────────┘         │   │
│  │                            │                            │   │
│  │   Image Pull: 192.168.178.80:5000/*                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation

### Registry Setup

**Docker Compose Configuration:**

```yaml
version: '3.8'
services:
  registry:
    image: registry:2
    container_name: local-registry
    restart: always
    ports:
      - "5000:5000"
    environment:
      REGISTRY_HTTP_ADDR: 0.0.0.0:5000
      REGISTRY_HTTP_TLS_CERTIFICATE: /certs/localhost.crt
      REGISTRY_HTTP_TLS_KEY: /certs/localhost.key
    volumes:
      - /var/lib/registry:/var/lib/docker/registry
      - ./api-gateway/certs:/certs:ro
```

**TLS Certificates:**

- Self-signed certificate from `api-gateway/certs/` (development)
- CN: localhost
- Alternative: Let's Encrypt for production

### Containerd Configuration

**File:** `/etc/containerd/certs.d/192.168.178.80:5000/hosts.toml`

```toml
server = "https://192.168.178.80:5000"

[host."https://192.168.178.80:5000"]
  capabilities = ["pull", "resolve"]
  skip_verify = true  # For self-signed certificates
```

**Applied to all kind nodes:**

```bash
for node in erechnung-control-plane erechnung-worker erechnung-worker2; do
  docker exec $node mkdir -p /etc/containerd/certs.d/192.168.178.80:5000
  docker exec $node sh -c 'cat > /etc/containerd/certs.d/192.168.178.80:5000/hosts.toml <<EOF
server = "https://192.168.178.80:5000"
[host."https://192.168.178.80:5000"]
  capabilities = ["pull", "resolve"]
  skip_verify = true
EOF'
  docker exec $node systemctl restart containerd
done
```

### Image Management

**Images in Local Registry (11 total):**

**Application Images (4):**

- `192.168.178.80:5000/erechnung-web:latest` (Django Backend)
- `192.168.178.80:5000/erechnung-celery:latest` (Celery Worker)
- `192.168.178.80:5000/erechnung-init:latest` (Migration Job)
- `192.168.178.80:5000/erechnung-frontend:latest` (Vue.js Production)

**Infrastructure Images (4):**

- `192.168.178.80:5000/postgres:17`
- `192.168.178.80:5000/redis:7-alpine`
- `192.168.178.80:5000/busybox:1.35`
- `192.168.178.80:5000/nginx:alpine`

**CNI Images (3):**

- `192.168.178.80:5000/calico/node`
- `192.168.178.80:5000/calico/cni`
- `192.168.178.80:5000/calico/kube-controllers`

**Image Push Workflow:**

```bash
# Tag image for local registry
docker tag postgres:17 192.168.178.80:5000/postgres:17

# Push to local registry
docker push 192.168.178.80:5000/postgres:17

# Verify in registry catalog
curl -k https://192.168.178.80:5000/v2/_catalog
```

### Kubernetes Manifest Updates

**Before (external registry):**

```yaml
containers:
- name: postgres
  image: postgres:17  # Pulls from Docker Hub
  imagePullPolicy: IfNotPresent
```

**After (local registry):**

```yaml
containers:
- name: postgres
  image: 192.168.178.80:5000/postgres:17  # Pulls from local registry
  imagePullPolicy: IfNotPresent
```

## Rationale

### Why Local Registry?

**1. Deployment Speed Improvement:**

- **Before:** PostgreSQL pull from Docker Hub: >12 minutes
- **After:** PostgreSQL pull from local registry: <20 seconds
- **Speedup:** 36x faster (1 minute total deployment vs 15 minutes)

**2. No Rate Limits:**

- Docker Hub: 100 pulls/6h anonymous, 200 pulls/6h authenticated
- Local Registry: Unlimited pulls

**3. Offline Capability:**

- Development and deployment without internet
- Air-gapped environments supported
- No external dependencies

**4. Full Control:**

- Exact image versions controlled
- No risk of upstream deletions
- Reproducible builds

**5. CI/CD Integration:**

- GitHub Actions can push to local registry (with VPN/tunnel)
- Consistent images across environments

### Why HTTPS (not HTTP)?

- **User Feedback:** kubelet attempts HTTPS by default
- **Production-like:** HTTPS mirrors real registry setups
- **Security:** Even self-signed certs better than insecure HTTP
- **Future-Proof:** Easy upgrade to proper CA certificates

### Why Self-Signed Certificates?

- **Development:** Fast setup, no external dependencies
- **containerd Support:** `skip_verify = true` works reliably
- **Production Path:** Replace with Let's Encrypt later

## Performance Results

### Deployment Time Comparison

| Component | Docker Hub | Local Registry | Improvement |
|-----------|------------|----------------|-------------|
| PostgreSQL:17 | >12 min | <20 sec | 36x faster ⚡ |
| Redis:7-alpine | ~3 min | <10 sec | 18x faster |
| nginx:alpine | ~2 min | <10 sec | 12x faster |
| **Total Deployment** | ~15 min | ~1 min | **15x faster** 🎉 |

### Image Pull Logs

```bash
Successfully pulled image "192.168.178.80:5000/postgres:17" in 18.642s
Successfully pulled image "192.168.178.80:5000/erechnung-frontend:latest" in 2.355s
Successfully pulled image "192.168.178.80:5000/erechnung-web:latest" in 12.635s
```

## Consequences

### Positive

- ✅ **15x Faster Deployments** (1 min vs 15 min)
- ✅ **No External Dependencies** (offline capability)
- ✅ **No Rate Limits** (unlimited pulls)
- ✅ **Full Image Control** (reproducibility)
- ✅ **Production-like Setup** (HTTPS registry)
- ✅ **kubectl-based Workflow** (no manual `kind load docker-image`)

### Negative

- ⚠️ **Self-signed Certificates** (`skip_verify=true` not production-grade)
- ⚠️ **No Authentication** (registry accessible to anyone on network)
- ⚠️ **Manual Updates** (images must be manually pushed to registry)
- ⚠️ **Storage Management** (registry storage can grow large)

### Neutral

- **Host Dependency:** Registry runs on Kubernetes host (not in cluster)
- **Network Requirement:** All nodes need access to registry IP

## Alternatives Considered

### 1. Insecure HTTP Registry

**Rejected:** Requires `[plugins."io.containerd.grpc.v1.cri".registry.configs]` changes on all nodes, less production-like

### 2. kind load docker-image

**Rejected:** Manual workflow, slow (must load to each node), doesn't scale

### 3. External Registry (Docker Hub, Quay, GitHub)

**Rejected:** Rate limits, costs, external dependencies, slower

### 4. Registry in Kubernetes Cluster

**Considered:** Would require bootstrap problem (how to pull registry image?), more complex

## Future Improvements

1. **Proper CA Certificates:**
   - Let's Encrypt for production
   - Remove `skip_verify=true` requirement

2. **Registry Authentication:**
   - htpasswd for basic auth
   - ImagePullSecrets in Kubernetes

3. **Automatic Image Updates:**
   - Watchtower or Flux for automated updates
   - CronJob to check upstream changes

4. **Registry Backup:**
   - Automated backup of `/var/lib/registry`
   - S3-compatible storage backend

5. **Monitoring:**
   - Prometheus metrics for registry
   - Alerts on storage usage

## Related Decisions

- ADR-010: Kubernetes Orchestration (requires image registry)
- ADR-021: MetalLB LoadBalancer (Kubernetes infrastructure)
- ADR-022: Calico CNI Provider (Kubernetes networking)

## References

- Docker Registry Documentation: <https://docs.docker.com/registry/>
- containerd Registry Configuration: <https://github.com/containerd/containerd/blob/main/docs/hosts.md>
- kind Registry Documentation: <https://kind.sigs.k8s.io/docs/user/local-registry/>
