# ADR 012: Secrets Management Strategy

## Status

**TODO** - Decision Pending

## Context

Kubernetes applications require secure management of sensitive data:
- Database credentials
- JWT signing keys
- API keys and tokens
- TLS/SSL certificates
- Third-party service credentials
- Encryption keys

The eRechnung system needs a secrets management solution that:
- Avoids vendor lock-in to specific cloud providers
- Provides cost-effective operation at various scales
- Supports secure storage and rotation of secrets
- Integrates well with Kubernetes
- Enables audit logging
- Supports encryption at rest and in transit

### Key Requirements

1. **Vendor Neutrality**: Must work on-premises and across different cloud providers
2. **Cost Efficiency**: Minimize licensing and operational costs
3. **Security**: Strong encryption, access controls, audit trails
4. **Kubernetes Integration**: Native or seamless integration with K8s
5. **Secret Rotation**: Support automated rotation of credentials
6. **Backup and Recovery**: Reliable backup and disaster recovery
7. **Developer Experience**: Easy to use in development and production

## Decision

**TO BE DETERMINED**

Need to evaluate and decide between the following approaches.

## Options to Evaluate

### Option 1: HashiCorp Vault (Self-Hosted)

**Pros:**
- Industry standard, mature solution
- Vendor-neutral, runs anywhere
- Excellent Kubernetes integration via Vault Agent
- Dynamic secrets generation
- Rich audit logging
- Active community support
- **No licensing costs** for open-source version

**Cons:**
- Operational complexity (requires running Vault cluster)
- High availability setup requires careful configuration
- Resource overhead (dedicated pods/VMs)
- Learning curve for operations team
- Backup and disaster recovery complexity

**Cost Considerations:**
- Open Source: $0 licensing
- Operational costs: Compute resources for Vault cluster (~3 nodes for HA)
- Management overhead: DevOps time for maintenance

---

### Option 2: External Secrets Operator + Cloud KMS (Multi-Cloud)

**Pros:**
- Leverages managed cloud services (reduced operations)
- Good Kubernetes integration
- Can switch between cloud providers
- Automatic backup by cloud provider
- **Open-source operator** ($0 licensing)

**Cons:**
- **Partial vendor lock-in** (secrets stored in cloud KMS)
- Costs scale with number of secrets and API calls
- Different configuration per cloud provider
- Migration between clouds requires secret export/import
- On-premises deployment more complex

**Cost Considerations:**
- AWS Secrets Manager: $0.40/secret/month + $0.05/10k API calls
- Azure Key Vault: ~$0.03/10k operations, certificates extra
- GCP Secret Manager: $0.06/secret version/month + access costs
- External Secrets Operator: $0 (open source)

---

### Option 3: Sealed Secrets (Bitnami)

**Pros:**
- **Completely vendor-neutral**
- **Zero operational costs** (no additional infrastructure)
- Secrets stored in Git (GitOps friendly)
- Simple architecture (just a controller)
- Minimal resource requirements
- Easy backup (secrets in Git)

**Cons:**
- No dynamic secrets generation
- Limited secret rotation capabilities
- No centralized audit logging
- Key management complexity
- Less suitable for highly sensitive environments
- Backup of private key is critical

**Cost Considerations:**
- $0 licensing and infrastructure
- Minimal compute overhead (single controller pod)

---

### Option 4: Kubernetes Native Secrets + etcd Encryption

**Pros:**
- **No additional infrastructure needed**
- **Zero cost**
- Built into Kubernetes
- Simple for basic use cases
- Encryption at rest via etcd

**Cons:**
- **Limited security features** (no rotation, no audit, basic access control)
- Secrets in plain text in etcd (unless encrypted)
- No secret versioning
- No dynamic secrets
- **Not recommended for production** sensitive data
- Difficult to manage at scale

**Cost Considerations:**
- $0 (built-in)

---

## Evaluation Criteria

| Criterion | Weight | Vault | External Secrets + KMS | Sealed Secrets | K8s Native |
|-----------|--------|-------|------------------------|----------------|------------|
| Vendor Lock-in Avoidance | High | ✅✅✅ | ⚠️ | ✅✅✅ | ✅✅✅ |
| Cost Efficiency | High | ⚠️ | ⚠️ | ✅✅✅ | ✅✅✅ |
| Security Features | High | ✅✅✅ | ✅✅ | ⚠️ | ❌ |
| Operational Complexity | Medium | ❌ | ⚠️ | ✅✅ | ✅✅✅ |
| K8s Integration | Medium | ✅✅ | ✅✅✅ | ✅✅ | ✅✅✅ |
| Secret Rotation | Medium | ✅✅✅ | ✅✅ | ⚠️ | ❌ |
| Audit Logging | Medium | ✅✅✅ | ✅✅ | ❌ | ⚠️ |

Legend: ✅✅✅ Excellent | ✅✅ Good | ⚠️ Acceptable | ❌ Poor

## Questions to Answer

1. **Deployment Environment**:
   - On-premises only, multi-cloud, or hybrid?
   - Does this influence the decision?

2. **Scale and Sensitivity**:
   - How many secrets need to be managed?
   - What is the sensitivity level of the data?

3. **Operational Capacity**:
   - Do we have capacity to run and maintain Vault?
   - Or prefer simpler, lower-maintenance solution?

4. **Budget Constraints**:
   - What is acceptable monthly cost for secrets management?
   - Is operational complexity cost more important than infrastructure cost?

5. **Compliance Requirements**:
   - Are there specific audit/compliance requirements?
   - Does this mandate certain solutions?

## Recommended Approach

**TO BE DECIDED AFTER ANSWERING ABOVE QUESTIONS**

### Possible Hybrid Approach:
- **Development/Testing**: Sealed Secrets (simple, low cost)
- **Production**: HashiCorp Vault or External Secrets + KMS (higher security)

### Migration Path:
- Start with Sealed Secrets for quick setup
- Migrate to Vault if security/audit requirements increase
- Or migrate to External Secrets if moving to managed cloud

## Implementation Notes (Placeholder)

**TO BE COMPLETED AFTER DECISION**

- Specific configuration examples
- Integration with cert-manager
- Secret rotation procedures
- Backup and recovery strategy
- Access control policies

## Consequences

**TO BE DOCUMENTED AFTER DECISION**

## Related Decisions

- ADR-010: Kubernetes Orchestration
- ADR-011: Ingress Controller Selection (certificate management)
- ADR-005: JWT Authentication (JWT secret storage)

## References

- [HashiCorp Vault](https://www.vaultproject.io/)
- [External Secrets Operator](https://external-secrets.io/)
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Secrets Management Best Practices](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)

---

**Next Steps:**
1. Evaluate deployment environment and requirements
2. Assess operational capacity and budget
3. Compare total cost of ownership for each option
4. Make decision and update this ADR
5. Document implementation details
