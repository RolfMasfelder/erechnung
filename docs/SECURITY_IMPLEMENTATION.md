# Security Implementation Plan

**Erstellt:** 23. Januar 2026
**Aktualisiert:** 04. März 2026
**Status:** Phase 2 implementiert
**Ziel:** Absicherung beider Deployment-Varianten (Docker-Only & Kubernetes)

---

## 📊 Status-Überblick: Implementierungs-Fortschritt

### Gesamtstatus

| Phase | Beschreibung | Aufwand | Status | Fortschritt |
|-------|-------------|---------|--------|-------------|
| **Phase 0** | Basis-Security (vorhanden) | - | ✅ **Abgeschlossen** | 100% |
| **Phase 1** | HTTPS/TLS Grundabsicherung | 8.5h | ⚠️ **Weitgehend** | 80% |
| **Phase 2** | Service Mesh & mTLS | 10-15h | ✅ **Implementiert** | 100% |
| **Phase 3** | Advanced Security | 10-15h | ❌ **Offen** | 0% |
| **Phase 4** | Zero-Trust Reife | 5-10h | ❌ **Offen** | 0% |

**Gesamt-Aufwand:** 33.5 - 48.5 Stunden
**Aktueller Stand:** Phase 0 + Phase 2 abgeschlossen, Phase 1 zu 80%
**Nächster Meilenstein:** Phase 3 - Advanced Security

---

## ✅ Phase 0: Bereits implementiert (Basis-Security)

### Docker-Only

- ✅ JWT-basierte Authentifizierung mit Token-Ablauf
- ✅ Django Permission System (RBAC auf Application-Level)
- ✅ CSRF-Protection für Web-Interface
- ✅ API Rate Limiting (DRF Throttling + nginx)
- ✅ nginx API Gateway mit CORS-Handling
- ✅ Audit Logging (AuditLog Model)
- ✅ HTTPS-Infrastruktur vorhanden (api-gateway mit TLS)
- ✅ Selbst-signierte Zertifikate generierbar
- ✅ HTTP → HTTPS Redirect konfiguriert

### Kubernetes

- ✅ Kubernetes-Cluster läuft (kind auf 192.168.178.80)
- ✅ Pods sind healthy (8 Pods running)
- ✅ Ingress-Controller (nginx) installiert
- ✅ ConfigMap & Secrets vorhanden
- ✅ PVCs für Postgres & Redis
- ✅ Basic Health Checks

---

## ⚠️ Phase 1: HTTPS/TLS Grundabsicherung (40% implementiert)

**Aufwand:** 8.5 Stunden (6h verbleibend)
**Priorität:** 🔴 **KRITISCH** - Production Blocker
**Ziel:** Beide Deployments production-ready machen

### 1.1 Django HTTPS Security Settings ✅ **Erledigt** (1h)

**Problem:** Django hat keine HTTPS-Security-Settings konfiguriert.

**Was fehlt:**

```python
# project_root/invoice_project/settings.py
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True              # HTTP → HTTPS Redirect
    SESSION_COOKIE_SECURE = True            # Cookies nur über HTTPS
    CSRF_COOKIE_SECURE = True               # CSRF-Cookies nur über HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000          # HSTS: 1 Jahr
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True   # HSTS für Subdomains
    SECURE_HSTS_PRELOAD = True              # HSTS Preload-Liste

# Security Headers (immer aktiv)
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'same-origin'
```

**Dateien:**

- `project_root/invoice_project/settings.py`

**Acceptance Criteria:**

- [ ] Settings erweitert mit HTTPS-Konfiguration
- [ ] Production-Mode erkennt `DJANGO_ENV=production`
- [ ] Tests passen (keine HTTPS-Redirects in Development)

---

### 1.2 Docker-Only: Port-Exposure Fix ✅ **Erledigt** (0.5h)

**Problem:** PostgreSQL (5432) und Django (8000) sind nach außen exponiert - Sicherheitsrisiko!

**Was zu ändern:**

```yaml
# docker-compose.production.yml
db:
  # ports: []  # ENTFERNEN - nur intern verfügbar
  # AKTUELL: - "5432:5432"  # ⚠️ SICHERHEITSRISIKO

web:
  # ports: []  # ENTFERNEN - nur via api-gateway
  # AKTUELL: - "8000:8000"  # ⚠️ SICHERHEITSRISIKO
```

**Dateien:**

- `docker-compose.production.yml`

**Acceptance Criteria:**

- [ ] DB und Web haben keine exposed Ports
- [ ] Nur api-gateway (80/443) ist erreichbar
- [ ] Interne Services kommunizieren via Docker Network

---

### 1.3 nginx Security Headers erweitern ⚠️ **Teilweise** (1h)

**Status:** Basis vorhanden, erweiterte Headers fehlen

**Was fehlt:**

```nginx
# api-gateway/api-gateway-https.conf
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
add_header Referrer-Policy "same-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

**Dateien:**

- `api-gateway/api-gateway-https.conf`

**Acceptance Criteria:**

- [ ] Alle Security Headers gesetzt
- [ ] CSP ohne unsafe-eval (nur unsafe-inline für Vue.js)
- [ ] Header mit securityheaders.com A-Rating

---

### 1.4 Kubernetes: TLS Ingress ❌ **TODO** (2h)

**Problem:** Kubernetes Ingress hat keine TLS-Konfiguration - läuft nur HTTP.

**Was zu erstellen:**

**1. TLS-Secret erstellen:**

```bash
# k8s/kind/create-tls-secret.sh
kubectl create secret tls erechnung-tls-cert \
  --cert=../../api-gateway/certs/localhost.crt \
  --key=../../api-gateway/certs/localhost.key \
  -n erechnung
```

**2. Ingress erweitern:**

```yaml
# k8s/kind/ingress.yaml
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.erechnung.local
    - 192.168.178.80
    secretName: erechnung-tls-cert
  rules:
  - host: api.erechnung.local
    # ... (rest wie bisher)
```

**Dateien zu erstellen/ändern:**

- `k8s/kind/create-tls-secret.sh` (neu)
- `k8s/kind/ingress.yaml` (erweitern)
- `k8s/kind/README-TLS.md` (Dokumentation)

**Acceptance Criteria:**

- [ ] TLS-Secret in Kubernetes vorhanden
- [ ] Ingress mit TLS konfiguriert
- [ ] HTTPS funktioniert auf <https://192.168.178.80>
- [ ] HTTP → HTTPS Redirect aktiv

---

### 1.5 Kubernetes: Network Policies ❌ **TODO** (3h)

**Problem:** Keine Network Policies - alle Pods können frei kommunizieren.

**Was zu tun:**

**1. Calico installieren (kind hat keinen Network Policy Provider):**

```bash
# k8s/kind/setup-calico.sh
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml
```

**2. Network Policies erstellen:**

- Default Deny All (Ingress + Egress)
- Allow: api-gateway → django-web (Port 8000)
- Allow: django-web → postgres (Port 5432)
- Allow: django-web/celery → redis (Port 6379)
- Allow: Alle → DNS (Port 53)
- Allow: Alle → Ingress-Controller

**Dateien zu erstellen:**

- `k8s/kind/setup-calico.sh` (neu)
- `k8s/kind/network-policies.yaml` (neu)
- `k8s/kind/test-network-policies.sh` (Test-Script)

**Acceptance Criteria:**

- [ ] Calico installiert und healthy
- [ ] 6 Network Policies deployed
- [ ] Unerlaubte Verbindungen werden blockiert
- [ ] Erlaubte Verbindungen funktionieren

---

### 1.6 Kubernetes: Pod Security Standards ❌ **TODO** (2h)

**Problem:** Pods laufen als Root ohne Security-Einschränkungen.

**Was zu ändern:**

**1. Namespace mit Pod Security Labels:**

```yaml
# k8s/kind/k8s-erechnung-local.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: erechnung
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**2. SecurityContext in allen Deployments:**

```yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: django
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: false  # Django needs /tmp, /media
```

**Betroffene Deployments:**

- django-web
- api-gateway
- celery-worker
- frontend
- postgres (mit initdb als root, dann runAsUser)
- redis

**Dateien:**

- `k8s/kind/k8s-erechnung-local.yaml` (alle Deployments erweitern)
- `Dockerfile` (USER-Direktive prüfen/ergänzen)

**Acceptance Criteria:**

- [ ] Namespace mit Pod Security Labels
- [ ] Alle Deployments mit securityContext
- [ ] Pods starten erfolgreich als non-root
- [ ] Keine privileged Containers

---

### Phase 1 Zusammenfassung

| Task | Priorität | Aufwand | Status | Blocker? |
|------|-----------|---------|--------|----------|
| 1.1 Django HTTPS Settings | 🔴 Kritisch | 1h | ❌ TODO | ✅ Ja |
| 1.2 Docker Port-Exposure Fix | 🔴 Kritisch | 0.5h | ❌ TODO | ✅ Ja |
| 1.3 nginx Security Headers | 🟡 Hoch | 1h | ⚠️ Teilweise | ⚠️ Optional |
| 1.4 K8s TLS Ingress | 🔴 Kritisch | 2h | ❌ TODO | ✅ Ja |
| 1.5 K8s Network Policies | 🔴 Kritisch | 3h | ❌ TODO | ⚠️ Optional |
| 1.6 K8s Pod Security | 🔴 Kritisch | 2h | ❌ TODO | ⚠️ Optional |
| **GESAMT** | | **9.5h** | **40%** | |

**Nach Phase 1:**

- ✅ Docker-Only: Production-Ready (HTTPS, Ports geschlossen, Security Headers)
- ✅ Kubernetes: HTTPS funktioniert, Pod Security aktiv
- ⚠️ Kubernetes: Network Policies optional für MVP (aber empfohlen)

---

## ✅ Phase 2: Service Mesh & mTLS (100% implementiert)

**Aufwand:** 10-15 Stunden
**Priorität:** 🟡 **HOCH** (nur Kubernetes)
**Status:** Implementiert am 04.03.2026
**Ziel:** Automatische mTLS-Verschlüsselung, Audit Logging, Runtime Security, Secrets Management

### 2.1 Linkerd Service Mesh auf k3s ✅ **Erledigt** (3-4h)

**Implementiert:**

1. Linkerd CLI Installation + Control Plane Deployment
2. Automatische Sidecar-Injection via Namespace-Annotation
3. mTLS (TLS 1.3) für alle Service-to-Service-Kommunikation
4. Viz Dashboard für Traffic-Observability
5. Opt-out für Stateful Services (postgres, redis)

**Dateien:**

- `scripts/setup-linkerd-k3s.sh` — Installations-Script für k3s
- `scripts/verify-linkerd-mtls.sh` — mTLS-Verifikation
- `k8s/k3s/manifests/00-namespace.yaml` — Linkerd-Annotation
- `k8s/k3s/manifests/30-deploy-postgres.yaml` — Opt-out (stateful)
- `k8s/k3s/manifests/32-deploy-redis.yaml` — Opt-out (stateful)

**Meshed Services:** django-web, celery-worker, api-gateway, frontend
**Not Meshed:** postgres, redis (Network Policies schützen diese)

---

### 2.2 Kubernetes API Audit Logging ✅ **Erledigt** (2-3h)

**Implementiert:**

- Audit Policy für k3s API Server (Secrets, RBAC, Exec, Workloads)
- Konfiguration über k3s config.yaml (nicht kubeadm)
- Log Rotation (30 Tage, 100MB max, 10 Backups)
- Noise Reduction (health checks, events, leases excluded)

**Überwachte Events:**

| Kategorie | Level | Beschreibung |
|-----------|-------|-------------|
| Secrets | Metadata | Alle Secret-Zugriffe in erechnung |
| RBAC | RequestResponse | Create/Update/Delete auf Roles |
| Pod Exec | Request | kubectl exec/attach/portforward |
| Workloads | Request | Deployment/StatefulSet Änderungen |
| Services | Metadata | Service/Ingress/NetworkPolicy |

**Dateien:**

- `k8s/k3s/audit-policy.yaml` — Kubernetes Audit Policy
- `scripts/setup-k3s-audit-logging.sh` — Setup & Konfiguration

---

### 2.3 Falco Runtime Security Monitoring ✅ **Erledigt** (3-4h)

**Implementiert:**

- Falco via Helm auf k3s (modern_ebpf Driver)
- Erechnung-spezifische Custom Rules
- Falcosidekick + WebUI für Alert-Visualisierung
- Integration mit containerd (k3s)

**Custom Falco Rules:**

| Regel | Priorität | Beschreibung |
|-------|-----------|-------------|
| Shell in Container | WARNING | Erkennt unerwartete Shells |
| Sensitive File Access | WARNING | Zugriff auf Secrets/Keys/Certs |
| Unexpected Outbound | NOTICE | Nicht-erlaubte Netzwerkverbindungen |
| DB Access Anomaly | WARNING | Nicht-Django Zugriff auf PostgreSQL |
| Privilege Escalation | ERROR | setuid/setgid/su/sudo Versuche |
| Crypto Mining | CRITICAL | Bekannte Miner-Prozesse |

**Dateien:**

- `scripts/setup-falco-k3s.sh` — Falco Installation + Rules

---

### 2.4 Secure Password/Key Management ✅ **Erledigt** (2-3h)

**Implementiert:**

- Kryptografisch sichere Secret-Generierung (`/dev/urandom`)
- `.env.example` Template (ohne echte Secrets)
- `generate-secrets.sh` für Docker Compose + optional K8s Secrets
- `rotate-k8s-secrets.sh` für Kubernetes Secret Rotation
- Backup vor Rotation, Rollback-Möglichkeit
- File Permissions (600) für .env-Dateien

**Dateien:**

- `scripts/generate-secrets.sh` — Sichere Secret-Generierung
- `scripts/rotate-k8s-secrets.sh` — K8s Secret Rotation
- `.env.example` — Template-Datei ohne Secrets

**Empfehlung für Production:** External Secrets Operator (Phase 3)

---

## ❌ Phase 3: Advanced Security (0% implementiert)

**Aufwand:** 10-15 Stunden
**Priorität:** 🟢 **MITTEL**
**Status:** Nicht gestartet

### 3.1 External Secrets Management ❌ **TODO** (4-6h)

**Docker-Only:**

- `.env` Files außerhalb Git
- Optional: Vault als Standalone-Container

**Kubernetes:**

- External Secrets Operator installieren
- SecretStore konfigurieren
- ExternalSecret Ressourcen erstellen

**Dateien:**

- `k8s/kind/external-secrets-install.sh`
- `k8s/kind/secret-store.yaml`
- `k8s/kind/external-secrets.yaml`
- `.env.example` (Template ohne Secrets)

---

### 3.2 WAF (ModSecurity) ❌ **TODO** (2-3h)

**Docker-Only:**

- ModSecurity nginx Module kompilieren (optional)

**Kubernetes:**

- Ingress-Controller mit ModSecurity konfigurieren
- OWASP Core Rule Set aktivieren

**Dateien:**

- `k8s/kind/ingress-modsecurity.yaml`
- `api-gateway/modsecurity.conf` (Docker)

---

### 3.3 Image Scanning ❌ **TODO** (2-3h)

**CI/CD:**

- Trivy in GitHub Actions
- Scan bei jedem Build
- Vulnerabilities als Artefakte

**Dateien:**

- `.github/workflows/security.yml` (erweitern)

---

### 3.4 Let's Encrypt Setup ❌ **TODO** (3h)

**Docker-Only:**

- certbot Container hinzufügen
- Automatische Renewal

**Kubernetes:**

- cert-manager installieren
- ClusterIssuer für Let's Encrypt
- Certificate Ressourcen

**Dateien:**

- `docker-compose.certbot.yml`
- `k8s/production/cert-manager.yaml`
- `k8s/production/cluster-issuer.yaml`

---

## ❌ Phase 4: Zero-Trust Reife (0% implementiert)

**Aufwand:** 5-10 Stunden
**Priorität:** 🟢 **NIEDRIG** (Enterprise-Feature)
**Status:** Nicht gestartet

### 4.1 RBAC Implementation ❌ **TODO** (2-3h)

**Kubernetes:**

- ServiceAccounts für jeden Service
- Roles & RoleBindings
- ClusterRoles wo nötig

**Dateien:**

- `k8s/kind/rbac.yaml`

---

### 4.2 Resource Quotas & Limits ❌ **TODO** (2h)

**Kubernetes:**

- ResourceQuota pro Namespace
- LimitRanges für Pods

**Dateien:**

- `k8s/kind/resource-quotas.yaml`

---

### 4.3 Advanced Rate Limiting ❌ **TODO** (2h)

**Kubernetes:**

- Redis-basiertes Rate Limiting
- Ingress-Level + Application-Level

**Dateien:**

- `k8s/kind/ingress.yaml` (Annotations)
- `project_root/invoice_project/settings.py` (DRF Config)

---

### 4.4 Monitoring & Alerting ❌ **TODO** (5-8h)

**Stack:**

- Prometheus (Metriken)
- Grafana (Dashboards)
- Alertmanager (Notifications)

**Dateien:**

- `k8s/monitoring/prometheus.yaml`
- `k8s/monitoring/grafana.yaml`
- `k8s/monitoring/alert-rules.yaml`

---

## 🎯 Empfohlene Implementierungs-Reihenfolge

### Sprint 1: Docker-Only Production-Ready (2.5h)

**Ziel:** Docker Compose sicher machen

1. Django HTTPS Settings (1h)
2. Docker Port-Exposure Fix (0.5h)
3. nginx Security Headers (1h)

**Deliverable:** Docker-Only Deployment ist produktiv nutzbar

---

### Sprint 2: Kubernetes HTTPS (4h)

**Ziel:** K8s mit TLS absichern

1. K8s TLS Ingress (2h)
2. K8s Pod Security Standards (2h)

**Deliverable:** Kubernetes mit HTTPS erreichbar

---

### Sprint 3: Kubernetes Network Isolation (3h)

**Ziel:** Micro-Segmentation

1. Calico Installation (1h)
2. Network Policies (2h)

**Deliverable:** Phase 1 abgeschlossen

---

### Sprint 4-6: Zero-Trust (Optional, 20-30h)

**Ziel:** Enterprise-Grade Security

1. Service Mesh (Linkerd)
2. External Secrets
3. WAF + Monitoring

**Deliverable:** Zero-Trust Level 4

---

## 📋 Testing & Validation Checkliste

### Nach Phase 1 (MUST-HAVE)

**Docker-Only:**

- [ ] HTTPS funktioniert ohne Browser-Warnung (selbst-signierte Certs importiert)
- [ ] Port 5432 (Postgres) nicht erreichbar von außen
- [ ] Port 8000 (Django) nicht erreichbar von außen
- [ ] Security Headers mit A-Rating (securityheaders.com)
- [ ] JWT-Login funktioniert über HTTPS
- [ ] API-Requests über api-gateway

**Kubernetes:**

- [ ] HTTPS auf <https://192.168.178.80> funktioniert
- [ ] HTTP → HTTPS Redirect aktiv
- [ ] Pods starten als non-root (UID 1000)
- [ ] Network Policies blockieren unerlaubte Verbindungen
- [ ] Erlaubte Verbindungen funktionieren (django→postgres, django→redis)
- [ ] Frontend kann API erreichen

---

### Nach Phase 2 (Service Mesh)

**Kubernetes:**

- [x] Linkerd Control Plane installiert und healthy
- [x] Sidecar-Injection für erechnung Namespace aktiv
- [x] mTLS aktiv zwischen meshed Services (TLS 1.3)
- [x] Viz Dashboard verfügbar (linkerd viz dashboard)
- [x] Audit Policy deployed (Secrets, RBAC, Exec, Workloads)
- [x] Falco Runtime Security mit eRechnung-spezifischen Rules
- [x] Secure Secret Generation + Rotation Scripts
- [x] .env.example Template (ohne echte Secrets)

---

### Nach Phase 3 (Advanced)

**Beide Deployments:**

- [ ] Secrets nicht mehr in Git/YAML
- [ ] ModSecurity blockiert XSS/SQL-Injection
- [ ] Image Scan findet keine CRITICAL Vulnerabilities
- [ ] Let's Encrypt Zertifikate funktionieren

---

### Nach Phase 4 (Zero-Trust)

**Kubernetes:**

- [ ] RBAC verhindert unauthorized Zugriffe
- [ ] Resource Quotas werden eingehalten
- [ ] Prometheus sammelt Metriken
- [ ] Alerts funktionieren

---

## 🚨 Production Blocker (vor Go-Live beheben!)

### Kritisch (Phase 1)

1. ⚠️ **Django HTTPS Settings fehlen** → Session-Cookies unsicher
2. ⚠️ **PostgreSQL Port 5432 exposed** → Direkter DB-Zugriff möglich
3. ⚠️ **Kubernetes ohne TLS** → Datenverkehr unverschlüsselt
4. ⚠️ **Pods als Root** → Container Escape möglich

### Hoch (Phase 2)

5. ⚠️ **Service-to-Service unverschlüsselt** → Lateral Movement möglich
6. ⚠️ **Secrets in Git** → Credentials leakbar

### Medium (Phase 3)

7. ⚠️ **Keine WAF** → XSS/SQL-Injection nicht blockiert
8. ⚠️ **Self-signed Certs in Production** → Man-in-the-Middle möglich

---

## 📚 Noch zu klärende Fragen

1. **Timeline:**
   - Wann soll Phase 1 abgeschlossen sein?
   - Ist Zero-Trust (Phase 4) überhaupt Ziel?

2. **Zertifikate:**
   - Welche Domain für Production?
   - Let's Encrypt oder kommerzielle CA?

3. **Service Mesh:**
   - Ist 150MB RAM overhead pro Node für kind akzeptabel?
   - Linkerd oder kein Service Mesh?

4. **Monitoring:**
   - Self-hosted oder Cloud-Provider?
   - Welche Metriken sind critical?

5. **Compliance:**
   - DSGVO only oder ISO 27001/SOC2?
   - Audit-Trail Retention Policy?

---

## Deployment-Varianten

### 1. Docker-Only (Small Business)

- **Zielgruppe:** Kleine Unternehmen, 1-5 Anwender
- **Infrastruktur:** Docker Compose auf Single-Host
- **Basis:** `docker-compose.yml`, `docker-compose.production.yml`
- **Zugriff:** <http://localhost> oder lokales Netzwerk
- **Skalierung:** Vertikal (mehr CPU/RAM auf einem Server)

### 2. Kubernetes (Enterprise)

- **Zielgruppe:** Mittelständler, >10 Anwender, Multi-Tenant
- **Infrastruktur:** kind (Development), K3s/K8s (Production)
- **Basis:** `k8s/kind/k8s-erechnung-local.yaml`
- **Zugriff:** Ingress-Controller mit Load-Balancing
- **Skalierung:** Horizontal (mehr Pods/Nodes)

**Besonderheiten kind (Development):**

- Läuft in Docker-Containern (Container-in-Container)
- Port-Mapping via extraPortMappings in kind-cluster-config.yaml
- NodePort-Services für externen Zugriff
- Kein echter Load-Balancer (MetalLB als Ersatz möglich)
- Lokale Image-Registry oder `kind load docker-image`
- Shared Host-Dateisystem via extraMounts möglich

---

## Phase 1: HTTPS/TLS Grundabsicherung (MUST-HAVE)

**Aufwand:** 6-8 Stunden
**Priorität:** 🔴 Kritisch

### 1.1 Docker-Only: HTTPS via nginx (2-3h)

**Bereits vorhanden:**

- ✅ `docker-compose.frontend.yml` mit api-gateway (nginx + HTTPS)
- ✅ `api-gateway/api-gateway-https.conf` mit TLS-Config
- ✅ `api-gateway/generate-certs.sh` für selbst-signierte Zertifikate

**Implementierungsschritte:**

```bash
# 1. Zertifikate generieren (Development: selbst-signiert)
cd api-gateway && ./generate-certs.sh

# 2. Production Compose-File erweitern
# docker-compose.production.yml: api-gateway Service hinzufügen

# 3. Frontend .env.production anpassen
VITE_API_BASE_URL=https://localhost/api

# 4. Starten mit HTTPS
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

**Für Production (echte Domain):**

- Let's Encrypt via certbot
- Automatische Zertifikatserneuerung
- DNS-Validierung oder HTTP-01 Challenge

**Konfigurationsdateien:**

- `api-gateway/api-gateway-https.conf` - nginx TLS-Config
- `docker-compose.production.yml` - Production Setup mit Secrets
- `.env.production` - Environment mit HTTPS-URLs

### 1.2 Kubernetes: TLS Ingress (2-3h)

**KIND-spezifische Überlegungen:**

- Ingress-Controller (nginx) ist bereits installiert
- Selbst-signierte Certs für lokales Development OK
- Port 443 muss in kind-cluster-config.yaml gemappt sein
- TLS-Secret muss vor Ingress-Deployment erstellt werden

**Implementierungsschritte:**

```bash
# 1. Zertifikate als Kubernetes Secret
kubectl create secret tls erechnung-tls-cert \
  --cert=api-gateway/certs/cert.pem \
  --key=api-gateway/certs/key.pem \
  -n erechnung

# 2. Ingress mit TLS erweitern (k8s/kind/ingress.yaml)
# 3. Frontend neu bauen mit VITE_API_BASE_URL=https://192.168.178.80/api
# 4. Image in kind laden und deployen
```

**Ingress TLS-Konfiguration:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: erechnung-ingress
  namespace: erechnung
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.erechnung.local
    - 192.168.178.80
    secretName: erechnung-tls-cert
  rules:
  - host: api.erechnung.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway-service
            port:
              number: 80
```

**Für Production Kubernetes:**

- cert-manager installieren
- ClusterIssuer für Let's Encrypt
- Automatische Zertifikatsverwaltung

**Konfigurationsdateien:**

- `k8s/kind/ingress.yaml` - Ingress mit TLS
- `k8s/kind/tls-secret.yaml` - Secret für Zertifikate (als Beispiel, nicht committen!)
- `k8s/production/cert-manager.yaml` - cert-manager Setup für Production

### 1.3 Network Policies (2h)

**Ziel:** Micro-Segmentation - Nur erlaubte Service-zu-Service Kommunikation

**Docker-Only:**

- ⚠️ Docker Networks bieten Isolation, aber keine Firewall-Regeln
- Workaround: iptables-Regeln auf Host-Ebene (nicht empfohlen für Small Business)
- → Network Policies erst ab Kubernetes sinnvoll

**Kubernetes (inkl. kind):**

KIND-Hinweis: Standardmäßig kein Network Policy Provider! Muss installiert werden:

```bash
# Calico für kind installieren
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml
```

**Network Policy Beispiele:**

```yaml
# 1. Default Deny All
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
# 2. api-gateway → django-web erlauben
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-gateway-to-django
  namespace: erechnung
spec:
  podSelector:
    matchLabels:
      app: django-web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000

---
# 3. django-web → postgres erlauben
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-django-to-postgres
  namespace: erechnung
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: django-web
    - podSelector:
        matchLabels:
          app: celery-worker
    ports:
    - protocol: TCP
      port: 5432

---
# 4. django-web + celery → redis erlauben
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-django-celery-to-redis
  namespace: erechnung
spec:
  podSelector:
    matchLabels:
      app: redis
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: django-web
    - podSelector:
        matchLabels:
          app: celery-worker
    ports:
    - protocol: TCP
      port: 6379

---
# 5. Erlaubt DNS-Lookups (kube-dns)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: erechnung
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
```

**Konfigurationsdateien:**

- `k8s/kind/network-policies.yaml` - Alle Network Policies
- `k8s/kind/setup-calico.sh` - Script für Calico-Installation in kind

### 1.4 Pod Security Standards (1-2h)

**Ziel:** Pods mit minimalen Privilegien laufen lassen

**Docker-Only:**

- Docker Compose unterstützt `user:` Direktive
- Nicht-Root User in Dockerfiles definieren

**Kubernetes:**

**Pod Security Standards Levels:**

- **Privileged:** Keine Restriktionen (für System-Pods)
- **Baseline:** Minimale Restriktionen (Default empfohlen)
- **Restricted:** Stark eingeschränkt (Production empfohlen)

**Namespace-weite Enforcement:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: erechnung
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Pod-Level Security Context (Beispiel django-web):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: django-web
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: django
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: false  # Django needs write to /tmp, /app/media
        volumeMounts:
        - name: media
          mountPath: /app/media
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: media
        persistentVolumeClaim:
          claimName: media-pvc
      - name: tmp
        emptyDir: {}
```

**KIND-Hinweis:**

- kind unterstützt Pod Security Standards out-of-the-box (seit K8s 1.23)
- Keine zusätzliche Installation nötig

**Konfigurationsdateien:**

- `k8s/kind/k8s-erechnung-local.yaml` - Deployments mit securityContext erweitern
- `Dockerfile` - USER-Direktive für Nicht-Root User

---

## Phase 2: Service Mesh & mTLS (SHOULD-HAVE)

**Aufwand:** 10-15 Stunden
**Priorität:** 🟡 Hoch (nur Kubernetes)

### 2.1 Service Mesh Entscheidung

**Optionen für kind:**

1. **Linkerd** (empfohlen für kind)
   - Leichtgewichtig (~150MB RAM pro Node)
   - Einfache Installation
   - Automatisches mTLS
   - ✅ Funktioniert gut mit kind

2. **Istio**
   - Mächtiger, aber ressourcenintensiv (~1GB RAM)
   - Mehr Features (Traffic Management, Observability)
   - ⚠️ Kann kind überlasten

3. **Cilium Service Mesh**
   - eBPF-basiert, sehr performant
   - Erfordert neueren Kernel
   - ⚠️ kind braucht Host-Kernel-Support

**Empfehlung für kind Development:** Linkerd

### 2.2 Linkerd Installation (kind) (3-4h)

```bash
# 1. Linkerd CLI installieren
curl -fsL https://run.linkerd.io/install | sh

# 2. Pre-Flight Check
linkerd check --pre

# 3. Linkerd Control Plane installieren
linkerd install --crds | kubectl apply -f -
linkerd install | kubectl apply -f -

# 4. Verify Installation
linkerd check

# 5. Namespace für Auto-Injection markieren
kubectl annotate namespace erechnung linkerd.io/inject=enabled

# 6. Pods neu starten für Injection
kubectl rollout restart deployment -n erechnung
```

**Automatisches mTLS:**

- Linkerd injiziert automatisch Proxy-Sidecar in jeden Pod
- mTLS zwischen allen Pods im Mesh
- Keine Code-Änderungen nötig!

**Konfigurationsdateien:**

- `k8s/kind/linkerd-install.sh` - Installations-Script
- `k8s/kind/k8s-erechnung-local.yaml` - Namespace-Annotation hinzufügen

### 2.3 Audit Logging erweitern (3-5h)

**Docker-Only:**

- Django AuditLog Model (bereits vorhanden)
- nginx Access-Logs in Volume mounten
- Optional: Filebeat für Log-Aggregation

**Kubernetes:**

**Django Application-Level:**

- ✅ AuditLog Model bereits vorhanden
- Erweitern um Request-ID Tracking
- Structured Logging (JSON-Format)

**Kubernetes Audit Logs:**

KIND-Hinweis: Audit-Policy muss in kind-cluster-config.yaml konfiguriert werden:

```yaml
# k8s/kind/kind-cluster-config.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: ClusterConfiguration
    apiServer:
      extraArgs:
        audit-policy-file: /etc/kubernetes/audit-policy.yaml
        audit-log-path: /var/log/kubernetes/audit.log
        audit-log-maxage: "30"
        audit-log-maxbackup: "10"
        audit-log-maxsize: "100"
      extraVolumes:
      - name: audit-policy
        hostPath: /path/to/audit-policy.yaml
        mountPath: /etc/kubernetes/audit-policy.yaml
        readOnly: true
```

**Audit Policy (Beispiel):**

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
# Log Secrets access
- level: Metadata
  resources:
  - group: ""
    resources: ["secrets"]
# Log all RBAC changes
- level: RequestResponse
  verbs: ["create", "update", "patch", "delete"]
  resources:
  - group: "rbac.authorization.k8s.io"
# Log Pod exec
- level: Request
  verbs: ["create"]
  resources:
  - group: ""
    resources: ["pods/exec"]
```

**Konfigurationsdateien:**

- `k8s/kind/audit-policy.yaml` - Kubernetes Audit Policy
- `k8s/kind/kind-cluster-config.yaml` - Audit-Logging aktivieren
- `project_root/invoice_project/settings.py` - Structured Logging Config

---

## Phase 3: Advanced Security (NICE-TO-HAVE)

**Aufwand:** 10-15 Stunden
**Priorität:** 🟢 Mittel

### 3.1 External Secrets Management (4-6h)

**Problem:** Secrets in Git (base64 encoded) sind unsicher!

**Docker-Only:**

- Docker Secrets (Swarm-Mode) - nicht für Compose
- ✅ Empfohlen: `.env` Files außerhalb Git + Secrets-Manager
- Vault als Standalone-Container

**Kubernetes:**

**Optionen:**

1. **External Secrets Operator (empfohlen)**
2. **Sealed Secrets**
3. **HashiCorp Vault CSI Driver**

**External Secrets Operator (kind):**

```bash
# 1. Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace

# 2. SecretStore definieren (Beispiel: File-Backend für Development)
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: file-backend
  namespace: erechnung
spec:
  provider:
    # Für kind: Fake Secret Store aus ConfigMap
    kubernetes:
      server:
        url: kubernetes.default
      auth:
        serviceAccount:
          name: external-secrets
      remoteNamespace: erechnung-secrets-source
EOF

# 3. ExternalSecret definieren
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: django-secrets
  namespace: erechnung
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: file-backend
    kind: SecretStore
  target:
    name: erechnung-secrets
    creationPolicy: Owner
  data:
  - secretKey: DJANGO_SECRET_KEY
    remoteRef:
      key: django-secret-key
  - secretKey: DB_PASSWORD
    remoteRef:
      key: postgres-password
EOF
```

**Für Production:**

- AWS Secrets Manager
- Azure Key Vault
- GCP Secret Manager
- HashiCorp Vault

**Konfigurationsdateien:**

- `k8s/kind/external-secrets-install.sh`
- `k8s/kind/secret-store.yaml`
- `k8s/kind/external-secrets.yaml`

### 3.2 WAF (Web Application Firewall) (2-3h)

**Docker-Only:**

- ModSecurity nginx Module
- Erweiterte nginx.conf mit Security Headers

**Kubernetes:**

**ModSecurity für nginx-ingress:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ingress-nginx-controller
  namespace: ingress-nginx
data:
  enable-modsecurity: "true"
  enable-owasp-modsecurity-crs: "true"
  modsecurity-snippet: |
    SecRuleEngine On
    SecRequestBodyAccess On
    SecRule REQUEST_HEADERS:Content-Type "text/xml" \
         "id:'200000',phase:1,t:none,t:lowercase,pass,nolog,ctl:requestBodyProcessor=XML"
```

**Security Headers (nginx ConfigMap):**

```yaml
data:
  # Security Headers
  server-snippet: |
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

**Konfigurationsdateien:**

- `k8s/kind/ingress-modsecurity.yaml` - ModSecurity Config
- `api-gateway/nginx.conf` - Security Headers für Docker

### 3.3 Request Tracing (4-6h)

**Ziel:** Distributed Tracing über alle Services

**Docker-Only:**

- Jaeger All-in-One Container
- Django-Instrumentation mit OpenTelemetry

**Kubernetes:**

**Jaeger Installation (kind):**

```bash
# Jaeger Operator installieren
kubectl create namespace observability
kubectl create -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.51.0/jaeger-operator.yaml -n observability

# Jaeger Instance deployen
kubectl apply -f - <<EOF
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: erechnung-jaeger
  namespace: erechnung
spec:
  strategy: allInOne
  ingress:
    enabled: true
  allInOne:
    image: jaegertracing/all-in-one:latest
    options:
      log-level: debug
  storage:
    type: memory
EOF
```

**Django OpenTelemetry Integration:**

```python
# settings.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.django import DjangoInstrumentor

# Tracer konfigurieren
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent.erechnung.svc.cluster.local",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Django instrumentieren
DjangoInstrumentor().instrument()
```

**Konfigurationsdateien:**

- `k8s/kind/jaeger.yaml` - Jaeger Deployment
- `project_root/invoice_project/tracing.py` - OpenTelemetry Setup
- `requirements.txt` - OpenTelemetry Dependencies hinzufügen

### 3.4 Image Scanning & Signing (2-3h)

**Ziel:** Keine vulnerablen Images deployen

**Docker-Only:**

- Trivy CLI für lokales Scanning
- Pre-commit Hook für Image-Scan

**Kubernetes:**

KIND-Hinweis: Image Admission Controller ist kompliziert in kind. Alternative:

1. Scan lokal vor `kind load`
2. CI/CD Pipeline mit Image-Scan
3. Admission Webhook (Kyverno/OPA Gatekeeper)

**Trivy Scanning:**

```bash
# Lokales Image scannen
trivy image --severity HIGH,CRITICAL erechnung-django:local
trivy image --severity HIGH,CRITICAL erechnung-frontend:local

# In CI/CD (GitHub Actions):
- name: Scan Django Image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'erechnung-django:${{ github.sha }}'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'
```

**Cosign für Image-Signierung:**

```bash
# Cosign installieren
curl -O -L "https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64"
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
sudo chmod +x /usr/local/bin/cosign

# Keypair generieren
cosign generate-key-pair

# Image signieren
cosign sign --key cosign.key erechnung-django:v1.0.0

# Signatur verifizieren
cosign verify --key cosign.pub erechnung-django:v1.0.0
```

**Konfigurationsdateien:**

- `.github/workflows/security-scan.yml` - CI/CD Image-Scanning
- `scripts/scan-images.sh` - Lokales Scan-Script
- `k8s/kind/admission-policy.yaml` - Kyverno/OPA Policy (optional)

---

## Phase 4: Production Hardening (PRODUCTION ONLY)

**Aufwand:** Variable (5-20h je nach Anforderungen)
**Priorität:** 🔴 Kritisch für Production

### 4.1 RBAC (Role-Based Access Control)

**Docker-Only:**

- Keine Kubernetes RBAC
- ✅ Django User Permissions & Groups (bereits vorhanden)

**Kubernetes:**

**Service Accounts mit minimalen Rechten:**

```yaml
# Celery braucht keine API-Zugriffe
apiVersion: v1
kind: ServiceAccount
metadata:
  name: celery-worker-sa
  namespace: erechnung
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
spec:
  template:
    spec:
      serviceAccountName: celery-worker-sa
      automountServiceAccountToken: false  # Kein Token mounten
```

**Role für Django-Migrations:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: django-migration-role
  namespace: erechnung
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: django-migration-binding
  namespace: erechnung
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: django-migration-role
subjects:
- kind: ServiceAccount
  name: django-init-sa
  namespace: erechnung
```

**Konfigurationsdateien:**

- `k8s/kind/rbac.yaml` - Service Accounts, Roles, RoleBindings

### 4.2 Resource Limits & Quotas

**Ziel:** DoS-Schutz durch Resource-Limitierung

**Docker-Only:**

```yaml
# docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

**Kubernetes:**

**ResourceQuota für Namespace:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: erechnung-quota
  namespace: erechnung
spec:
  hard:
    requests.cpu: "8"
    requests.memory: 16Gi
    limits.cpu: "16"
    limits.memory: 32Gi
    persistentvolumeclaims: "10"
```

**LimitRange (Defaults für Pods):**

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: erechnung-limits
  namespace: erechnung
spec:
  limits:
  - max:
      cpu: "2"
      memory: "4Gi"
    min:
      cpu: "100m"
      memory: "128Mi"
    default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "200m"
      memory: "256Mi"
    type: Container
```

**Konfigurationsdateien:**

- `k8s/kind/resource-quotas.yaml`
- `docker-compose.production.yml` - Resource Limits hinzufügen

### 4.3 Rate Limiting (erweitert)

**Docker-Only:**

- nginx rate limiting in api-gateway.conf

**Kubernetes:**

**Ingress-Level Rate Limiting:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: erechnung-ingress
  annotations:
    nginx.ingress.kubernetes.io/limit-rps: "100"
    nginx.ingress.kubernetes.io/limit-connections: "50"
    nginx.ingress.kubernetes.io/limit-rpm: "1000"
    # Per-IP Rate Limit
    nginx.ingress.kubernetes.io/limit-whitelist: "10.0.0.0/8"
```

**Django Throttling (bereits in DRF):**

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'invoice_create': '50/hour',
        'invoice_list': '200/hour',
    }
}
```

**Konfigurationsdateien:**

- `k8s/kind/ingress.yaml` - Rate Limiting Annotations
- `project_root/invoice_project/settings.py` - DRF Throttling

---

## Testing & Validation

### Security Testing Checkliste

**Docker-Only:**

- [ ] HTTPS funktioniert (selbst-signierte Certs OK)
- [ ] nginx Security Headers gesetzt
- [ ] Container laufen als non-root User
- [ ] Resource Limits definiert
- [ ] DRF Throttling aktiv
- [ ] Audit Logs werden geschrieben

**Kubernetes:**

- [ ] TLS Ingress funktioniert
- [ ] Network Policies aktiv (Pod-zu-Pod Kommunikation blockiert wo gewünscht)
- [ ] Pod Security Standards enforced (Namespace-Label prüfen)
- [ ] Service Mesh mTLS (linkerd viz dashboard)
- [ ] Secrets via External Secrets oder verschlüsselt
- [ ] ModSecurity WAF aktiv
- [ ] Request Tracing funktioniert (Jaeger UI)
- [ ] Image Scanning in CI/CD
- [ ] RBAC Policies definiert
- [ ] Resource Quotas & Limits gesetzt

### Penetration Testing

**Tools:**

- OWASP ZAP für Web-Security
- kubectl auth can-i für RBAC-Tests
- kube-bench für K8s CIS Benchmark
- trivy für Image-Scanning

**Test-Szenarien:**

1. XSS/CSRF-Tests gegen Frontend
2. SQL-Injection gegen API
3. JWT-Token-Manipulation
4. Pod Escape-Versuche
5. Network Policy Bypass-Versuche
6. Rate Limit Umgehung
7. Privilege Escalation (RBAC)

---

## Maintenance & Monitoring

### Security Updates

**Docker-Only:**

- Monatliche Base-Image Updates
- `docker-compose pull && docker-compose up -d`

**Kubernetes:**

- Automated Image Updates (Renovate Bot/Dependabot)
- Rolling Updates ohne Downtime
- Rollback-Strategie

### Monitoring

**Metriken:**

- Request Rate & Latency
- Failed Login Attempts
- 4xx/5xx Error Rates
- Certificate Expiry
- Pod Restarts
- Network Policy Drops

**Alerting:**

- Certificate läuft in <30 Tagen ab
- Ungewöhnlich hohe Failed Logins
- Pod Crash-Loop
- Resource Quota überschritten

---

## Zusammenfassung: Implementierungs-Roadmap

### Minimal (Development/Small Business)

**Docker-Only, 6-8 Stunden:**

1. HTTPS via api-gateway (2-3h)
2. Security Headers (1h)
3. Container als non-root (1h)
4. DRF Throttling (1h)
5. Resource Limits (1h)

### Standard (Production Small Business)

**Docker-Only, 10-15 Stunden:**

- Minimal +
- Let's Encrypt Zertifikate (2-3h)
- External Secrets (env files) (2h)
- Monitoring (Prometheus/Grafana) (3-4h)
- Backup-Strategie (2h)

### Enterprise (Kubernetes)

**Kubernetes mit kind, 30-40 Stunden:**

- Phase 1: HTTPS + Network Policies + Pod Security (6-8h)
- Phase 2: Service Mesh + Audit Logging (10-15h)
- Phase 3: WAF + Tracing + Image Scanning (10-15h)
- Phase 4: RBAC + Quotas + Rate Limiting (5-7h)

### Zero-Trust (Full Security)

**Kubernetes Production, 50-70 Stunden:**

- Enterprise +
- OAuth2/OIDC Integration (6-8h)
- cert-manager + Let's Encrypt (3-4h)
- External Secrets Operator + Vault (6-8h)
- Service Mesh (Linkerd/Istio) (8-12h)
- Comprehensive Monitoring & Alerting (8-10h)
- Security Audits & Pen-Testing (8-12h)

---

## Offene Fragen / Zu klärende Details

1. **Zertifikate:**
   - Self-signed für Development OK?
   - Für Production: Welche Domain(s)?
   - Let's Encrypt oder kommerzielle CA?

2. **Service Mesh:**
   - ✅ **ENTSCHIEDEN:** Für kind Development: **Kein Service Mesh** | Für Production K8s: **Linkerd**
   - Begründung siehe unten (Abschnitt "Service Mesh Entscheidung: Detailanalyse")

3. **Secrets Management:**
   - Für Docker-Only: env files außerhalb Git?
   - Für K8s: Vault selbst hosten oder Cloud-Provider nutzen?

4. **Monitoring:**
   - Self-hosted (Prometheus/Grafana) oder Cloud (Datadog/New Relic)?
   - Welche Metriken sind critical?

5. **Audit Logs:**
   - Retention Policy? (30/90/365 Tage?)
   - Log-Aggregation nötig? (ELK/Loki)

6. **Zero-Trust Scope:**
   - Welche Phase ist Ziel? (Minimal/Standard/Enterprise/Zero-Trust)
   - Timeline? (Wochen/Monate)

7. **Compliance:**
   - Gibt es spezifische Anforderungen? (DSGVO, ISO 27001, SOC2)
   - Audit-Trail für Finanzdaten?

---

## Service Mesh Entscheidung: Detailanalyse

**Aktualisiert:** 31. Januar 2026
**Status:** ✅ Entscheidung getroffen

### Was ist ein Service Mesh?

Ein Service Mesh ist eine dedizierte Infrastruktur-Schicht, die **automatisch** zwischen allen Services kommuniziert. Es injiziert einen "Sidecar-Proxy" in jeden Pod, der den gesamten Netzwerk-Traffic abfängt.

**Hauptfunktionen:**

- **mTLS** (mutual TLS): Automatische Verschlüsselung zwischen allen Services
- **Traffic Management**: Load Balancing, Circuit Breaking, Retries
- **Observability**: Request Tracing, Metriken, Service-Map
- **Security**: Policies, Zero-Trust auf Netzwerk-Ebene

---

### Option 1: Linkerd

#### ✅ Vorteile

- **Sehr leichtgewichtig**: ~150 MB RAM pro Node, minimaler CPU-Overhead
- **Einfach**: Installation in 5 Minuten, automatisches mTLS ohne Konfiguration
- **Performance**: Rust-basierter Proxy (schneller als Envoy)
- **Kind-freundlich**: Funktioniert out-of-the-box mit kind
- **Zero-Config mTLS**: Alle Pod-zu-Pod Verbindungen automatisch verschlüsselt

#### ❌ Nachteile

- Weniger Features als Istio (kein fortgeschrittenes Traffic Routing)
- Kleinere Community
- Keine WebAssembly-Plugins

#### Für dein Projekt

```bash
# Installation (3 Befehle)
linkerd install --crds | kubectl apply -f -
linkerd install | kubectl apply -f -
kubectl annotate namespace erechnung linkerd.io/inject=enabled

# → Alle Pods bekommen automatisch mTLS
# → Kein Code-Change nötig!
```

#### Ressourcen-Impact

**kind mit 1 Control-Plane + 2 Worker-Nodes:**

- Linkerd Control Plane (auf Control-Plane-Node): ~150 MB RAM
- Pro Worker-Node: ~50 MB RAM (Linkerd-Proxy DaemonSet)
- Pro Pod: +30-50 MB RAM (Sidecar-Proxy)
- **Bei 8 App-Pods auf 2 Worker-Nodes:** ~650-750 MB total
  - Control Plane: 150 MB
  - Worker-Nodes: 2 × 50 MB = 100 MB
  - Sidecars: 8 × 40 MB (Durchschnitt) = 320 MB
  - **Total: ~570 MB** (akzeptabel für Multi-Node-Setup)

---

### Option 2: Istio

#### ✅ Vorteile

- **Feature-reich**: Advanced Traffic Management (A/B Testing, Canary Deployments)
- **Große Community**: Mehr Tutorials, Docs, Enterprise-Support
- **Extensible**: WebAssembly-Plugins, Custom Filters
- **Multi-Cluster**: Service Mesh über mehrere K8s-Cluster
- **Istio Gateway**: Ingress-Controller Ersatz

#### ❌ Nachteile

- **Sehr ressourcenhungrig**: ~1-2 GB RAM für Control Plane
- **Komplex**: Steile Lernkurve, viele CRDs
- **Kind-problematisch**: Kann kind-Cluster überlasten
- **Performance**: Envoy-Proxy langsamer als Linkerd

#### Für dein Projekt

```bash
# Installation (komplexer)
istioctl install --set profile=demo

# → Viele ConfigMaps, Services, Deployments
# → Erfordert Tuning für kind
```

#### Ressourcen-Impact

**kind mit 1 Control-Plane + 2 Worker-Nodes:**

- Istio Control Plane (istiod): ~1-2 GB RAM
- Pro Worker-Node: ~100 MB RAM (Istio DaemonSets)
- Pro Pod: +100-150 MB RAM (Envoy Sidecar)
- **Bei 8 App-Pods auf 2 Worker-Nodes:** ~3-4 GB total
  - Control Plane: 1.5 GB (Durchschnitt)
  - Worker-Nodes: 2 × 100 MB = 200 MB
  - Sidecars: 8 × 125 MB (Durchschnitt) = 1000 MB
  - **Total: ~2.7 GB** (⚠️ kann kind-Nodes überlasten!)

---

### Option 3: Kein Service Mesh

#### ✅ Vorteile

- **Einfach**: Keine zusätzliche Komplexität
- **Ressourcen**: Keine Overhead (wichtig für kind/Small Business)
- **Weniger zu warten**: Keine Service Mesh-Updates
- **Schneller**: Kein Proxy-Hop

#### ❌ Nachteile

- **Kein automatisches mTLS**: Pod-zu-Pod Traffic unverschlüsselt
- **Manuelles Monitoring**: Kein built-in Request Tracing
- **Mehr Arbeit**: Security/Observability auf Application-Level implementieren

#### Für dein Projekt

**Du hast bereits:**

- ✅ HTTPS am Ingress (nginx)
- ✅ JWT-Auth auf Application-Level
- ✅ Network Policies (wenn Calico installiert)
- ✅ DRF Throttling

**Was fehlt ohne Service Mesh:**

- ❌ Verschlüsselung zwischen django-web → postgres (aber in LAN!)
- ❌ Automatisches Request Tracing
- ❌ Service-to-Service Policies (nur Network Policies)

---

### Vergleichstabelle

| Kriterium | Linkerd | Istio | Kein Mesh |
|-----------|---------|-------|-----------|
| **Komplexität** | 🟢 Niedrig | 🔴 Hoch | 🟢 Keine |
| **RAM-Overhead (1 CP + 2 Worker)** | 🟢 ~570 MB | 🔴 ~2.7 GB | 🟢 0 MB |
| **RAM-Overhead (1 Node)** | 🟡 ~500 MB | 🔴 ~3 GB | 🟢 0 MB |
| **Setup-Zeit** | 🟢 1h | 🔴 4-6h | 🟢 0h |
| **mTLS** | 🟢 Auto | 🟢 Auto | 🔴 Manuell |
| **Tracing** | 🟢 Ja | 🟢 Ja | 🔴 Nein |
| **kind-Support** | 🟢 Perfekt | 🟡 Geht | 🟢 Perfekt |
| **Multi-Node Vorteil** | 🟢 Ja | 🟡 Ja | 🔴 Nein |
| **Wartung** | 🟢 Einfach | 🔴 Komplex | 🟢 Keine |
| **Use-Case** | Small-Mid | Enterprise | Development |

---

### Empfehlung für eRechnung-App

#### Für kind Development (1 CP + 2 Worker): **Kein Service Mesh**

**Begründung:**

- kind läuft in Containern mit limitiertem RAM (siehe Konfiguration unten)
- Multi-Node-Setup macht Linkerd attraktiver, aber:
  - Network Policies reichen für Isolation zwischen Pods
  - Django ↔ Postgres/Redis läuft im gleichen Namespace (vertrauenswürdiges LAN)
  - Kein Cross-Node-Traffic in kleinem Development-Setup
  - Ressourcen-Overhead von 570 MB ist für Development zu hoch
- **Alternative für mTLS in Development:**
  - Stunnel für einzelne kritische Verbindungen (leichtgewichtig)
  - Nur wenn Compliance-Tests erforderlich sind

**Mit 2 Worker-Nodes ändert sich:**

- ✅ Mehr Inter-Node-Traffic → Service Mesh würde mehr bringen
- ❌ Aber: Development-Workload verteilt sich selten auf mehrere Nodes
- ⚠️ kind-Nodes haben limitierte Ressourcen (Standard: Shared Host-RAM)

#### Für Production Kubernetes (3+ Nodes): **Linkerd**

**Begründung:**

- ✅ Leichtgewichtig genug für Small Business (5-10 User Setup)
- ✅ Automatisches mTLS erfüllt Compliance (DSGVO Artikel 32)
- ✅ Zero-Config: Namespace-Annotation reicht
- ✅ Observability (Linkerd Viz Dashboard)
- ✅ Production-Ready ohne komplexe Config
- ✅ **Multi-Node-Vorteil:** Cross-Node mTLS ohne Aufwand

**Setup-Aufwand:** 3-4 Stunden (Phase 2.2)

**Bei Production mit 3 Nodes (1 CP + 2 Worker):**

- Control Plane: 150 MB
- Worker-Nodes: 2 × 50 MB = 100 MB
- Sidecars: 8 × 40 MB = 320 MB
- **Total: ~570 MB** auf 3 Nodes verteilt = ~190 MB pro Node (✅ akzeptabel)

#### Für Enterprise (>50 User, >10 Nodes): **Istio**

**Nur wenn du brauchst:**

- Multi-Cluster Service Mesh
- Advanced Traffic Management (Canary Deployments)
- WebAssembly Custom Filters
- Service Mesh Federation

**Setup-Aufwand:** 8-12 Stunden + Tuning

---

### kind Memory-Limits Konfiguration

#### Standard-Verhalten

kind-Nodes sind Docker-Container und teilen sich **standardmäßig den gesamten Host-RAM** ohne harte Limits.

#### Docker Desktop (Mac/Windows)

```bash
# Docker Desktop Settings → Resources → Advanced
# Beispiel: 8 GB für Docker Desktop gesamt
# → Wird automatisch auf alle Container verteilt
```

#### Linux (Docker CLI)

Memory-Limits werden **beim Cluster-Start** gesetzt, nicht in `kind-cluster-config.yaml`:

```bash
# Option 1: Docker Run mit Memory-Limit (manuell, nicht empfohlen)
docker run --memory="4g" --cpus="2" ...

# Option 2: kind mit Docker Resource Limits (experimentell)
# Erfordert Docker API-Zugriff während Cluster-Erstellung

# Option 3: cgroups v2 Limits (systemd)
# /etc/systemd/system/docker.service.d/override.conf
[Service]
MemoryLimit=8G
```

#### kind-cluster-config.yaml (KEINE Memory-Limits!)

```yaml
# k8s/kind/kind-cluster-config.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  # ❌ KEIN memory: 4Gi → wird ignoriert!
  # kind nutzt Docker-Container-Limits

- role: worker
- role: worker

# ✅ STATTDESSEN: extraPortMappings, extraMounts, kubeadmConfigPatches
```

#### Praktische Empfehlung für kind Development

**Host mit 16 GB RAM:**

- Docker Desktop/Engine: 10 GB Limit
- kind mit 3 Nodes: ~3-4 GB RAM-Verbrauch (ohne Service Mesh)
- → 6 GB frei für Host-OS

**Host mit 8 GB RAM:**

- Docker Desktop/Engine: 6 GB Limit
- kind mit 3 Nodes: ~3-4 GB RAM-Verbrauch
- → 2 GB frei (knapp!)
- ⚠️ **Kein Service Mesh möglich!** (Linkerd würde +570 MB = 4.5 GB total)

#### Monitoring von kind-Node-Ressourcen

```bash
# 1. Docker Container Stats (Live)
docker stats

# 2. Kubernetes Node-Metriken
kubectl top nodes

# 3. Detaillierte Node-Info
kubectl describe node kind-control-plane
kubectl describe node kind-worker
kubectl describe node kind-worker2

# 4. Pod-Ressourcen pro Node
kubectl top pods --all-namespaces --sort-by=memory
```

#### Memory-Limit-Empfehlung pro Node-Typ

**Control-Plane-Node:**

- Minimum: 2 GB RAM
- Empfohlen: 4 GB RAM
- Benötigt: kube-apiserver, etcd, kube-scheduler, kube-controller-manager
- Mit Linkerd: +150 MB

**Worker-Node:**

- Minimum: 1.5 GB RAM (pro Worker)
- Empfohlen: 3 GB RAM (pro Worker)
- Benötigt: kubelet, kube-proxy, Container-Runtime
- Mit Linkerd: +50 MB (DaemonSet) + ~40 MB pro Pod

**Gesamt für kind mit 2 Workern (ohne Service Mesh):**

- Control-Plane: 2 GB
- Worker 1: 1.5 GB (4 Pods à ~300 MB)
- Worker 2: 1.5 GB (4 Pods à ~300 MB)
- **Total: ~5 GB RAM minimum**

**Mit Linkerd:**

- Control-Plane: 2.15 GB (+150 MB)
- Worker 1: 1.7 GB (+200 MB: 50 MB DaemonSet + 4×40 MB Sidecars)
- Worker 2: 1.7 GB (+200 MB)
- **Total: ~5.6 GB RAM** (⚠️ grenzwertig für 8 GB Host!)

---

### Fazit: Auswirkung von 2 Worker-Nodes

**Technische Auswirkung:**

- ✅ **Pro Linkerd:** Multi-Node-Setup profitiert mehr von Service Mesh (Cross-Node mTLS)
- ✅ **Pro Linkerd:** RAM-Overhead verteilt sich auf 3 Nodes → ~190 MB pro Node (akzeptabel)
- ❌ **Contra Linkerd:** kind Development-Workload nutzt selten echte Node-Verteilung
- ❌ **Contra Linkerd:** Absolute RAM-Kosten bleiben gleich (~570 MB zusätzlich)

**Empfehlung bleibt:**

- **kind Development (1 CP + 2 Worker):** ❌ **Kein Service Mesh**
  - Network Policies reichen aus
  - Ressourcen für App-Development besser nutzen
  - Phase 1 (Network Policies + Pod Security) umsetzen

- **Production Kubernetes (3+ Nodes, echte Hardware):** ✅ **Linkerd**
  - Multi-Node-Traffic rechtfertigt Service Mesh
  - mTLS für Compliance
  - Echter Load-Balancing-Vorteil

**Wenn du Linkerd in kind testen willst:**

- Mindestens 12 GB Host-RAM empfohlen
- Nur 1 Worker-Node für Tests (statt 2)
- Profile: `minimal` statt `default`
- Monitoring: `linkerd viz` optional lassen (spart ~200 MB)

---

## Referenzen

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/security-checklist/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
- [NSA Kubernetes Hardening Guide](https://media.defense.gov/2022/Aug/29/2003066362/-1/-1/0/CTR_KUBERNETES_HARDENING_GUIDANCE_1.2_20220829.PDF)
- [Linkerd Documentation](https://linkerd.io/2.14/overview/)
- [nginx Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
