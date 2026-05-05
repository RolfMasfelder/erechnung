# Security Policies

## Reporting Security Vulnerabilities

If you discover a security vulnerability in the eRechnung Django App, please report it by emailing **github@nector-it-gmbh.de**.

**Please do not report security vulnerabilities through public GitHub issues.**

## Security Measures

### Automated Security Scanning

- **Trivy**: Container and filesystem vulnerability scanning
- **Safety**: Python dependency vulnerability checking
- **Dependabot**: Automated dependency updates
- **CodeQL**: Code analysis for security issues

### Docker Security

- Multi-stage builds with minimal attack surface
- Non-root user execution
- Regular base image updates
- Security scanning on every build

### Application Security

- JWT authentication with RBAC
- CSRF protection for web interface
- Account lockout after failed login attempts
- Audit logging for all operations
- Rate limiting via API Gateway

### Infrastructure Security

- nginx-based API Gateway with security headers
- TLS termination at gateway level
- Network isolation between services
- Health checks and monitoring

## Security Updates

Security updates are prioritized and will be released as soon as possible. All security-related changes will be documented in the changelog with CVE references where applicable.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| 0.x.x   | :x:                |

## Security Configuration Checklist

### Production Deployment

- [x] Change default secret keys (`DJANGO_SECRET_KEY` via env, Pflicht seit 2025)
- [x] Enable HTTPS/TLS (api-gateway-https.conf + Let's Encrypt Option)
- [x] Configure firewall rules (K8s: NetworkPolicies, Docker: isolierte Networks)
- [x] Set up monitoring and alerting (Prometheus + Grafana + Loki in K8s)
- [x] Regular backup procedures (scripts/backup.sh + Disaster Recovery)
- [x] Access control and user management (JWT + RBAC + Account Lockout)
- [x] Security headers configuration (CSP, HSTS, X-Frame-Options via nginx)
- [ ] Database encryption at rest (LUKS Host-Level geplant)
- [x] Regular security updates (Dependabot + pip-audit CI Workflow)

## PDF/A-3 Generation (Ghostscript) Hardening

Ghostscript wird zur Konvertierung von Basis-PDFs in PDF/A-3 eingesetzt. Härtungsmaßnahmen (Issue #5):

### Risiken

- Historische CVEs bei Ghostscript (Sandbox Escapes, Memory Corruption)
- Ausführung externer PostScript/PDF Inhalte könnte theoretisch missbraucht werden (bei manipulierten Zwischenstufen)

### Umgesetzte Maßnahmen

| Maßnahme | Beschreibung | Status |
|----------|--------------|--------|
| `-dSAFER` Flag | Restriktiver Modus: verhindert Dateisystem-Zugriff außer explizit freigegebener Pfade | ✅ Umgesetzt |
| `--permit-file-read` Whitelist | Nur ICC-Profil und PDFA_def.ps sind lesbar | ✅ Umgesetzt |
| Prozess-Timeout (60s) | `subprocess.run(timeout=60)` verhindert hängende Prozesse | ✅ Umgesetzt |
| Feature Flag `ENABLE_ASYNC_PDF` | PDF-Generierung kann in Celery-Worker ausgelagert werden | ✅ Umgesetzt |
| Logging & Monitoring | Erfolg/Fehler + Dauer via Prometheus-Metriken | ✅ Umgesetzt |

### Offene Maßnahmen (Nice-to-Have)

| Maßnahme | Beschreibung | Status |
|----------|--------------|--------|
| Isolierung | Ausführung unter dediziertem unprivilegierten User | Offen |
| Seccomp/AppArmor | Evaluierung eines minimalen Syscall-Profils | Offen |

## Update: 2026-01-22 – Readiness Endpoint Made Public for CI/CD

- Changed `/health/readiness/` from JWT-protected to public (AllowAny) for Kubernetes readinessProbe and CI/CD compatibility
- Kubernetes readinessProbes cannot use authentication headers
- Endpoint returns minimal status information (migrations, database ready)
- Detailed health data remains protected at `/health/detailed/` (JWT required)

## Update: 2026-01-09 – Gateway Health Rate Limiting & CSRF Adjustment

- Added rate limiting for public health endpoints at the API Gateway (`/health`, `/health/`) using a dedicated `health_limit` zone to reduce probe abuse potential.
- Removed `@csrf_exempt` from the GET-only `health_check()` to reduce unnecessary CSRF surface.

---

## Zero-Trust Architecture Considerations

### Overview

Die eRechnung-App wird in zwei Deployment-Varianten betrieben:

1. **Docker-Only** (Small Business): 1-5 Anwender auf Single-Host
2. **Kubernetes** (Enterprise): >10 Anwender, Multi-Tenant-fähig

Eine vollständige Zero-Trust-Architektur erfordert unterschiedliche Maßnahmen je nach Deployment-Typ.

### Zero-Trust Prinzipien

**"Never trust, always verify"** - Kernprinzipien:

1. **Explicit Verification:** Jede Anfrage wird authentifiziert und autorisiert
2. **Least Privilege Access:** Minimale notwendige Berechtigungen
3. **Assume Breach:** Systeme sind so designed, dass ein Kompromiss isoliert bleibt

### Aktueller Stand (2026-03-08)

**Bereits implementiert:**

- ✅ JWT-basierte Authentifizierung mit Token-Ablauf-Validierung
- ✅ Django Permission System (RBAC auf Application-Level)
- ✅ CSRF-Protection für Web-Interface
- ✅ API Rate Limiting (DRF Throttling)
- ✅ nginx Security Headers (CSP, HSTS, X-Frame-Options, Referrer-Policy)
- ✅ Audit Logging (AuditLog Model)
- ✅ HTTPS/TLS (api-gateway-https.conf + letsencrypt.conf, Django HSTS/SSL Settings)
- ✅ Non-root Container (Dockerfile `USER app_user`, K8s `runAsNonRoot: true`)
- ✅ Network Segmentation (K8s: 5 NetworkPolicies für erechnung-Namespace)
- ✅ Pod Security Standards (securityContext auf allen K8s Deployments)
- ✅ Image Scanning (Trivy in CI/CD Pipeline)
- ✅ Resource Limits (K8s Deployments: requests/limits konfiguriert)
- ✅ Kubernetes Audit Logging (audit-policy.yaml für k3s)
- ✅ Monitoring & Alerting (Prometheus + Grafana + Loki + Promtail in K8s)
- ✅ Ghostscript Hardening (-dSAFER, permit-file-read Whitelist, Timeout)
- ✅ Resource Limits Docker Compose (deploy.resources auf allen Services)
- ✅ Structured Logging + Request-ID Middleware (JSON + ContextVar)
- ✅ Docker Secrets Support (get_secret() liest /run/secrets/ mit env-Fallback)

**Noch fehlend für Zero-Trust:**

- ❌ mTLS zwischen Services (Service Mesh — Linkerd evaluiert, nicht deployt)
- ✅ External Secret Management (ESO Phase 2: K8s-Backend, Vault vorbereitet)
- ✅ Image Signing (Cosign keyless via GitHub Actions OIDC)
- ✅ K8s TLS Ingress (cert-manager + self-signed CA für LAN)
- ❌ WAF/ModSecurity Rules

### Zero-Trust Implementierung nach Deployment-Typ

#### Docker-Only (Small Business)

**Aufwand verbleibend:** 4-6 Stunden
**Fokus:** Resource Limits, Structured Logging, Secrets

**Bereits erledigt (Phase 1):**

- ✅ HTTPS via api-gateway (Self-signed + Let's Encrypt config)
- ✅ Security Headers (CSP, HSTS, X-Frame-Options, Referrer-Policy)
- ✅ Container als non-root User (`USER app_user`)
- ✅ Automated Security Scanning (Trivy in CI)
- ✅ Resource Limits (`deploy.resources` in docker-compose.production.yml)
- ✅ Structured Logging + Request-ID Middleware (JSON, ContextVar)
- ✅ Docker Secrets Support (`get_secret()` + `/run/secrets/` Fallback)

**Offen (Phase 2):**

- WAF/ModSecurity Rules (2-3h, NICE-TO-HAVE)

**Einschränkungen Docker-Only:**

- Keine native Network Policies (nur Docker Networks)
- Kein Service-zu-Service mTLS ohne Service Mesh
- Vertikale Skalierung (Single-Host-Limitation)

#### Kubernetes (Enterprise)

**Aufwand verbleibend:** 10-15 Stunden
**Fokus:** Service Mesh, WAF

**Bereits erledigt:**

- ✅ Network Policies (5 Policies: api-gateway→django, ingress→api-gateway, etc.)
- ✅ Pod Security Standards (runAsNonRoot, allowPrivilegeEscalation: false, drop ALL)
- ✅ Resource Requests & Limits (alle Deployments)
- ✅ Kubernetes Audit Logging (audit-policy.yaml)
- ✅ Image Scanning (Trivy in CI/CD)
- ✅ Monitoring & Alerting (Prometheus + Grafana + Loki + Promtail + kube-state-metrics)

**Erledigt - Phase 1 (Sprint 2):**

- ✅ TLS Ingress mit cert-manager (self-signed CA für LAN)
- ✅ External Secrets Operator (Phase 2: K8s-Backend, Vault vorbereitet)
- ✅ Image Signing mit Cosign (keyless via GitHub Actions OIDC)

**Offen - Phase 2 (NICE-TO-HAVE, 10-15h):**

- Linkerd Service Mesh + mTLS (3-4h)
- Request Tracing mit Jaeger (4-6h)
- WAF (ModSecurity für Ingress) (2-3h)
- Service Account RBAC granularer machen (2-3h)

**Besonderheiten kind (Development):**

- Network Policy Provider (Calico) muss separat installiert werden
- TLS mit selbst-signierten Certs OK (mkcert für lokale CA empfohlen)
- Service Mesh (Linkerd) funktioniert, aber ressourcenintensiv
- Image-Transfer via `docker save | ssh | kind load`

### Zero-Trust Maturity Model

| Level | Beschreibung | Docker-Only | Kubernetes |
|-------|--------------|-------------|------------|
| **Level 0** | Keine Security-Maßnahmen | ❌ Nicht akzeptabel | ❌ Nicht akzeptabel |
| **Level 1** | Basic Authentication + HTTPS | ✅ Erreicht | ✅ Erreicht (HTTP intern) |
| **Level 2** | + Segmentation + Least Privilege | ✅ Erreicht (non-root, RBAC) | ✅ Erreicht (NetworkPolicies, PodSecurity) |
| **Level 3** | + mTLS + Audit Logging | ⚠️ Audit ✅, mTLS ❌ | ⚠️ Audit ✅, mTLS fehlt (Linkerd) |
| **Level 4** | + Secret Management + Scanning | ⚠️ Scanning ✅, Vault ❌ | ⚠️ Scanning ✅, Vault ❌ |
| **Level 5** | Full Zero-Trust (Assume Breach) | ⚠️ Eingeschränkt | ⚠️ Erreichbar mit Phase 1+2 |

**Empfehlungen:**

- **Docker-Only:** Ziel Level 2-3 (HTTPS, Secrets, Monitoring)
- **Kubernetes:** Ziel Level 4-5 (Service Mesh, Full Security Stack)

### Service-zu-Service Authentication

**Aktuell:**

- Services kommunizieren innerhalb Docker Network ohne Authentifizierung
- Nur externe Requests (via API Gateway) erfordern JWT

**Zero-Trust Ziel:**

**Docker-Only:**

- Schwierig ohne Service Mesh
- Workaround: Shared Secrets zwischen Services (nicht empfohlen)

**Kubernetes mit Service Mesh (Linkerd):**

- Automatisches mTLS zwischen allen Pods
- Jeder Service bekommt eigene Identität (X.509 Certificate)
- Zertifikat-Rotation automatisch (24h)
- Policy-basierte Service-zu-Service Autorisierung

```yaml
# Beispiel: Nur api-gateway darf django-web aufrufen
apiVersion: policy.linkerd.io/v1beta1
kind: Server
metadata:
  name: django-web-server
  namespace: erechnung
spec:
  podSelector:
    matchLabels:
      app: django-web
  port: 8000
  proxyProtocol: HTTP/1
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: django-web-policy
  namespace: erechnung
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: django-web-server
  requiredAuthenticationRefs:
  - name: api-gateway-auth
    kind: MeshTLSAuthentication
---
apiVersion: policy.linkerd.io/v1alpha1
kind: MeshTLSAuthentication
metadata:
  name: api-gateway-auth
  namespace: erechnung
spec:
  identities:
  - "api-gateway.erechnung.serviceaccount.identity.linkerd.cluster.local"
```

### Data Encryption

**At Rest:**

- ⚠️ PostgreSQL: Host-Level LUKS geplant, DB selbst unverschlüsselt
- ⚠️ Media Files (PDFs, XML) aktuell unverschlüsselt
- ❌ Redis Cache unverschlüsselt (ephemeral data, akzeptabel)

**In Transit:**

- ✅ HTTPS/TLS am API-Gateway (Self-signed + Let's Encrypt)
- ✅ Django HSTS + SECURE_SSL_REDIRECT in Production
- ✅ K8s TLS Ingress via cert-manager (self-signed CA für LAN)
- ❌ Service-zu-Service unverschlüsselt (ohne Service Mesh)

**Recommendations:**

- Docker-Only: HTTPS via Let's Encrypt
- Kubernetes: TLS Ingress + Service Mesh mTLS
- Sensitive Media Files: Verschlüsselung auf Application-Level (Django)

### Audit & Compliance

**Aktueller Audit Trail:**

- ✅ AuditLog Model (User Actions tracked)
- ✅ nginx Access Logs
- ⚠️ Django Application Logs (structured logging mit Request-IDs fehlt)
- ✅ Kubernetes Audit Logs (audit-policy.yaml für k3s konfiguriert)
- ✅ Centralized Logging (Loki + Promtail in K8s)

**Zero-Trust Requirements:**

- Alle API-Calls mit User-ID + Request-ID geloggt
- Security Events (Failed Logins, Permission Denied) hervorgehoben
- Tamper-proof Logging (Logs in externe SIEM/Log-Aggregation)
- Retention Policy (DSGVO: 90 Tage für Audit, 30 Tage für Access Logs)

**Compliance Frameworks:**

- DSGVO (General Data Protection Regulation) - EU
- ISO 27001 (Information Security Management)
- SOC 2 (Service Organization Control) - für Cloud-Provider
- GoBD (Grundsätze zur ordnungsmäßigen Führung von Büchern) - Deutschland

### Threat Model

**High-Value Assets:**

1. Rechnungsdaten (Business-Critical, DSGVO-relevant)
2. Kundendaten (Personenbezogen, DSGVO-relevant)
3. JWT Signing Keys (Kompromittierung = voller Zugriff)
4. Database Credentials (Kompromittierung = Daten-Leak)

**Threat Scenarios:**

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|------------|------------|
| SQL Injection | Data Leak | Low (ORM) | ✅ Django ORM, Input Validation |
| XSS in Frontend | Session Hijack | Medium | ✅ Vue.js Escaping + CSP Header (nginx) |
| JWT Token Theft | Account Takeover | Medium | ✅ Short expiry + HTTPS aktiv |
| Compromised Container | Lateral Movement | High | ✅ NetworkPolicies + PodSecurity (K8s), ⚠️ Docker limitiert |
| Secrets in Git | Full Compromise | High | ⚠️ Env-Vars statt Git, Vault noch offen |
| Vulnerable Dependencies | Code Execution | Medium | ✅ Dependabot + Trivy + pip-audit |
| DDoS Attack | Service Unavailable | High (Public) | ⚠️ Rate Limiting ✅, WAF noch offen |
| Privilege Escalation | Cluster Compromise | Low | ✅ RBAC + PodSecurity (K8s) |

### Next Steps — Umsetzungsplan (Stand: 2026-03-08)

Aktueller Maturity Level: **Level 2** (Docker) / **Level 2-3** (K8s).
Ziel: **Level 3** (Docker) / **Level 4** (K8s).

#### Sprint 1: Docker-Only Härten ~~(4-6h)~~ ✅ Erledigt 2026-03-08

| # | Aufgabe | Aufwand | Status |
|---|---------|---------|--------|
| 1 | Resource Limits in `docker-compose.production.yml` | 1h | ✅ Erledigt |
| 2 | Structured Logging + Request-ID Middleware | 2-3h | ✅ Bereits vorhanden |
| 3 | Docker Secrets statt .env-Files (Production) | 1-2h | ✅ Erledigt |

#### Sprint 2: Kubernetes Verschlüsselung (6-10h)

| # | Aufgabe | Aufwand | Status |
|---|---------|---------|--------|
| 4 | TLS Ingress mit cert-manager (k3s) | 2-3h | ✅ Erledigt |
| 5 | External Secrets Operator + Vault | 4-6h | ✅ Erledigt (Phase 2 K8s-Backend, Vault vorbereitet) |
| 6 | Image Signing mit Cosign | 1-2h | ✅ Erledigt (Keyless via GitHub Actions OIDC) |

#### Sprint 3: Service Mesh & Observability (10-15h, NICE-TO-HAVE)

| # | Aufgabe | Aufwand | Priorität |
|---|---------|---------|----------|
| 7 | Linkerd Service Mesh + automatisches mTLS | 3-4h | NICE |
| 8 | Request Tracing (Jaeger/Tempo) | 4-6h | NICE |
| 9 | WAF/ModSecurity für nginx Ingress | 2-3h | NICE |

**Siehe auch:**

- [SECURITY_IMPLEMENTATION.md](./SECURITY_IMPLEMENTATION.md) - Detaillierter Implementierungsplan
- [arc42/production-operations.md](./arc42/production-operations.md) - HTTPS/TLS Setup, Backup, Operations (konsolidiert)
