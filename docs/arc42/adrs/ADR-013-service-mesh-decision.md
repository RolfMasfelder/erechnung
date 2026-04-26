# ADR 013: Service Mesh Decision

## Status

**TODO** - Decision Pending

## Context

Service meshes provide advanced traffic management, security, and observability features for microservices:
- Mutual TLS (mTLS) between all services
- Advanced traffic routing (canary deployments, A/B testing, traffic splitting)
- Circuit breaking and fault injection
- Distributed tracing and metrics
- Service-to-service authorization
- Automatic retries and timeouts

For the eRechnung system, we need to decide whether to implement a service mesh and if so, which one.

### Current Architecture
- Monolithic Django application (not microservices yet)
- NGINX Ingress for external traffic (ADR-011)
- Standard Kubernetes Services for internal communication

### Key Considerations

1. **Vendor Lock-in**: Must avoid cloud-specific solutions
2. **Cost**: Both infrastructure and operational costs matter
3. **Complexity**: Current team expertise and learning curve
4. **Current Needs**: Do we need service mesh features now?
5. **Future Scalability**: Will we evolve to microservices?

## Decision

**TO BE DETERMINED**

Need to evaluate whether a service mesh is necessary and which option fits best.

## Options to Evaluate

### Option 1: No Service Mesh (Current State)

**Pros:**
- **Lowest complexity** - no additional infrastructure
- **Zero cost** - no service mesh overhead
- **Fastest to deploy** - no learning curve
- **Vendor neutral** - standard Kubernetes networking
- Sufficient for monolithic applications
- Lower resource consumption

**Cons:**
- No automatic mTLS between services
- Limited traffic management capabilities
- No built-in circuit breaking
- Manual implementation of retries, timeouts
- Less sophisticated observability

**When Suitable:**
- Monolithic or simple architectures
- Limited service-to-service communication
- No requirement for mTLS
- Cost-sensitive deployments

---

### Option 2: Istio

**Pros:**
- **Most feature-complete** service mesh
- Strong security features (mTLS, authorization policies)
- Advanced traffic management (canary, blue-green, A/B)
- Excellent observability (metrics, tracing, logging)
- **Vendor neutral** - runs anywhere
- Large community and ecosystem
- Good documentation

**Cons:**
- **High complexity** - steep learning curve
- **Significant resource overhead** (~1GB+ memory per node for sidecars + control plane)
- **High operational burden** - requires dedicated expertise
- Can impact application latency (sidecar proxy)
- Frequent breaking changes between versions
- **Overkill for simple architectures**

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: High (control plane + sidecars consume resources)
- Operational: High (requires skilled operations team)

---

### Option 3: Linkerd

**Pros:**
- **Simpler than Istio** - easier to learn and operate
- **Lower resource footprint** - optimized Rust-based proxy
- **Excellent mTLS** - automatic, zero-config
- Good performance and low latency
- **Vendor neutral** - runs anywhere
- CNCF graduated project (stable, trusted)
- Focus on security and reliability

**Cons:**
- Fewer features than Istio (less traffic management)
- Smaller ecosystem than Istio
- Less flexible for complex routing scenarios
- Fewer integrations than Istio
- Still adds operational complexity

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Medium (lighter than Istio)
- Operational: Medium (simpler than Istio)

---

### Option 4: Cilium Service Mesh

**Pros:**
- **eBPF-based** - very high performance, low overhead
- Can replace CNI (network plugin) + service mesh in one
- Advanced network policies
- **Vendor neutral**
- Modern, innovative approach
- Lower resource usage than traditional sidecars

**Cons:**
- Requires Linux kernel 4.9+ with eBPF support
- Newer, less mature than Istio/Linkerd
- Smaller community
- Learning curve for eBPF concepts
- Feature set still evolving

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Low (no sidecars, kernel-based)
- Operational: Medium (new technology to learn)

---

### Option 5: Consul Service Mesh

**Pros:**
- Multi-platform (not just Kubernetes)
- Good integration with HashiCorp ecosystem (Vault, Nomad)
- **Vendor neutral**
- Service discovery + mesh in one

**Cons:**
- Requires running Consul cluster
- **Commercial features** behind paywall (Consul Enterprise)
- More complex than Kubernetes-native solutions
- Smaller Kubernetes-specific community

**Cost Considerations:**
- Open Source: $0 but limited features
- Enterprise: Licensing costs for advanced features
- Operational: High (separate Consul infrastructure)

---

## Evaluation Criteria

| Criterion | Weight | No Mesh | Istio | Linkerd | Cilium | Consul |
|-----------|--------|---------|-------|---------|--------|--------|
| Vendor Lock-in Avoidance | High | ✅✅✅ | ✅✅✅ | ✅✅✅ | ✅✅✅ | ✅✅ |
| Cost (Infrastructure) | High | ✅✅✅ | ❌ | ⚠️ | ✅✅ | ⚠️ |
| Operational Simplicity | High | ✅✅✅ | ❌ | ⚠️ | ⚠️ | ❌ |
| Security (mTLS) | Medium | ❌ | ✅✅✅ | ✅✅✅ | ✅✅ | ✅✅ |
| Traffic Management | Low | ❌ | ✅✅✅ | ✅✅ | ✅✅ | ✅✅ |
| Observability | Medium | ⚠️ | ✅✅✅ | ✅✅ | ✅✅ | ✅✅ |
| Performance | Medium | ✅✅✅ | ⚠️ | ✅✅ | ✅✅✅ | ⚠️ |

Legend: ✅✅✅ Excellent | ✅✅ Good | ⚠️ Acceptable | ❌ Poor

## Questions to Answer

1. **Current Architecture**:
   - Do we have multiple services that need to communicate?
   - Or is it a monolithic Django application?

2. **Security Requirements**:
   - Is mTLS between services required?
   - Or is network-level security (NetworkPolicies) sufficient?

3. **Future Evolution**:
   - Will we split into microservices in the near future?
   - Or remain monolithic for the foreseeable future?

4. **Operational Capacity**:
   - Do we have expertise to run a service mesh?
   - Or should we keep it simple?

5. **Budget**:
   - Can we afford the resource overhead of a service mesh?
   - What is the cost-benefit analysis?

6. **Compliance**:
   - Are there regulatory requirements for mTLS?
   - Or can we achieve compliance without a service mesh?

## Recommendation (Preliminary)

### For Initial Deployment:
**Start WITHOUT a Service Mesh**

**Rationale:**
- Current architecture is monolithic (Django app)
- NGINX Ingress handles external traffic well (ADR-011)
- Kubernetes NetworkPolicies provide adequate isolation
- Avoid premature complexity and cost
- Can add later if needs evolve

### Migration Path:
1. **Phase 1** (Now): No service mesh
2. **Phase 2** (If microservices): Evaluate Linkerd (simple, secure)
3. **Phase 3** (If complex needs): Consider Istio or Cilium

### When to Reconsider:
- Migration to microservices architecture
- Regulatory requirement for mTLS
- Need for advanced traffic management (canary deployments)
- Security incidents requiring enhanced isolation

## Implementation Notes (If Service Mesh Chosen)

**TO BE COMPLETED AFTER DECISION**

### Istio Specific:
- Installation via Helm or istioctl
- Namespace labeling for sidecar injection
- Virtual Services and Destination Rules
- Authorization policies

### Linkerd Specific:
- Installation via Linkerd CLI
- Automatic mTLS configuration
- SMI (Service Mesh Interface) compatibility
- Simplified monitoring setup

### Cilium Specific:
- Replace existing CNI
- eBPF network policies
- Hubble for observability
- Cluster Mesh for multi-cluster

## Consequences

**TO BE DOCUMENTED AFTER DECISION**

### If No Service Mesh:
- Positive: Simple, low cost, fast deployment
- Negative: Manual security, limited traffic control
- Mitigation: Use NetworkPolicies, implement at app level

### If Service Mesh:
- Positive: Enhanced security, advanced traffic management, better observability
- Negative: Higher complexity, resource overhead, learning curve
- Mitigation: Training, start with simple configuration, gradual adoption

## Related Decisions

- ADR-010: Kubernetes Orchestration (provides platform)
- ADR-011: Ingress Controller Selection (external traffic)
- ADR-012: Secrets Management (certificate management for mTLS)

## References

- [Istio](https://istio.io/)
- [Linkerd](https://linkerd.io/)
- [Cilium Service Mesh](https://cilium.io/use-cases/service-mesh/)
- [Consul Service Mesh](https://www.consul.io/docs/connect)
- [CNCF Service Mesh Landscape](https://landscape.cncf.io/guide#orchestration-management--service-mesh)
- [Service Mesh Comparison](https://servicemesh.es/)

---

**Next Steps:**
1. Assess current and future architecture (monolith vs. microservices)
2. Determine security requirements (mTLS mandatory?)
3. Evaluate operational capacity and budget
4. Make decision based on actual needs, not trends
5. Document implementation plan if service mesh chosen
