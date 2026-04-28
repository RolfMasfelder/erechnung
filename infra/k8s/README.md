# Kubernetes Manifests for eRechnung

This directory contains Kubernetes deployment manifests for the eRechnung electronic invoicing system.

## Files

- **api-gateway-deployment.yaml** - API Gateway deployment with nginx
- **api-gateway-service.yaml** - LoadBalancer service for API Gateway (Production)
- **django-backend-deployment.yaml** - Django application deployment
- **django-backend-service.yaml** - Internal ClusterIP service for Django
- **ingress.yaml** - Ingress configuration for external access (Production)
- **k8s-erechnung.yaml** - Complete all-in-one deployment manifest
- **kind/** - kind-specific configuration for local testing
  - **kind-cluster-config.yaml** - Cluster configuration with Ingress support
  - **api-gateway-service.yaml** - NodePort service (kind-compatible)
  - **ingress.yaml** - Ingress for local testing
  - **setup.sh** - Automated deployment script
  - **teardown.sh** - Cluster cleanup script
  - **README.md** - kind-specific documentation

## Architecture

```txt
Internet → Ingress → API Gateway Service → API Gateway Pods
                                             ↓
                     Django Backend Service → Django Backend Pods
```

## Deployment

### Production Deployment

Deploy all resources in order:

```bash
# Create namespace
kubectl create namespace erechnung

# Deploy all manifests
# weil zusätzliche Konfiguration k8s-erechnung.yaml enthalten alle benötigten expliziten Dateien
kubectl apply -f k8s/api-gateway-deployment.yaml
kubectl apply -f k8s/api-gateway-service.yaml
kubectl apply -f k8s/django-backend-deployment.yaml
kubectl apply -f k8s/django-backend-service.yaml
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get all -n erechnung
```

Or

Deploy k8s-erechnung.yaml directly:

```bash
# Secrets aktualisieren (Base64-encoded)
echo -n "your-secret-key" | base64
echo -n "your-db-password" | base64

# Deployment
kubectl apply -f k8s-erechnung.yaml

# Status prüfen
kubectl get pods -n erechnung
kubectl get services -n erechnung

# Logs anzeigen
kubectl logs -n erechnung deployment/django-web
```

### Local Testing with kind

For local Kubernetes testing, use the kind-specific configuration:

```bash
# Quick start - automated setup
./k8s/kind/setup.sh

# Access application
curl http://localhost/health/

# View logs
kubectl logs -n erechnung -l app=django-web -f

# Cleanup
./k8s/kind/teardown.sh
```

See [k8s/kind/README.md](kind/README.md) for detailed kind documentation.

## Remote kubectl Access

To access the kind cluster from your local machine after setting up kubectl with the remote kubeconfig:

```bash
# On remote kind host: Export kubeconfig
kind get kubeconfig --name erechnung > kubeconfig-erechnung.yaml

# Copy to local machine
scp user@remote-host:kubeconfig-erechnung.yaml ~/.kube/config-erechnung

# On local machine: Use the config
export KUBECONFIG=~/.kube/config-erechnung
kubectl get pods -n erechnung

# Or merge into default config
KUBECONFIG=~/.kube/config:~/.kube/config-erechnung kubectl config view --flatten > ~/.kube/config.new
mv ~/.kube/config.new ~/.kube/config
kubectl config use-context kind-erechnung
```

**Note:** The API server address in the kubeconfig must be accessible from your local machine (may require SSH tunnel or direct network access).

## Local HTTPS Docker Registry

For Production-like deployments (kind multi-node cluster), all images are served from a local HTTPS Docker Registry to ensure fast, reproducible deployments without external dependencies.

### Registry Setup

```bash
# 1. Start HTTPS Registry on host (192.168.178.80:5000)
docker run -d \
  --name registry \
  --restart=always \
  -p 5000:5000 \
  -v /home/rolf/workspace/erechnung/infra/api-gateway/certs:/certs \
  -e REGISTRY_HTTP_ADDR=0.0.0.0:5000 \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/localhost.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/localhost.key \
  registry:2

# 2. Configure containerd on all kind nodes to trust self-signed cert
ssh rolf@192.168.178.80
for node in erechnung-control-plane erechnung-worker erechnung-worker2; do
  docker exec $node mkdir -p /etc/containerd/certs.d/192.168.178.80:5000
  docker exec $node bash -c 'cat > /etc/containerd/certs.d/192.168.178.80:5000/hosts.toml <<EOF
server = "https://192.168.178.80:5000"

[host."https://192.168.178.80:5000"]
  capabilities = ["pull", "resolve"]
  skip_verify = true
EOF'
done
```

### Images in Registry

**Application Images:**

- `192.168.178.80:5000/erechnung-web:latest`
- `192.168.178.80:5000/erechnung-celery:latest`
- `192.168.178.80:5000/erechnung-init:latest`
- `192.168.178.80:5000/erechnung-frontend:latest`

**Infrastructure Images:**

- `192.168.178.80:5000/postgres:17`
- `192.168.178.80:5000/redis:7-alpine`
- `192.168.178.80:5000/busybox:1.35`
- `192.168.178.80:5000/nginx:alpine`

**Calico CNI:**

- `192.168.178.80:5000/calico/node`
- `192.168.178.80:5000/calico/cni`
- `192.168.178.80:5000/calico/kube-controllers`

### Image Updates

When updating application code or dependencies:

```bash
# 1. Rebuild application images
docker-compose build --no-cache web celery init
docker build -f frontend/Dockerfile.prod -t 192.168.178.80:5000/erechnung-frontend:latest frontend/

# 2. Tag for registry
docker tag erechnung-web:latest 192.168.178.80:5000/erechnung-web:latest
docker tag erechnung-celery:latest 192.168.178.80:5000/erechnung-celery:latest
docker tag erechnung-init:latest 192.168.178.80:5000/erechnung-init:latest

# 3. Push to registry
docker push 192.168.178.80:5000/erechnung-web:latest
docker push 192.168.178.80:5000/erechnung-celery:latest
docker push 192.168.178.80:5000/erechnung-init:latest
docker push 192.168.178.80:5000/erechnung-frontend:latest

# 4. Redeploy in Kubernetes
KUBECONFIG=~/.kube/config-erechnung kubectl rollout restart deployment/django-web -n erechnung
KUBECONFIG=~/.kube/config-erechnung kubectl rollout restart deployment/celery-worker -n erechnung
KUBECONFIG=~/.kube/config-erechnung kubectl rollout restart deployment/frontend -n erechnung
```

### Updating External Images

When PostgreSQL, Redis, or other external images need updates:

```bash
# Pull latest version
docker pull postgres:17
docker pull redis:7-alpine

# Tag and push to local registry
docker tag postgres:17 192.168.178.80:5000/postgres:17
docker tag redis:7-alpine 192.168.178.80:5000/redis:7-alpine

docker push 192.168.178.80:5000/postgres:17
docker push 192.168.178.80:5000/redis:7-alpine

# Update deployment (if version changed in manifests)
KUBECONFIG=~/.kube/config-erechnung kubectl apply -f k8s/kind/k8s-erechnung-local.yaml
```

### Registry Verification

```bash
# List all images in registry
curl -k https://192.168.178.80:5000/v2/_catalog | jq .

# Check specific image tags
curl -k https://192.168.178.80:5000/v2/erechnung-web/tags/list | jq .
```

**Benefits:**

- ⚡ Fast deployment: Postgres starts in <20s (previously >12 minutes)
- 🔒 No external dependencies during deployment
- 📦 Complete reproducibility of all components
- 🌐 Works offline after initial image pull

## Configuration

- **Namespace**: `erechnung`
- **External Domain**: `api.erechnung.com`
- **API Gateway**: Load balanced with 2 replicas
- **Django Backend**: Auto-scaled with 3 replicas (internal only)

## Resource Requirements

- API Gateway: 64Mi-128Mi memory, 50m-100m CPU per pod
- Django Backend: 256Mi-512Mi memory, 100m-500m CPU per pod

## Notes

- Files are split for better maintainability and pre-commit compliance
- Previously was a single multi-document YAML file
- Rate limiting configured at ingress level (100 req/min)
