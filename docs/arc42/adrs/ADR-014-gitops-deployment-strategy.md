# ADR 014: GitOps Deployment Strategy

## Status

**Accepted** — 2026-04-30

## Context

GitOps is a deployment methodology where Git serves as the single source of truth for infrastructure and application configurations. Changes are made via Git commits and pull requests, with automated systems synchronizing the desired state to the cluster.

For the eRechnung Kubernetes deployment, we need to decide on the deployment approach:
- Traditional CI/CD with kubectl/helm apply
- GitOps with automated reconciliation
- Hybrid approach

### Key Considerations

1. **Vendor Lock-in**: Solution must work across different Kubernetes distributions
2. **Cost**: Both tooling costs and operational overhead
3. **Complexity**: Learning curve and operational burden
4. **Auditability**: Complete history of changes
5. **Security**: Credentials management and access control
6. **Developer Experience**: Ease of deployment and debugging

## Decision

**Two-stage approach: keep traditional `kubectl apply -k` short-term, introduce ArgoCD mid-term.**

1. **Short-term (status quo):** Continue using `kubectl apply -k infra/k8s/k3s/` driven by GitHub Actions. No change to the existing workflow.
2. **Mid-term:** Install ArgoCD in the k3s cluster and migrate deployment to an App-of-Apps configuration that watches `infra/k8s/k3s/`. The traditional kustomize layout stays intact — ArgoCD only adds reconciliation on top.

FluxCD and Jenkins X are explicitly rejected.

### Rationale

- **Market relevance / hireability:** ArgoCD is the dominant GitOps tool in current job postings and CNCF Graduated since December 2022. Adopting it strengthens the project's CV value.
- **UI matters:** For a single-maintainer project doing GoBD-relevant audits, ArgoCD's resource tree and live diff are tangible operational wins. Flux's CLI-only approach loses most of its appeal in this context.
- **Audit trail:** Sync history and reconciliation events live in the cluster, not only in CI logs — useful for compliance contexts.
- **Low migration risk:** ArgoCD reads the existing kustomize tree as-is. Rollback to traditional `kubectl apply` is a one-command operation.
- **Why not Flux:** Technically elegant and lightweight, but no first-party UI; the lone-maintainer scenario benefits more from visual feedback than from CLI minimalism.
- **Why not Jenkins X:** Disproportionate complexity for a single-cluster, two-deployment project; declining popularity.
- **Why not stay traditional forever:** Acceptable today, but lacks drift detection, self-healing, and in-cluster audit trail — gaps that will surface as the deployment scales (multi-cluster, additional environments, more contributors).

## Options to Evaluate

### Option 1: Traditional CI/CD (GitHub Actions + kubectl/helm)

**Pros:**
- **Simple and direct** - straightforward to understand
- **Low complexity** - no additional infrastructure
- **Flexible** - can use any CI/CD platform
- **Vendor neutral** - standard Kubernetes tools
- **Zero cost** for tooling (GitHub Actions free tier)
- Quick to set up and iterate

**Cons:**
- No drift detection or auto-reconciliation
- Manual rollback processes
- Cluster credentials in CI/CD system
- Less declarative, more imperative
- No multi-cluster sync out of the box
- Limited audit trail compared to Git history

**Cost Considerations:**
- GitHub Actions: Free for public repos, ~$0.008/minute for private
- No additional infrastructure needed

---

### Option 2: ArgoCD

**Pros:**
- **Most popular GitOps tool** for Kubernetes
- **Vendor neutral** - runs on any Kubernetes
- **Excellent UI** - visual application state and sync status
- Automatic drift detection and reconciliation
- Multi-cluster management
- RBAC and SSO integration
- **Free and open-source** (CNCF graduated project)
- Git as single source of truth
- Automated rollback capabilities
- Excellent Helm support

**Cons:**
- Additional infrastructure to run (ArgoCD itself)
- Learning curve for GitOps concepts
- Requires Git repository structure reorganization
- More complex for simple deployments
- Resource overhead (ArgoCD components)

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Low-Medium (ArgoCD pods in cluster)
- Operational: Medium (setup and learning curve)

---

### Option 3: Flux CD

**Pros:**
- **GitOps-native** - built for GitOps from the ground up
- **Lightweight** - minimal resource footprint
- **Vendor neutral** - CNCF project
- Multi-tenancy support
- Excellent Helm and Kustomize support
- Git-based access control
- Notification system (Slack, etc.)
- **Free and open-source**
- Progressive delivery support

**Cons:**
- **No UI** (command-line focused)
- Steeper learning curve than ArgoCD
- Smaller community than ArgoCD
- Less intuitive for beginners
- Debugging can be challenging without UI

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Low (lightweight controllers)
- Operational: Medium-High (CLI-focused)

---

### Option 4: Jenkins X

**Pros:**
- Full CI/CD + GitOps in one platform
- Preview environments for pull requests
- Built-in best practices
- **Vendor neutral**

**Cons:**
- **High complexity** - many moving parts
- Resource-intensive
- Opinionated workflow
- Declining popularity
- Learning curve steep

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: High (many components)
- Operational: High (complex to maintain)

---

### Option 5: Hybrid Approach

**Concept:**
- Use CI/CD for building and testing
- Use GitOps tool for deployment only
- Best of both worlds

**Pros:**
- **Flexibility** - choose best tool for each task
- Gradual adoption of GitOps
- Leverage existing CI/CD expertise
- **Vendor neutral** approach

**Cons:**
- More complex architecture
- Two systems to maintain
- Potential for confusion

---

## Evaluation Criteria

| Criterion | Weight | CI/CD Only | ArgoCD | Flux CD | Jenkins X | Hybrid |
|-----------|--------|------------|--------|---------|-----------|--------|
| Vendor Lock-in Avoidance | High | ✅✅✅ | ✅✅✅ | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| Cost Efficiency | High | ✅✅✅ | ✅✅ | ✅✅✅ | ⚠️ | ✅✅ |
| Simplicity | High | ✅✅✅ | ✅✅ | ⚠️ | ❌ | ⚠️ |
| Auditability | Medium | ⚠️ | ✅✅✅ | ✅✅✅ | ✅✅ | ✅✅ |
| Drift Detection | Medium | ❌ | ✅✅✅ | ✅✅✅ | ✅✅ | ✅✅✅ |
| Developer Experience | Medium | ✅✅ | ✅✅✅ | ⚠️ | ⚠️ | ✅✅ |
| Multi-Cluster Support | Low | ⚠️ | ✅✅✅ | ✅✅ | ✅✅ | ✅✅ |

Legend: ✅✅✅ Excellent | ✅✅ Good | ⚠️ Acceptable | ❌ Poor

## Questions to Answer

1. **Team Expertise**:
   - Is the team familiar with GitOps principles?
   - Or is traditional CI/CD more comfortable?

2. **Scale and Complexity**:
   - How many environments (dev, staging, prod)?
   - How many clusters to manage?
   - How frequent are deployments?

3. **Audit Requirements**:
   - Is complete audit trail a requirement?
   - Or is basic logging sufficient?

4. **Budget and Resources**:
   - Can we afford additional infrastructure for GitOps tools?
   - Or should we keep it minimal?

5. **Operational Capacity**:
   - Do we have capacity to learn and maintain GitOps tools?
   - Or prefer simpler, proven approaches?

6. **Security Model**:
   - Is pull-based deployment (GitOps) preferred for security?
   - Or is push-based (CI/CD) acceptable?

## Recommendation (Preliminary)

### For Initial Deployment:
**Start with Traditional CI/CD (GitHub Actions + Helm)**

**Rationale:**
- Simpler to set up initially
- Avoid premature complexity
- Team likely familiar with CI/CD
- Can migrate to GitOps later if needed
- Lower operational overhead

### Migration Path:
1. **Phase 1** (Now): GitHub Actions + Helm
2. **Phase 2** (Evaluate): Monitor pain points
3. **Phase 3** (If needed): Migrate to ArgoCD for GitOps benefits

### When to Adopt GitOps:
- Managing multiple environments/clusters
- Frequent deployments requiring audit trails
- Team growth necessitating better change control
- Drift detection becomes important
- Multi-tenancy requirements

## Implementation Notes

### ArgoCD Specific:
```yaml
# Example Application manifest
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: erechnung
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/erechnung-k8s
    targetRevision: HEAD
    path: k8s/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: erechnung
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Repository Structure:
```
erechnung-k8s/
├── base/
│   └── kustomization.yaml
├── overlays/
│   ├── development/
│   ├── staging/
│   └── production/
└── argocd/
    └── applications/
```

## Consequences

### Positive
- Drift detection and self-healing for the k3s deployment.
- In-cluster audit trail (sync history, reconciliation events) supplementing CI/CD logs — relevant for GoBD operational evidence.
- Web UI gives immediate visual feedback on cluster state vs. Git state.
- Skill alignment with mainstream Kubernetes job market.
- Coexists with the existing `kubectl apply -k` workflow during the transition; no big-bang migration required.

### Negative
- Additional runtime components in the k3s cluster (argocd-server, repo-server, application-controller, redis) — modest CPU/memory overhead.
- Learning curve for App-of-Apps and ApplicationSet patterns.
- One more component to upgrade and monitor.
- The Docker Compose deployment is unaffected — ArgoCD applies only to the Kubernetes target, leaving the two deployments structurally asymmetric.

### Mitigations
- Pin ArgoCD to an explicit chart version (no `:latest`, per project rules).
- Keep `kubectl apply -k` as documented fallback in `infra/k8s/k3s/README.md` for the duration of the transition.
- Document the App-of-Apps layout in `docs/arc42/production-operations.md` once installed.

## Related Decisions

- ADR-010: Kubernetes Orchestration (deployment target)
- ADR-012: Secrets Management (how secrets are deployed)
- CI/CD pipeline in `/ci/github-actions-workflows/`

## References

- [ArgoCD](https://argo-cd.readthedocs.io/)
- [Flux CD](https://fluxcd.io/)
- [GitOps Principles](https://opengitops.dev/)
- [CNCF GitOps Working Group](https://github.com/cncf/tag-app-delivery)
- [Weaveworks GitOps Guide](https://www.weave.works/technologies/gitops/)

---

**Next Steps:**
1. Pin ArgoCD chart version and add manifests under `infra/k8s/k3s/argocd/`.
2. Create App-of-Apps definition pointing at `infra/k8s/k3s/`.
3. Validate sync against the existing cluster (read-only / `--dry-run` first).
4. Cut over: enable `automated.selfHeal` and `prune`.
5. Update `docs/arc42/production-operations.md` and `infra/k8s/k3s/README.md`.
