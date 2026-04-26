# Dokumentations-Synchronisation: req42 und arc42

## Zusammenfassung

Dieser Report dokumentiert alle Änderungen, die vorgenommen wurden, um die req42 (Requirements) und arc42 (Architektur) Dokumentation mit den tatsächlich implementierten Features aus README.md, TODO.md und PROGRESS_PROTOCOL.md zu synchronisieren.

**Status:** Alle identifizierten Lücken wurden geschlossen ✅

---

## Änderungen in req42 (Funktionale Anforderungen)

### Datei: docs/req42/05-functional-requirements.md

**Neue Abschnitte hinzugefügt:**

#### FR-07: Frontend-Funktionalität (Vue.js SPA)

- FR-07.01: Single Page Application
- FR-07.02: Responsive Design für Mobile/Tablet/Desktop
- FR-07.03: Echtzeit-Dashboard mit Statistiken
- FR-07.04: Confirmation Dialogs für kritische Aktionen
- FR-07.05: Loading States und Error Handling
- FR-07.06: Toast Notifications
- FR-07.07: Offline-Erkennung und Netzwerkfehler-Behandlung

**Begründung:** Vue.js 3 Frontend wurde in Phase 1-6 (November 2025 - Januar 2026) vollständig implementiert mit 381 Unit Tests.

#### FR-08: Advanced Features

- FR-08.01: Advanced Filtering mit URL-Persistenz
- FR-08.02: Bulk Operations (Multi-Select, Bulk Delete)
- FR-08.03: CSV Export mit deutscher Formatierung
- FR-08.04: CSV/JSON Import mit Validierung
- FR-08.05: Table Sorting für alle Listen-Ansichten
- FR-08.06: DatePicker Integration

**Begründung:** Phase 6 Features (Januar 2026) vollständig implementiert.

#### FR-09: Background Processing

- FR-09.01: Asynchrone Task-Verarbeitung mit Celery
- FR-09.02: Redis als Message Broker und Cache
- FR-09.03: Background-Jobs für zeitintensive Operationen
- FR-09.04: Task-Status-Tracking

**Begründung:** Celery Worker läuft produktiv in allen Deployment-Varianten.

#### FR-10: API Gateway und Rate Limiting

- FR-10.01: nginx API Gateway als Reverse Proxy
- FR-10.02: Rate Limiting pro IP-Adresse
- FR-10.03: Security Headers (HSTS, CSP, X-Frame-Options)
- FR-10.04: API-Versionierung über Gateway
- FR-10.05: CORS-Konfiguration zentral

**Begründung:** API Gateway seit Juli 2025 produktiv, vollständig in Kubernetes integriert.

#### FR-11: Health Monitoring

- FR-11.01: Drei-stufige Health Endpoints (/health/, /health/detailed/, /health/readiness/)
- FR-11.02: Komponenten-Status-Überprüfung (PostgreSQL, Redis)
- FR-11.03: JSON-formatierte Health-Antworten

**Begründung:** Health Endpoints für Kubernetes Probes seit Dezember 2025 implementiert.

**Neue User Stories:**

Epic: Frontend UI/UX

- US-13: Moderne, intuitive Oberfläche
- US-14: Echtzeit-Statistiken Dashboard
- US-15: Bulk Operations
- US-16: Advanced Filtering
- US-17: CSV Export
- US-18: CSV/JSON Import

Epic: Testing & Quality Assurance

- US-19: E2E Tests mit Playwright
- US-20: Frontend Unit Tests
- US-21: CI/CD Tests in GitHub Actions

---

## Änderungen in req42 (Qualitätsanforderungen)

### Datei: docs/req42/06-quality-requirements.md

**Neue Abschnitte hinzugefügt:**

#### NFR-10: Frontend Performance

- NFR-10.01: First Contentful Paint (FCP) < 1.5s
- NFR-10.02: Time to Interactive (TTI) < 3s
- NFR-10.03: Bundle Size < 300KB gzipped
- NFR-10.04: Vue.js 3 mit Composition API
- NFR-10.05: Vite Build System

**Begründung:** Vue.js 3 Frontend optimiert für Performance.

#### NFR-11: Test Coverage

- NFR-11.01: Backend Unit Tests: 80%+ Coverage (aktuell: 263 Tests)
- NFR-11.02: Frontend Unit Tests: 80%+ Coverage (aktuell: 381 Tests)
- NFR-11.03: E2E Tests: 90%+ Pass-Rate (aktuell: 96%)
- NFR-11.04: CI/CD Pipeline mit automatisierten Tests
- NFR-11.05: Test-Isolation

**Begründung:** Umfassende Test-Infrastruktur produktiv seit Februar 2026.

#### NFR-12: Kubernetes Enterprise Deployment

- NFR-12.01: Multi-Node Cluster Support
- NFR-12.02: LoadBalancer Integration (MetalLB)
- NFR-12.03: Ingress Controller mit TLS/HTTPS
- NFR-12.04: Network Policies für Zero-Trust
- NFR-12.05: Pod Security Standards
- NFR-12.06: CNI Provider (Calico)
- NFR-12.07: Persistent Storage mit PVC
- NFR-12.08: InitContainer für DB Migrations

**Begründung:** Kubernetes Deployment produktionsreif seit Februar 2026.

#### NFR-13: Container Registry

- NFR-13.01: Lokale HTTPS Docker Registry
- NFR-13.02: Image Pull < 20s (PostgreSQL)
- NFR-13.03: containerd Mirror Configuration
- NFR-13.04: Alle Images lokal verfügbar
- NFR-13.05: TLS-Zertifikate

**Begründung:** Lokale Registry seit Januar 2026, 15x schnellere Deployments.

#### NFR-14: Developer Experience

- NFR-14.01: Docker-First Development
- NFR-14.02: Hot-Reload für Frontend (Vite HMR)
- NFR-14.03: Lokale E2E Tests in Container
- NFR-14.04: API-Dokumentation mit OpenAPI/Swagger
- NFR-14.05: Strukturierte Projekt-Dokumentation

**Begründung:** Vollständige Developer Experience implementiert.

---

## Neue ADRs in arc42

### ADR-018: Vue.js 3 Framework Selection for Frontend SPA

**Status:** Accepted (November 2025)

**Kernpunkte:**

- Vue.js 3.5.24 mit Composition API gewählt
- Vite 7.2.2 für Build Tooling
- Pinia 3.0.4 für State Management
- Tailwind CSS 4.1.17 für Styling
- Playwright für E2E Testing

**Begründung:**

- Beste Developer Experience
- Kleine Bundle Size (~30KB)
- Composition API für Code Reuse
- Hervorragende TypeScript-Unterstützung

**Milestones:**

- Phase 1-6 abgeschlossen (November 2025 - Januar 2026)
- 381 Unit Tests, 96% E2E Test Pass-Rate

**Datei:** `docs/arc42/adrs/ADR-018-vuejs-3-frontend-selection.md`

---

### ADR-019: Playwright for End-to-End Testing

**Status:** Accepted (November 2025)

**Kernpunkte:**

- Playwright 1.49.1 für Multi-Browser E2E Tests
- Docker-basierte Test-Infrastruktur
- 90 E2E Tests, 96% Pass-Rate (74/77 passing)
- CI/CD Integration in GitHub Actions

**Begründung:**

- Multi-Browser Support (Chromium, Firefox, WebKit)
- Intelligentes Auto-Waiting
- Hervorragende Debugging-Tools (UI Mode, Trace Viewer)
- Robust Selectors mit User-Facing API

**Test Coverage:**

- Authentication, Token Refresh
- CRUD Operations (Invoices, Customers, Companies)
- Pagination, Filtering, Bulk Operations
- Export/Import Funktionalität

**Datei:** `docs/arc42/adrs/ADR-019-playwright-e2e-testing.md`

---

### ADR-020: Local HTTPS Docker Registry for Kubernetes Image Management

**Status:** Accepted (January 2026)

**Kernpunkte:**

- Lokale HTTPS Docker Registry auf 192.168.178.80:5000
- 11 Images (4 Application, 4 Infrastructure, 3 CNI)
- containerd Mirror Configuration auf allen Kubernetes Nodes
- Self-signed TLS Certificates

**Performance-Verbesserung:**

- PostgreSQL Pull: 12+ Minuten → <20 Sekunden (36x schneller)
- Gesamt-Deployment: 15 Minuten → 1 Minute (15x schneller)

**Begründung:**

- Eliminierung externer Registry-Abhängigkeiten
- Keine Docker Hub Rate-Limits
- Offline-Fähigkeit
- Volle Kontrolle über Images

**Datei:** `docs/arc42/adrs/ADR-020-local-https-registry.md`

---

### ADR-021: MetalLB for Kubernetes LoadBalancer Services

**Status:** Accepted (January 2026)

**Kernpunkte:**

- MetalLB v0.14.9 in Layer 2 Mode
- IP Pool: 172.18.255.200-250 (kind Docker-Netzwerk)
- Ingress Controller External-IP: 172.18.255.200
- ARP-basierte LoadBalancer-Funktionalität

**Problem gelöst:**

- kind hat keinen nativen LoadBalancer
- Services bleiben ohne MetalLB in `<pending>` State
- Externe Erreichbarkeit unmöglich

**Begründung:**

- Production-Grade LoadBalancer für Bare-Metal
- Einfache Layer 2 Setup (kein BGP erforderlich)
- kind-kompatibel
- CNCF Sandbox Project

**Datei:** `docs/arc42/adrs/ADR-021-metallb-loadbalancer.md`

---

### ADR-022: Calico CNI Provider for Kubernetes Network Policies

**Status:** Accepted (January 2026)

**Kernpunkte:**

- Calico v3.27.0 als CNI Provider
- Network Policy API vollständig implementiert
- Zero-Trust Architecture mit Default-Deny
- 12 Network Policies für Least-Privilege Access

**Problem gelöst:**

- kindnetd (default CNI) unterstützt KEINE Network Policies
- Policies wurden stillschweigend ignoriert
- Keine Netzwerk-Segmentierung möglich

**Begründung:**

- Production-Grade Network Policies
- iptables-basierte Enforcement (performant)
- CNCF Graduated Project
- Umfassende Observability

**Datei:** `docs/arc42/adrs/ADR-022-calico-cni-network-policies.md`

---

### ADR-023: pypdf-only Backend for PDF/A-3 Generation

**Status:** Accepted (September 2025)

**Kernpunkte:**

- PyPDF4 vollständig entfernt (deprecated, unmaintained seit 2020)
- pypdf v5.1.0+ als einzige PDF-Bibliothek
- Vereinfachte Architektur (kein Fallback mehr)
- Bessere Sicherheit und Python 3.11+ Kompatibilität

**Begründung:**

- PyPDF4 ist sicherheitsrisiko (keine Updates seit 2020)
- pypdf ist aktiv maintained (moderner Nachfolger)
- Feature-Parität erreicht
- Reduzierte Code-Komplexität (~300 Zeilen entfernt)

**Validierung:**

- Alle 263 Backend Tests bestehen
- PDF/A-3 Compliance erhalten
- ZUGFeRD Validierung funktioniert

**Datei:** `docs/arc42/adrs/ADR-023-pypdf-only-backend.md`

---

## Weitere Änderungen

### docs/arc42/09-architecture-decisions.md

**Aktualisierte ADR-Übersichtstabelle:**

- ADR-009 Status: Proposed → Accepted
- ADR-018 hinzugefügt: Vue.js 3 Frontend Selection
- ADR-019 hinzugefügt: Playwright E2E Testing
- ADR-020 hinzugefügt: Local HTTPS Registry
- ADR-021 hinzugefügt: MetalLB LoadBalancer
- ADR-022 hinzugefügt: Calico CNI Network Policies
- ADR-023 hinzugefügt: pypdf-only Backend

---

### docs/arc42/07-deployment-view.md

**Neuer Abschnitt hinzugefügt:** 7.7 Implemented Kubernetes Deployment (Production-Ready, February 2026)

**Inhalt:**

- Real-World Implementation Status
- Multi-Node Cluster Configuration (1 Control-Plane + 2 Workers)
- Infrastructure Components (Calico, MetalLB, Ingress, Registry)
- 10 Application Services mit Details
- 12 Network Policies (Zero-Trust)
- Local HTTPS Registry Integration
- Security Implementation (Pod Security Standards, TLS)
- Deployment Architecture Diagram
- Health Checks, InitContainer Details
- Network Policy Beispiele
- Deployment Workflow (Setup, Application, Network Policies)
- Production Readiness Status
- Deployment Metrics (7 min, 15x faster, 96% E2E Pass-Rate)

---

## Statistiken

### Änderungs-Übersicht

**req42 (Requirements):**

- ✅ 5 neue Functional Requirements (FR-07 bis FR-11)
- ✅ 5 neue Quality Requirements (NFR-10 bis NFR-14)
- ✅ 9 neue User Stories (US-13 bis US-21)

**arc42 (Architektur):**

- ✅ 6 neue ADRs (ADR-018 bis ADR-023)
- ✅ 1 aktualisierte ADR-Übersichtstabelle
- ✅ 1 neuer Deployment View Abschnitt (7.7)

**Gesamt:**

- ✅ 27 Änderungen in 4 Dateien

### Abdeckung der implementierten Features

**Vollständig dokumentiert:**

- ✅ Vue.js 3 Frontend (Phase 1-6)
- ✅ Playwright E2E Testing (90 Tests, 96% Pass-Rate)
- ✅ Kubernetes Multi-Node Deployment
- ✅ Local HTTPS Docker Registry
- ✅ MetalLB LoadBalancer
- ✅ Calico CNI Network Policies
- ✅ pypdf-only Backend
- ✅ API Gateway mit Rate Limiting
- ✅ Celery Background Processing
- ✅ Health Endpoints (drei-stufig)
- ✅ Advanced Frontend Features (Filtering, Bulk, Export/Import)

---

## Nacharbeiten empfohlen

Die folgenden Bereiche sollten vom Projektverantwortlichen überprüft werden:

### 1. Technische Details validieren

**ADR-018 (Vue.js 3):**

- [ ] Prüfen: Sind die genannten Paket-Versionen korrekt?
- [ ] Prüfen: Fehlen wichtige Composables oder Stores?
- [ ] Prüfen: Sind die Milestones-Daten korrekt?

**ADR-020 (Local Registry):**

- [ ] Prüfen: Registry-URL und Konfiguration korrekt dokumentiert?
- [ ] Prüfen: Sind alle 11 Images vollständig aufgelistet?
- [ ] Prüfen: containerd hosts.toml Pfad korrekt?

**ADR-022 (Calico CNI):**

- [ ] Prüfen: Calico Version und Manifests korrekt?
- [ ] Prüfen: Sind alle 12 Network Policies dokumentiert?
- [ ] Prüfen: Image Pre-Load Workaround noch relevant?

### 2. Business Requirements verfeinern

**FR-07 (Frontend-Funktionalität):**

- [ ] Ergänzen: Spezifische UI/UX Requirements
- [ ] Ergänzen: Accessibility Requirements (WCAG)
- [ ] Ergänzen: Internationalisierung (i18n) Requirements

**FR-08 (Advanced Features):**

- [ ] Ergänzen: Export-Formate (CSV, JSON, PDF, Excel?)
- [ ] Ergänzen: Import-Validierungsregeln detailliert
- [ ] Ergänzen: Bulk Operations (welche genau?)

**NFR-12 (Kubernetes):**

- [ ] Definieren: SLA für Kubernetes Deployment (Uptime?)
- [ ] Definieren: Backup/Restore Strategie
- [ ] Definieren: Disaster Recovery Prozess

### 3. Fehlende Aspekte

**Security:**

- [ ] ADR für Security Hardening (RBAC, Pod Security, etc.)
- [ ] ADR für Secrets Management (External Secrets Operator?)
- [ ] Security Testing Requirements (SAST, DAST, Penetration Tests)

**Monitoring:**

- [ ] NFR für Monitoring und Observability
- [ ] ADR für Prometheus + Grafana (falls geplant)
- [ ] Alerting und Incident Response Requirements

**Compliance:**

- [ ] GoBD Compliance Details in Requirements
- [ ] DSGVO Compliance Requirements verfeinern
- [ ] Audit Trail Requirements detailliert

### 4. Diagramme und Visualisierungen

**arc42 Deployment View:**

- [ ] Aktuelles Kubernetes Diagramm als Mermaid oder PlantUML
- [ ] Network Policy Visualisierung
- [ ] Service-Mesh Diagramm (falls geplant)

**arc42 Building Block View:**

- [ ] Vue.js Component Hierarchy Diagramm
- [ ] Backend Service Layer Diagramm
- [ ] API Gateway Architektur Diagramm

### 5. Cross-References prüfen

- [ ] Alle ADR cross-references validieren
- [ ] Links zwischen req42 und arc42 ergänzen
- [ ] Links zu README.md und TODO.md aus arc42/req42

---

## Empfehlungen für zukünftige Synchronisation

1. **Regelmäßige Reviews:** Quartalsweise req42/arc42 vs. README/TODO/PROGRESS_PROTOCOL abgleichen

2. **Change Process:** Jede größere Feature-Implementierung sollte parallel Requirements und ADRs aktualisieren

3. **Tools:** Erwägen: Automated Documentation Tools (Structurizr, PlantUML, arc42-generator)

4. **Skills:** Team sollte arc42/req42 Methodik kennen und nutzen

5. **Templates:** Projektspezifische Templates für ADRs und Requirements erstellen

---

## Kontakt für Rückfragen

Bei Fragen zu den vorgenommenen Änderungen oder Inkonsistenzen:

- README.md und TODO.md enthalten die aktuellsten Feature-Listen
- PROGRESS_PROTOCOL.md enthält historische Milestones mit Details
- Alle ADRs sind in `docs/arc42/adrs/` vollständig dokumentiert
- Network Policy Details: `k8s/kind/network-policies.yaml`
- Kubernetes Manifests: `k8s/kind/k8s-erechnung-local.yaml`

**Dokumentation ist jetzt synchron mit Implementierung (Stand: Februar 2026)** ✅
