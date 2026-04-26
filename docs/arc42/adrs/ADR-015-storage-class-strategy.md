# ADR 015: Storage Class Strategy

## Status

**TODO** - Decision Pending

## Context

Kubernetes requires storage classes for persistent volumes used by:
- PostgreSQL database (primary data storage)
- File storage for generated PDFs and uploaded documents
- Backup storage
- Monitoring and logging data

Different workloads have different storage requirements:
- **Database**: High IOPS, low latency, consistency
- **File Storage**: High throughput, cost-effective
- **Backup**: Cost-optimized, high capacity

The storage class selection must consider:
- **Vendor lock-in avoidance** (not cloud-specific)
- **Cost efficiency** (balance performance and cost)
- **Performance** (IOPS, throughput, latency)
- **Availability** (replication, backup)
- **Portability** (migration between environments)

## Decision

**TO BE DETERMINED**

Need to evaluate storage options based on deployment environment (on-premises, cloud, or hybrid).

## Deployment Scenarios

### Scenario A: On-Premises Kubernetes

**Available Options:**
- Local storage (hostPath)
- NFS (Network File System)
- Ceph / Rook
- GlusterFS
- Longhorn
- OpenEBS

### Scenario B: Cloud Kubernetes (Multi-Cloud Compatible)

**Available Options:**
- CSI drivers for cloud storage (AWS EBS, Azure Disk, GCP PD)
- Portworx (commercial, multi-cloud)
- Rook-Ceph (cloud-agnostic)
- Longhorn (cloud-agnostic)

### Scenario C: Hybrid / Multi-Cloud

**Available Options:**
- Rook-Ceph
- Longhorn
- Portworx
- MinIO (for object storage)

## Storage Requirements by Workload

### PostgreSQL Database
- **Type**: Block storage
- **Performance**: High IOPS (5000+), low latency (<5ms)
- **Capacity**: 100GB-1TB (depends on scale)
- **Replication**: Built-in PostgreSQL replication, not storage-level
- **Backup**: Daily snapshots required
- **Access Mode**: ReadWriteOnce (RWO)

### File Storage (PDFs, Documents)
- **Type**: Object or file storage
- **Performance**: High throughput (100+ MB/s)
- **Capacity**: 500GB-5TB (depends on volume)
- **Replication**: Nice to have, not critical
- **Backup**: Weekly/monthly snapshots
- **Access Mode**: ReadWriteMany (RWX) preferred for multi-pod access

### Backup Storage
- **Type**: Object storage preferred
- **Performance**: Lower priority, cost-optimized
- **Capacity**: 2-10TB (multiple backups retained)
- **Replication**: Geo-redundant preferred
- **Backup**: Self-storage (backups of backups)
- **Access Mode**: ReadWriteOnce acceptable

## Options to Evaluate

### Option 1: Cloud-Native Storage (AWS EBS, Azure Disk, GCP PD)

**Pros:**
- Fully managed by cloud provider
- High performance and reliability
- Automatic replication (depending on tier)
- Snapshot capabilities built-in
- Easy to provision and scale

**Cons:**
- **Strong vendor lock-in** (different APIs per cloud)
- **Migration complexity** (moving data between clouds difficult)
- Costs can be significant at scale
- Not portable to on-premises

**Cost Considerations:**
- AWS EBS gp3: $0.08/GB/month + IOPS/throughput costs
- Azure Premium SSD: $0.12-0.20/GB/month
- GCP Persistent Disk SSD: $0.17/GB/month

**Verdict:** ⚠️ **Acceptable for cloud-only, but creates vendor lock-in**

---

### Option 2: Rook-Ceph

**Pros:**
- **Completely vendor-neutral** - runs anywhere
- **Free and open-source** (CNCF graduated)
- Block, file, and object storage in one
- Self-healing and automatic replication
- Excellent Kubernetes integration
- Snapshots and cloning supported
- Can run on-premises or in cloud

**Cons:**
- **Complex to set up and operate** - requires expertise
- Resource overhead (Ceph daemons consume CPU/memory)
- Requires at least 3 nodes for HA
- Learning curve steep
- Troubleshooting can be challenging

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Medium-High (needs dedicated storage nodes/disks)
- Operational: High (requires Ceph expertise)

**Verdict:** ✅ **Excellent for vendor neutrality, but complex**

---

### Option 3: Longhorn (CNCF Project)

**Pros:**
- **Simple to install and operate** (easier than Ceph)
- **Vendor neutral** - runs anywhere
- **Free and open-source** (CNCF sandbox project)
- Good UI for management
- Automatic replication
- Snapshot and backup support
- Lower resource overhead than Ceph
- Good Kubernetes integration

**Cons:**
- Less mature than Ceph
- Performance not as high as dedicated storage systems
- Primarily for block storage (not object storage)
- Smaller community than Ceph
- Not suitable for very high-performance workloads

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Low-Medium (uses existing node storage)
- Operational: Medium (simpler than Ceph)

**Verdict:** ✅✅ **Good balance of simplicity and vendor neutrality**

---

### Option 4: NFS (Network File System)

**Pros:**
- **Very simple** to set up and use
- **Vendor neutral** - standard protocol
- **Low cost** - can use existing NAS
- Supports ReadWriteMany (RWX)
- Mature and well-understood
- Good for file storage workloads

**Cons:**
- Not suitable for databases (performance, consistency issues)
- Single point of failure (unless using HA NFS)
- No built-in replication or snapshots (depends on NAS)
- Potential performance bottleneck
- Security concerns (NFS v3)

**Cost Considerations:**
- Software: $0 (protocol)
- Infrastructure: Depends on NAS appliance (can reuse existing)
- Operational: Low (simple to maintain)

**Verdict:** ✅ **Good for file storage, not for databases**

---

### Option 5: Local Storage (hostPath / Local PV)

**Pros:**
- **Highest performance** (no network overhead)
- **Zero cost** - uses node's local disk
- **Vendor neutral**
- Simplest configuration

**Cons:**
- **No replication** - data loss if node fails
- **Not portable** - pods tied to specific nodes
- Not suitable for production databases
- Backup complexity

**Cost Considerations:**
- $0 (uses local disks)

**Verdict:** ⚠️ **Only for development/testing, not production**

---

### Option 6: OpenEBS

**Pros:**
- **Container-native storage** (Kubernetes-first)
- **Vendor neutral** and open-source
- Multiple storage engines (Mayastor, cStor, LocalPV)
- Simpler than Ceph
- Good performance with Mayastor engine

**Cons:**
- Smaller community than Ceph/Longhorn
- Less mature than Ceph
- Some engines still in beta
- Limited production deployments

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Medium
- Operational: Medium

**Verdict:** ✅ **Worth considering as alternative to Longhorn**

---

## Evaluation Criteria

| Criterion | Weight | Cloud-Native | Rook-Ceph | Longhorn | NFS | Local | OpenEBS |
|-----------|--------|--------------|-----------|----------|-----|-------|---------|
| Vendor Lock-in Avoidance | **High** | ❌ | ✅✅✅ | ✅✅✅ | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| Cost Efficiency | **High** | ⚠️ | ✅✅ | ✅✅✅ | ✅✅✅ | ✅✅✅ | ✅✅ |
| Operational Simplicity | High | ✅✅✅ | ❌ | ✅✅ | ✅✅✅ | ✅✅✅ | ✅✅ |
| Database Performance | High | ✅✅✅ | ✅✅ | ✅✅ | ❌ | ✅✅✅ | ✅✅ |
| File Storage Support | Medium | ⚠️ | ✅✅✅ | ⚠️ | ✅✅✅ | ❌ | ✅✅ |
| High Availability | Medium | ✅✅✅ | ✅✅✅ | ✅✅ | ⚠️ | ❌ | ✅✅ |
| Portability | **High** | ❌ | ✅✅✅ | ✅✅✅ | ✅✅ | ✅✅ | ✅✅✅ |

Legend: ✅✅✅ Excellent | ✅✅ Good | ⚠️ Acceptable | ❌ Poor

## Questions to Answer

1. **Deployment Environment**:
   - On-premises, cloud, or hybrid?
   - Single cloud or multi-cloud strategy?

2. **Operational Capacity**:
   - Do we have expertise to run Ceph?
   - Or prefer simpler solutions (Longhorn, managed storage)?

3. **Performance Requirements**:
   - What are actual IOPS/throughput needs?
   - Can we measure current database performance requirements?

4. **Budget**:
   - What is acceptable monthly storage cost?
   - Is operational complexity cost more important than storage cost?

5. **Scale**:
   - How much data now? In 1 year? In 3 years?
   - Growth projections?

6. **Backup Strategy**:
   - What are RTO/RPO requirements?
   - Snapshot frequency needed?

## Recommended Approach

**TO BE DECIDED AFTER ANSWERING ABOVE QUESTIONS**

### Possible Hybrid Strategy:

| Workload | Storage Solution | Rationale |
|----------|------------------|-----------|
| PostgreSQL (Production) | Longhorn or Cloud SSD | Performance + reliability |
| Files (PDFs, Uploads) | NFS or Rook-Ceph (CephFS) | RWX support, cost-effective |
| Backups | S3-compatible (MinIO) or Rook-Ceph (Object) | Cost-optimized object storage |
| Development/Testing | Local Storage or NFS | Simple, low cost |

## Implementation Notes (Placeholder)

**TO BE COMPLETED AFTER DECISION**

### StorageClass Definitions:
```yaml
# Example - TO BE CUSTOMIZED
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: TBD
parameters:
  # TBD based on chosen solution
```

### Backup Strategy:
- Snapshot schedule
- Retention policy
- Disaster recovery procedure

## Consequences

**TO BE DOCUMENTED AFTER DECISION**

## Related Decisions

- ADR-002: PostgreSQL Database (storage consumer)
- ADR-007: Data Persistence Strategy (application-level)
- ADR-010: Kubernetes Orchestration (platform)

## References

- [Kubernetes Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Rook-Ceph](https://rook.io/)
- [Longhorn](https://longhorn.io/)
- [OpenEBS](https://openebs.io/)
- [CNCF Storage Landscape](https://landscape.cncf.io/guide#provisioning--cloud-native-storage)

---

**Next Steps:**
1. Determine deployment environment (on-prem, cloud, hybrid)
2. Assess operational capacity for complex solutions (Ceph)
3. Benchmark performance requirements
4. Compare total cost of ownership
5. Make decision and document storage classes
6. Test backup and restore procedures
