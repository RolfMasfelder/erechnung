# 9. Architecture Decisions

For detailed Architecture Decision Records (ADRs), please refer to the `/docs/arc42/adrs` directory.

## 9.1 Key Architecture Decisions Overview

| Decision                                    | Status    | Context                                                    |
|---------------------------------------------|-----------|-----------------------------------------------------------|
| [Use Django for Backend](./adrs/ADR-001-use-django.md) | Accepted | Framework selection for backend development                |
| [Use PostgreSQL as Database](./adrs/ADR-002-use-postgresql.md) | Accepted | Database technology selection                             |
| [Use Python-based Tools for PDF/A Generation](./adrs/ADR-003-use-python-pdf-generation.md) | Accepted | Technology choice for PDF/A-3 document generation          |
| [Docker-based Deployment](./adrs/ADR-004-docker-based-deployment.md) | Accepted | Infrastructure and deployment strategy                    |
| [JWT Authentication](./adrs/ADR-005-jwt-authentication.md) | Accepted | Authentication mechanism for APIs                          |
| [ZUGFeRD Comfort Profile Selection](./adrs/ADR-006-zugferd-profile-selection.md) | Accepted | ZUGFeRD Comfort Profile implementation as starting point   |
| [Two-Tier PostgreSQL Data Strategy](./adrs/ADR-007-data-persistence-strategy.md) | Accepted | Hot/warm data tiers with GDPR compliance support           |
| [Layered Validation Strategy](./adrs/ADR-008-error-handling-validation-strategy.md) | Accepted | Multi-layer validation with future rule engine support     |
| [Frontend Architecture & API-First](./adrs/ADR-009-frontend-architecture-api-first.md) | Accepted | API-first approach enabling multiple frontend types        |
| [Kubernetes Orchestration](./adrs/ADR-010-kubernetes-orchestration.md) | Accepted | Enterprise deployment with Kubernetes orchestration        |
| [Ingress Controller Selection](./adrs/ADR-011-ingress-controller-selection.md) | Accepted | nginx Ingress Controller for Kubernetes                   |
| [Secrets Management Strategy](./adrs/ADR-012-secrets-management-strategy.md) | Proposed | Kubernetes Secrets with External Secrets Operator          |
| [Service Mesh Decision](./adrs/ADR-013-service-mesh-decision.md) | Proposed | Service mesh evaluation for mTLS and observability        |
| [GitOps Deployment Strategy](./adrs/ADR-014-gitops-deployment-strategy.md) | Proposed | GitOps with Flux or ArgoCD for Kubernetes                 |
| [Storage Class Strategy](./adrs/ADR-015-storage-class-strategy.md) | Proposed | Storage class selection for Kubernetes PVCs               |
| [Monitoring Stack Selection](./adrs/ADR-016-monitoring-stack-selection.md) | Proposed | Prometheus + Grafana for system monitoring                |
| [Multi-Tenancy Strategy](./adrs/ADR-017-multi-tenancy-strategy.md) | Proposed | Multi-tenancy architecture for SaaS deployments           |
| [Vue.js 3 Frontend Selection](./adrs/ADR-018-vuejs-3-frontend-selection.md) | Accepted (Nov 2025) | Vue.js 3 with Composition API for modern SPA              |
| [Playwright E2E Testing](./adrs/ADR-019-playwright-e2e-testing.md) | Accepted (Nov 2025) | Playwright for cross-browser E2E testing                  |
| [Local HTTPS Registry](./adrs/ADR-020-local-https-registry.md) | Accepted (Jan 2026) | Local Docker Registry for offline Kubernetes deployments  |
| [MetalLB LoadBalancer](./adrs/ADR-021-metallb-loadbalancer.md) | Accepted (Jan 2026) | MetalLB for LoadBalancer services in bare-metal clusters  |
| [Calico CNI Network Policies](./adrs/ADR-022-calico-cni-network-policies.md) | Accepted (Jan 2026) | Calico CNI provider for Network Policy enforcement        |
| [pypdf-only Backend](./adrs/ADR-023-pypdf-only-backend.md) | Accepted (Sep 2025) | Single pypdf library, PyPDF4 removed for security         |

## 9.2 Current Architecture Decisions

### 9.2.1 Framework Selection
The Django framework was chosen for its built-in admin interface, ORM, and robust ecosystem of extensions like Django REST Framework.

### 9.2.2 Database Technology
PostgreSQL was selected for its reliability, ACID compliance, and advanced features like JSON support.

### 9.2.3 PDF Generation Technology
Python-based tools (ReportLab, WeasyPrint, factur-x) were chosen for PDF/A-3 generation to maintain consistency with the Python ecosystem.

### 9.2.4 Deployment Strategy
Docker and Docker Compose were chosen for containerization to ensure consistency across environments and simplify deployment.

### 9.2.5 Authentication Mechanism
JWT-based authentication was selected for its stateless nature, which improves scalability and simplifies client integration.

### 9.2.6 ZUGFeRD Profile Strategy
**ZUGFeRD Comfort Profile** was selected as the initial implementation target, covering 80-90% of business use cases while maintaining development focus and quality.

### 9.2.7 Data Persistence Strategy
**Two-tier PostgreSQL approach** with hot data (0-2 years) in standard tables and warm data (2+ years) in compressed partitions, optimizing for GDPR compliance and performance.

### 9.2.8 Validation Strategy
**Layered validation** across client-side, API, domain logic, and database constraints, with provisions for future rule engine integration for enhanced UI/UX guidance.

### 9.2.9 Frontend Architecture Strategy
**API-first approach** with Django REST Framework providing comprehensive APIs, enabling independent development of web, mobile, and desktop frontends while maintaining clear separation of concerns.

## 9.3 Future Decisions to Consider

### 9.3.1 Kubernetes Migration
As the system scales, a decision may be needed on migrating from Docker Compose to Kubernetes for enhanced orchestration capabilities.

### 9.3.2 Microservices Architecture
If specific components need independent scaling or deployment, a decision may be needed on migrating to a microservices architecture.

### 9.3.3 Message Queue Integration
For asynchronous processing of large batches of invoices, integration with a message queue system might be considered.
