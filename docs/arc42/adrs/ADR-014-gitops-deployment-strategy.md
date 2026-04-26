# ADR 014: GitOps Deployment Strategy

## Status

**TODO** - Decision Pending

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

**TO BE DETERMINED**

Need to evaluate whether GitOps is appropriate and which tool to use.

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

## Implementation Notes (If GitOps Chosen)

**TO BE COMPLETED AFTER DECISION**

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

**TO BE DOCUMENTED AFTER DECISION**

### If Traditional CI/CD:
- Positive: Simple, fast to implement, familiar
- Negative: Manual drift detection, less audit trail
- Mitigation: Document procedures, regular cluster validation

### If GitOps (ArgoCD/Flux):
- Positive: Drift detection, audit trail, declarative
- Negative: Additional complexity, learning curve
- Mitigation: Training, gradual adoption, good documentation

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
1. Assess team expertise and operational capacity
2. Determine scale and audit requirements
3. Evaluate cost-benefit of GitOps tools
4. Start with simpler approach, migrate if needed
5. Document chosen deployment workflow
