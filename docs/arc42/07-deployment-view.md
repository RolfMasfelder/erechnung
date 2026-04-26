# 7. Deployment View

## 7.1 Deployment Overview

The eRechnung system supports two deployment architectures to accommodate different organizational needs and scales:

### Option 1: Small/Private Deployment (Docker Compose)
- **Target Audience**: Small businesses, development teams, proof-of-concept
- **Scale**: Up to 100 concurrent users, <10,000 invoices/month
- **Complexity**: Simplified setup and maintenance
- **Infrastructure**: Single server or small cluster

### Option 2: Professional/Enterprise Deployment (Kubernetes)
- **Target Audience**: Medium to large enterprises, high-availability requirements
- **Scale**: 1000+ concurrent users, unlimited invoices
- **Complexity**: Full enterprise features with advanced monitoring
- **Infrastructure**: Multi-node cluster with redundancy

## 7.2 Small/Private Deployment (Docker Compose)

### 7.2.1 Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Docker Compose Deployment                            │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                              Host Server                                   │ │
│  │                                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │ │
│  │  │   nginx-proxy   │  │   django-app    │  │   postgresql    │             │ │
│  │  │                 │  │                 │  │                 │             │ │
│  │  │ Port: 80/443    │  │ Port: 8000      │  │ Port: 5432      │             │ │
│  │  │ SSL Termination │  │ Application     │  │ Database        │             │ │
│  │  │ Load Balancing  │  │ PDF Generation  │  │ Data Storage    │             │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘             │ │
│  │           │                     │                     │                    │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │ │
│  │  │     redis       │  │   backup-svc    │  │   monitoring    │             │ │
│  │  │                 │  │                 │  │                 │             │ │
│  │  │ Port: 6379      │  │ Cron: daily     │  │ Prometheus      │             │ │
│  │  │ Session Cache   │  │ DB Backup       │  │ Grafana         │             │ │
│  │  │ Task Queue      │  │ File Archive    │  │ Alerting        │             │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘             │ │
│  │                                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                        Shared Volumes                                  │ │ │
│  │  │                                                                         │ │ │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │ │
│  │  │  │ postgres-   │ │ app-data    │ │ backup-     │ │ ssl-certs   │       │ │ │
│  │  │  │ data        │ │ (uploads/   │ │ storage     │ │ (PKI/LE)    │       │ │ │
│  │  │  │ (encrypted) │ │ generated)  │ │ (encrypted) │ │             │       │ │ │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2.2 Container Specifications

| Container | Image | Resources | Purpose |
|-----------|-------|-----------|---------|
| nginx-proxy | nginx:alpine | 0.5 CPU, 512MB RAM | Reverse proxy, SSL termination |
| django-app | python:3.11-slim | 1 CPU, 1GB RAM | Main application server |
| postgresql | postgres:15-alpine | 1 CPU, 2GB RAM | Primary database |
| redis | redis:7-alpine | 0.5 CPU, 256MB RAM | Cache and session store |
| backup-svc | alpine/duplicity | 0.25 CPU, 256MB RAM | Automated backups |
| monitoring | prom/prometheus + grafana | 0.5 CPU, 512MB RAM | System monitoring |

### 7.2.3 Security Configuration (Docker Compose)

**PKI Setup for Small Deployment:**
```yaml
# Certificate management via Let's Encrypt or self-signed
Certificate Authority: Let's Encrypt (production) / Self-signed (development)
Certificate Storage: Docker volume with proper permissions
Automatic Renewal: Certbot container or manual process
mTLS: Optional for development, recommended for production
```

**Network Security:**
- Docker networks with custom bridge for service isolation
- Firewall rules allowing only necessary ports (80, 443)
- Regular security updates via automated scripts
- Basic intrusion detection with fail2ban

## 7.3 Professional/Enterprise Deployment (Kubernetes)

### 7.3.1 Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Kubernetes Cluster Deployment                        │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                              Control Plane                                 │ │
│  │                                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │ │
│  │  │   API Server    │  │     etcd        │  │  Controller     │             │ │
│  │  │                 │  │                 │  │   Manager       │             │ │
│  │  │ HA: 3 replicas  │  │ HA: 3 replicas  │  │ HA: 3 replicas  │             │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘             │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                        │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                              Worker Nodes                                  │ │
│  │                                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                          Namespace: erechnung                          │ │ │
│  │  │                                                                         │ │ │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │ │
│  │  │  │   ingress   │ │ django-app  │ │ postgresql  │ │    redis    │       │ │ │
│  │  │  │             │ │             │ │             │ │             │       │ │ │
│  │  │  │ nginx-      │ │ HPA: 2-10   │ │ HA: 3 nodes │ │ HA: 3 nodes │       │ │ │
│  │  │  │ ingress     │ │ replicas    │ │ Streaming   │ │ Sentinel    │       │ │ │
│  │  │  │ controller  │ │ Rolling     │ │ Replication │ │ Clustering  │       │ │ │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                        Namespace: monitoring                           │ │ │
│  │  │                                                                         │ │ │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │ │
│  │  │  │ prometheus  │ │   grafana   │ │ alertmanager│ │   jaeger    │       │ │ │
│  │  │  │             │ │             │ │             │ │             │       │ │ │
│  │  │  │ HA: 3 nodes │ │ HA: 2 nodes │ │ HA: 3 nodes │ │ Distributed │       │ │ │
│  │  │  │ Federation  │ │ Dashboards  │ │ Routing     │ │ Tracing     │       │ │ │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                         Namespace: security                            │ │ │
│  │  │                                                                         │ │ │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │ │
│  │  │  │cert-manager │ │ vault       │ │ falco       │ │ istio-      │       │ │ │
│  │  │  │             │ │             │ │             │ │ system      │       │ │ │
│  │  │  │ PKI Auto    │ │ Secrets     │ │ Runtime     │ │ Service     │       │ │ │
│  │  │  │ Issuance    │ │ Management  │ │ Security    │ │ Mesh mTLS   │       │ │ │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.3.2 Kubernetes Resource Specifications

**Application Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: django-app
  namespace: erechnung
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  template:
    spec:
      containers:
      - name: django
        image: erechnung/app:latest
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2
            memory: 2Gi
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
```

**Horizontal Pod Autoscaler:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: django-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: django-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 7.3.3 Security Configuration (Kubernetes)

**PKI Setup for Kubernetes:**
```yaml
# cert-manager configuration for automated certificate management
Certificate Authority Options:
  1. Let's Encrypt with DNS-01 challenge
  2. Internal PKI with intermediate CA
  3. Integration with external Enterprise CA
  4. HSM-backed certificate authority

Certificate Types:
  - TLS Certificates: Ingress endpoints
  - Service Certificates: Inter-service communication
  - Client Certificates: API authentication
  - Code Signing: Container image verification
```

**Service Mesh Security (Istio):**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: erechnung
spec:
  mtls:
    mode: STRICT

---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: app-access
  namespace: erechnung
spec:
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/erechnung/sa/django-app"]
    to:
    - operation:
        methods: ["GET", "POST"]
```

## 7.4 Database Configuration

### 7.4.1 PostgreSQL High Availability

**Docker Compose (Simple):**
```yaml
# Single instance with backup
postgresql:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: erechnung
    POSTGRES_USER: app_user
    POSTGRES_PASSWORD_FILE: /run/secrets/db_password
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./backup:/backup
  command: |
    postgres
    -c ssl=on
    -c ssl_cert_file=/etc/ssl/certs/server.crt
    -c ssl_key_file=/etc/ssl/private/server.key
```

**Kubernetes (High Availability):**
```yaml
# PostgreSQL Operator with streaming replication
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster
spec:
  instances: 3
  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      effective_cache_size: "1GB"
      ssl: "on"
      ssl_cert_file: "/etc/ssl/certs/server.crt"
      ssl_key_file: "/etc/ssl/private/server.key"
  storage:
    size: 100Gi
    storageClass: fast-ssd
  monitoring:
    enabled: true
```

### 7.4.2 Backup and Recovery

**Docker Compose Backup Strategy:**
```bash
#!/bin/bash
# Automated backup script
BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Database backup
docker exec postgres-container pg_dump -U app_user erechnung | gzip > $BACKUP_DIR/database.sql.gz

# File backup
tar czf $BACKUP_DIR/files.tar.gz /app/media /app/static

# Encryption and upload
gpg --encrypt --recipient backup@company.com $BACKUP_DIR/*.gz
aws s3 sync $BACKUP_DIR s3://erechnung-backups/
```

**Kubernetes Backup Strategy:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres-cluster-rw postgresql://app_user:password@postgres-cluster-rw:5432/erechnung | \
              gzip | \
              gpg --encrypt --recipient backup@company.com > /backup/backup-$(date +%Y%m%d-%H%M%S).sql.gz.gpg
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
```

## 7.5 Migration Strategy

### 7.5.1 Blue-Green Deployment Process

**Kubernetes Blue-Green Deployment:**
```yaml
# Blue environment (current production)
apiVersion: v1
kind: Service
metadata:
  name: django-app
  labels:
    version: blue
spec:
  selector:
    app: django-app
    version: blue

---
# Green environment (new version)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: django-app-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: django-app
      version: green
  template:
    metadata:
      labels:
        app: django-app
        version: green
    spec:
      containers:
      - name: django
        image: erechnung/app:v2.0.0
```

**Migration Steps:**
1. Deploy green environment with new version
2. Run database migrations on green environment
3. Perform smoke tests on green environment
4. Switch traffic from blue to green (service selector update)
5. Monitor for issues, rollback if necessary
6. Decommission blue environment after 24h

### 7.5.2 Database Migration

**Safe Migration Process:**
```python
# Django migration with zero-downtime
class Migration(migrations.Migration):
    atomic = False  # Allow for large data migrations

    operations = [
        # Add new column as nullable first
        migrations.AddField(
            model_name='invoice',
            name='new_field',
            field=models.CharField(max_length=100, null=True),
        ),
        # Populate data in batches
        migrations.RunPython(
            migrate_data_in_batches,
            reverse_code=migrations.RunPython.noop,
        ),
        # Remove null constraint after data migration
        migrations.AlterField(
            model_name='invoice',
            name='new_field',
            field=models.CharField(max_length=100, null=False),
        ),
    ]
```

This deployment architecture provides flexibility for organizations to choose the appropriate deployment strategy based on their scale, security requirements, and operational capabilities. The Docker Compose option offers simplicity for smaller deployments, while the Kubernetes option provides enterprise-grade scalability and high availability features.

## 7.6 Future Enhancements

### 7.6.1 Planned Kubernetes Features

**To Be Elaborated:**
1. **Service Mesh Integration (Istio/Linkerd)**
   - Mutual TLS between all services
   - Advanced traffic management (canary deployments, A/B testing)
   - Fine-grained observability and tracing
   - Circuit breaking and fault injection

2. **GitOps Deployment (ArgoCD/Flux)**
   - Declarative infrastructure as code
   - Automated sync from Git repositories
   - Rollback capabilities
   - Multi-cluster management

3. **Advanced Auto-Scaling**
   - KEDA (Kubernetes Event-Driven Autoscaling)
   - Custom metrics based on business KPIs
   - Predictive scaling based on historical patterns
   - Cost optimization with spot instances

4. **Multi-Region Active-Active**
   - Geographic distribution for low latency
   - Cross-region database replication
   - Global load balancing
   - Disaster recovery with automatic failover

5. **Advanced Security Features**
   - OPA (Open Policy Agent) for policy enforcement
   - Falco for runtime security monitoring
   - Image scanning in CI/CD pipeline
   - Compliance-as-Code automation

6. **Observability Stack Enhancement**
   - Distributed tracing with Jaeger/Tempo
   - Log aggregation with Loki
   - Custom dashboards for business metrics
   - AI-powered anomaly detection

### 7.6.2 Helm Chart Development

**Planned Helm Chart Features:**
- Parameterized deployment for different environments
- Support for different ZUGFeRD profiles
- Integration with external databases and storage
- Custom resource definitions (CRDs) for invoice processing
- Backup and restore automation
- Multi-tenancy support

**Chart Structure (To Be Developed):**
```
erechnung-helm/
├── Chart.yaml
├── values.yaml
├── values-production.yaml
├── values-development.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── hpa.yaml
│   ├── networkpolicy.yaml
│   └── servicemonitor.yaml
└── charts/
    ├── postgresql/
    └── redis/
```

### 7.6.3 Kubernetes Operator Development

**Planned Custom Operator:**
- Custom Resource Definition (CRD) for Invoice objects
- Automated invoice lifecycle management
- Self-service provisioning of tenant environments
- Automated backup and restore operations
- Compliance monitoring and reporting

**Example CRD (To Be Developed):**
```yaml
apiVersion: erechnung.io/v1alpha1
kind: InvoiceProcessor
metadata:
  name: my-invoice-processor
spec:
  zugferdProfile: COMFORT
  replicas: 3
  storage:
    size: 100Gi
    class: fast-ssd
  backup:
    enabled: true
    schedule: "0 2 * * *"
    retention: 30d
```

---

## 7.7 Implemented Kubernetes Deployment (Production-Ready, February 2026) ✨

### 7.7.1 Real-World Implementation Status

As of February 2026, the eRechnung system has a **production-ready Kubernetes deployment** with the following architecture:

**Cluster Configuration:**
- **Platform:** kind v1.35.0 (Kubernetes in Docker)
- **Nodes:** Multi-node cluster (1 Control-Plane + 2 Workers)
- **Host:** Remote deployment on 192.168.178.80 (SSH-based management)
- **API Server:** https://192.168.178.80:6443 (Remote kubeconfig access)

**Infrastructure Components:**
- **CNI Provider:** Calico v3.27.0 (Network Policies enabled)
- **LoadBalancer:** MetalLB v0.14.9 (Layer 2 mode, IP pool: 172.18.255.200-250)
- **Ingress Controller:** nginx v1.14.2 (External IP: 172.18.255.200)
- **Image Registry:** Local HTTPS Docker Registry (192.168.178.80:5000)
- **TLS:** Self-signed certificates (development), Ingress with HTTPS

**Application Services (10 pods):**
```yaml
Namespace: erechnung
├── frontend-xxx (2 replicas)         # Vue.js Production Build, nginx:alpine
├── django-web-xxx (2 replicas)       # REST API, erechnung-web:latest
├── api-gateway-xxx (2 replicas)      # nginx Reverse Proxy, Rate Limiting
├── celery-worker-xxx (1 replica)     # Background Tasks
├── postgres-xxx (1 pod, PVC 10Gi)    # PostgreSQL 17 Database
├── redis-xxx (1 pod, PVC 1Gi)        # Redis 7 Cache/Queue
└── django-init-xxx (Job, Completed)  # Migrations + Test Data
```

**Network Policies (12 policies):**
- Zero-Trust architecture with default-deny baseline
- DNS access for all pods (kube-dns)
- Ingress → Frontend/API-Gateway
- API-Gateway → Django-Web
- Django + Celery → PostgreSQL + Redis
- Egress for external HTTPS (ZUGFeRD XML download)

**Deployment Performance:**
- **Image Pull Time:** PostgreSQL <20s (from local registry, was >12 min from Docker Hub)
- **Total Deployment:** ~7 minutes (including django-init Job)
- **15x faster** than external registry deployments

### 7.7.2 Container Images Management

**Local HTTPS Registry (192.168.178.80:5000):**

All images pulled from local registry (no external dependencies):

**Application Images (4):**
- `192.168.178.80:5000/erechnung-web:latest` - Django Backend
- `192.168.178.80:5000/erechnung-celery:latest` - Celery Worker
- `192.168.178.80:5000/erechnung-init:latest` - Migration Job
- `192.168.178.80:5000/erechnung-frontend:latest` - Vue.js Production

**Infrastructure Images (4):**
- `192.168.178.80:5000/postgres:17` - PostgreSQL Database
- `192.168.178.80:5000/redis:7-alpine` - Redis Cache/Queue
- `192.168.178.80:5000/nginx:alpine` - API Gateway
- `192.168.178.80:5000/busybox:1.35` - Init Containers

**CNI Images (3):**
- `192.168.178.80:5000/calico/node` - Calico Node Agent
- `192.168.178.80:5000/calico/cni` - Calico CNI Plugin
- `192.168.178.80:5000/calico/kube-controllers` - Calico Controllers

**containerd Registry Configuration:**
All 3 kind nodes configured with `/etc/containerd/certs.d/192.168.178.80:5000/hosts.toml` for automatic image pulls from local registry.

### 7.7.3 Security Implementation

**Network Segmentation:**
- Default-Deny-All Network Policy
- Least-Privilege access between pods
- Calico CNI enforces policies via iptables
- No pod-to-pod communication without explicit policy

**Pod Security Standards:**
```yaml
Namespace Labels (erechnung):
  pod-security.kubernetes.io/enforce: baseline    # Enforced
  pod-security.kubernetes.io/audit: restricted    # Logged
  pod-security.kubernetes.io/warn: restricted     # Warnings
```

**TLS/HTTPS:**
- Ingress Controller with TLS termination
- Self-signed certificates (development)
- Secret: erechnung-tls-cert
- HTTPS for all external access

**Secrets Management:**
- Kubernetes Secrets for sensitive data
- Database credentials: postgres-secret
- TLS certificates: erechnung-tls-cert
- Environment variables injection

### 7.7.4 Deployment Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      kind Kubernetes Cluster (192.168.178.80)                   │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                      MetalLB LoadBalancer (L2 Mode)                       │  │
│  │                      IP Pool: 172.18.255.200-250                          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                           │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │             nginx Ingress Controller (EXTERNAL-IP: 172.18.255.200)        │  │
│  │             Ports: 80/TCP (→308 Redirect), 443/TCP (HTTPS)                │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                          │                            │                         │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  Frontend (Vue.js)              │  │  API Gateway (nginx)                │  │
│  │  - 2 replicas                   │  │  - 2 replicas                       │  │
│  │  - nginx:alpine                 │  │  - Rate Limiting                    │  │
│  │  - Serves SPA                   │  │  - Security Headers                 │  │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘  │
│                                                       │                         │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                     Django-Web (REST API)                                 │  │
│  │                     - 2 replicas                                          │  │
│  │                     - Health endpoints: /health/, /health/detailed/       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                          │                            │                         │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  PostgreSQL 17                  │  │  Redis 7                            │  │
│  │  - 1 pod (StatefulSet pattern)  │  │  - 1 pod                            │  │
│  │  - PVC: 10Gi                    │  │  - PVC: 1Gi                         │  │
│  │  - Persistent storage           │  │  - Cache + Queue                    │  │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘  │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                     Celery Worker (Background Tasks)                      │  │
│  │                     - 1 replica                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                 Calico CNI (DaemonSet - 3 pods, 1 per node)               │  │
│  │                 - Network Policy enforcement via iptables                 │  │
│  │                 - Pod-to-pod traffic control                              │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                         ┌───────────────────────┐
                         │  Local HTTPS Registry │
                         │  192.168.178.80:5000  │
                         │  - All 11 images      │
                         │  - Offline capable    │
                         └───────────────────────┘
```

### 7.7.5 Key Implementation Details

**Health Checks:**
```yaml
readinessProbe:
  httpGet:
    path: /health/readiness/
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5

livenessProbe:
  httpGet:
    path: /health/
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

**InitContainer for Migrations:**
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: django-init
spec:
  template:
    spec:
      containers:
      - name: django-init
        image: 192.168.178.80:5000/erechnung-init:latest
        command: ["python", "project_root/manage.py", "migrate"]
      restartPolicy: OnFailure
```

**Network Policy Example (Zero-Trust):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: erechnung
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-gateway-to-django
spec:
  podSelector:
    matchLabels:
      app: django-web
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000
```

### 7.7.6 Deployment Workflow

**1. Cluster Setup (35 minutes, one-time):**
```bash
# Create multi-node cluster with containerd registry config
cd k8s/kind && ./restart-cluster-multinode.sh

# Install Calico CNI (with image pre-load workaround)
./fix-calico-remote.sh

# Install MetalLB LoadBalancer
kubectl apply -f metallb-native.yaml
kubectl apply -f metallb-config.yaml

# Install Ingress Controller
kubectl apply -f ingress-nginx-deploy.yaml

# Create TLS secret
./create-tls-secret.sh
```

**2. Application Deployment (7 minutes):**
```bash
# Deploy all application services
kubectl apply -f k8s-erechnung-local.yaml

# Images pulled automatically from local registry (containerd mirror config)
# django-init Job runs migrations + generates test data (53 seconds)
# All pods reach Ready state

# Verify deployment
kubectl get pods -n erechnung
# → All 10 services Running
```

**3. Network Policies (30 seconds):**
```bash
# Apply 12 Network Policies for Zero-Trust segmentation
kubectl apply -f network-policies.yaml

# Application remains accessible (no traffic disruption)
```

**4. Access Application:**
```bash
curl -k -H 'Host: api.erechnung.local' https://172.18.255.200/
# → Vue.js frontend served successfully
```

### 7.7.7 Production Readiness Status

**✅ Fully Implemented:**
- Multi-node Kubernetes cluster with kind
- Calico CNI for Network Policies
- MetalLB LoadBalancer for Service exposure
- nginx Ingress Controller with TLS
- Local HTTPS Docker Registry (offline capable)
- 12 Network Policies (Zero-Trust architecture)
- Pod Security Standards (baseline/restricted)
- Health endpoints for all services
- Persistent storage with PVCs
- Background task processing with Celery
- Database migrations with InitContainer

**⏳ Planned Future Enhancements:**
- Horizontal Pod Autoscaling (HPA)
- Monitoring with Prometheus + Grafana
- Service Mesh (Linkerd) for mTLS
- External Secrets Operator (Vault integration)
- GitOps with Flux or ArgoCD
- Production certificates (Let's Encrypt)

**📊 Deployment Metrics:**
- Deployment Time: 7 minutes (application stack)
- Image Pull Speed: 15x faster (local registry vs Docker Hub)
- E2E Test Pass Rate: 96% (74/77 tests passing)
- Backend Tests: 263 tests (all passing)
- Frontend Tests: 381 tests (all passing)

### 7.7.8 Related Documentation

- **ADR-010:** Kubernetes Orchestration (decision rationale)
- **ADR-020:** Local HTTPS Docker Registry (offline deployments)
- **ADR-021:** MetalLB LoadBalancer (bare-metal load balancing)
- **ADR-022:** Calico CNI Network Policies (Zero-Trust networking)
- **Security Architecture:** `docs/arc42/security-architecture.md` (Zero-Trust model)
- **Progress Protocol:** `docs/PROGRESS_PROTOCOL.md` (milestone summaries)

---
