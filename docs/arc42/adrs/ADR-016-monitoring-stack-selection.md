# ADR 016: Monitoring Stack Selection

## Status

**TODO** - Decision Pending

## Context

A production Kubernetes environment requires comprehensive monitoring for:
- Infrastructure metrics (nodes, pods, containers)
- Application metrics (request rates, latency, errors)
- Database performance
- Business metrics (invoices processed, success rates)
- Alerting on critical conditions
- Log aggregation and analysis

The monitoring solution must:
- **Avoid vendor lock-in** (not cloud-specific)
- Be **cost-effective** (prefer open-source)
- Integrate well with Kubernetes
- Support custom metrics for business KPIs
- Provide alerting and visualization

## Decision

**TO BE DETERMINED**

Need to evaluate monitoring solutions based on deployment environment and operational capacity.

## Options to Evaluate

### Option 1: Prometheus + Grafana (Self-Hosted)

**Pros:**
- **Industry standard** for Kubernetes monitoring
- **Completely vendor-neutral** - runs anywhere
- **Free and open-source** (both CNCF graduated)
- Excellent Kubernetes integration
- Rich ecosystem (exporters, integrations)
- Powerful query language (PromQL)
- Flexible alerting via Alertmanager
- Large community and good documentation
- **No licensing costs**

**Cons:**
- Operational overhead (requires maintenance)
- Limited long-term storage (needs external solution like Thanos)
- Scaling complexity for large deployments
- Alert configuration can be complex
- No built-in log aggregation (needs separate solution)

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Medium (Prometheus, Grafana, Alertmanager pods + storage)
- Operational: Medium (setup, maintenance, upgrades)

**Verdict:** ✅✅✅ **Best for vendor neutrality and cost**

---

### Option 2: Prometheus Operator (Managed Prometheus)

**Pros:**
- All benefits of Prometheus + Grafana
- **Simplified operations** via Operator pattern
- Automatic service discovery via ServiceMonitors
- **Vendor neutral** and open-source
- Easy Grafana integration
- Best practices built-in

**Cons:**
- Still requires operational effort
- Additional layer of complexity (Operator)
- Resource overhead for operator components

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Medium (similar to plain Prometheus)
- Operational: Low-Medium (easier than plain Prometheus)

**Verdict:** ✅✅✅ **Recommended variant of Option 1**

---

### Option 3: Cloud-Native Monitoring (CloudWatch, Azure Monitor, Google Cloud Monitoring)

**Pros:**
- **Fully managed** - no infrastructure to maintain
- Automatic scaling
- Integrated with cloud platform
- Built-in alerting and dashboards
- No operational overhead

**Cons:**
- **Strong vendor lock-in** (different for each cloud)
- **Costs scale with usage** (can become expensive)
- Limited customization
- Not portable to on-premises
- Vendor-specific query languages
- Migration between clouds very difficult

**Cost Considerations:**
- AWS CloudWatch: $0.30/metric/month + query costs + dashboard costs
- Azure Monitor: $0.25-2.88/GB ingested + query costs
- GCP Monitoring: $0.2580/million data points + query costs
- **Total**: Can easily reach $100-500+/month at scale

**Verdict:** ❌ **High vendor lock-in, costs can escalate**

---

### Option 4: Datadog / New Relic (Commercial SaaS)

**Pros:**
- Fully managed SaaS
- Excellent UI and user experience
- All-in-one (metrics, logs, traces, APM)
- Easy to set up
- Good support and documentation

**Cons:**
- **Very expensive** at scale
- **Vendor lock-in** to commercial platform
- Costs scale with hosts/containers
- Not self-hosted option
- Data sent to third party (compliance concern)

**Cost Considerations:**
- Datadog: ~$15-31/host/month (Infrastructure) + $23-40/host/month (APM)
- New Relic: ~$0.30/GB ingested + compute costs
- **Total**: Easily $500-2000+/month for small-medium deployments

**Verdict:** ❌ **Too expensive, vendor lock-in**

---

### Option 5: VictoriaMetrics

**Pros:**
- **Prometheus-compatible** (drop-in replacement)
- **Lower resource usage** than Prometheus
- Better long-term storage
- Faster queries on large datasets
- **Vendor neutral** and open-source
- Lower storage costs

**Cons:**
- Smaller community than Prometheus
- Less widely adopted
- Some advanced features in enterprise version
- Grafana integration needed separately

**Cost Considerations:**
- Software: $0 (open source core)
- Infrastructure: Low-Medium (more efficient than Prometheus)
- Operational: Medium

**Verdict:** ✅✅ **Good alternative to Prometheus for cost optimization**

---

### Option 6: Thanos (Prometheus Long-Term Storage)

**Pros:**
- **Extends Prometheus** with long-term storage
- **Vendor neutral** - uses object storage (S3-compatible)
- Multi-cluster monitoring
- Global query view
- Cost-effective long-term storage
- **Open source**

**Cons:**
- Additional complexity on top of Prometheus
- Requires object storage (S3, MinIO, etc.)
- Operational overhead

**Cost Considerations:**
- Software: $0 (open source)
- Infrastructure: Medium (Thanos components + object storage)
- Operational: Medium-High

**Verdict:** ✅ **Good for long-term retention needs**

---

## Evaluation Criteria

| Criterion | Weight | Prometheus + Grafana | Prometheus Operator | Cloud Monitoring | Datadog/New Relic | VictoriaMetrics | Thanos |
|-----------|--------|---------------------|---------------------|------------------|-------------------|-----------------|--------|
| Vendor Lock-in Avoidance | **High** | ✅✅✅ | ✅✅✅ | ❌ | ❌ | ✅✅✅ | ✅✅✅ |
| Cost Efficiency | **High** | ✅✅✅ | ✅✅✅ | ⚠️ | ❌ | ✅✅✅ | ✅✅ |
| Operational Simplicity | High | ⚠️ | ✅✅ | ✅✅✅ | ✅✅✅ | ⚠️ | ⚠️ |
| K8s Integration | High | ✅✅✅ | ✅✅✅ | ✅✅ | ✅✅ | ✅✅ | ✅✅✅ |
| Long-Term Storage | Medium | ⚠️ | ⚠️ | ✅✅ | ✅✅✅ | ✅✅ | ✅✅✅ |
| Community/Support | Medium | ✅✅✅ | ✅✅✅ | ✅✅ | ✅✅✅ | ✅✅ | ✅✅ |
| Customization | Medium | ✅✅✅ | ✅✅✅ | ⚠️ | ⚠️ | ✅✅ | ✅✅✅ |

Legend: ✅✅✅ Excellent | ✅✅ Good | ⚠️ Acceptable | ❌ Poor

## Log Aggregation

Monitoring stack should be combined with log aggregation. Options:

### Loki (with Grafana)
- **Pros**: Lightweight, integrates with Grafana, vendor-neutral, cost-effective
- **Cons**: Less feature-rich than ELK
- **Verdict**: ✅✅✅ Recommended for simplicity

### ELK Stack (Elasticsearch, Logstash, Kibana)
- **Pros**: Powerful, feature-rich, widely used
- **Cons**: Resource-intensive, complex, higher cost
- **Verdict**: ✅ Good but complex

### Cloud Logging (CloudWatch Logs, Azure Logs, GCP Logging)
- **Verdict**: ❌ Vendor lock-in

## Questions to Answer

1. **Operational Capacity**:
   - Can we maintain Prometheus/Grafana ourselves?
   - Or prefer fully managed solution?

2. **Budget**:
   - What is acceptable monthly monitoring cost?
   - Is $0 (self-hosted) vs. $500+ (SaaS) a factor?

3. **Long-Term Storage**:
   - How long should metrics be retained?
   - Is 15-30 days sufficient or need years?

4. **Scale**:
   - How many services/pods to monitor?
   - Expected metric volume?

5. **Compliance**:
   - Can metrics be sent to third-party SaaS?
   - Or must be self-hosted?

## Recommendation (Preliminary)

### For Initial Deployment:
**Prometheus Operator + Grafana + Loki**

**Rationale:**
- **Vendor neutral** - can run anywhere
- **Cost effective** - $0 licensing
- **Industry standard** - well-supported
- **Kubernetes-native** - excellent integration
- **Complete solution** - metrics + logs + dashboards
- **Operational** - manageable complexity with Operator

### Monitoring Stack Components:
- **Prometheus Operator**: Metrics collection
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notification
- **Loki**: Log aggregation
- **Promtail**: Log shipping to Loki

### Long-Term Enhancement (Optional):
- Add **Thanos** if long-term retention (>30 days) needed
- Or **VictoriaMetrics** if cost optimization critical

## Implementation Notes (Placeholder)

**TO BE COMPLETED AFTER DECISION**

### ServiceMonitor Example:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: django-app
  namespace: erechnung
spec:
  selector:
    matchLabels:
      app: django-app
  endpoints:
  - port: metrics
    interval: 30s
```

### Grafana Dashboard:
- Import community dashboards for Kubernetes
- Create custom dashboard for eRechnung business metrics
- Configure alerts for critical conditions

## Consequences

**TO BE DOCUMENTED AFTER DECISION**

## Related Decisions

- ADR-010: Kubernetes Orchestration (monitoring target)
- ADR-011: Ingress Controller (NGINX metrics)
- Cross-cutting concepts for observability (arc42/08)

## References

- [Prometheus](https://prometheus.io/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [Grafana](https://grafana.com/)
- [Loki](https://grafana.com/oss/loki/)
- [Thanos](https://thanos.io/)
- [VictoriaMetrics](https://victoriametrics.com/)
- [CNCF Observability](https://landscape.cncf.io/guide#observability-and-analysis--monitoring)

---

**Next Steps:**
1. Determine operational capacity for self-hosted solution
2. Assess budget constraints
3. Define retention requirements
4. Evaluate Prometheus Operator vs. managed monitoring
5. Document implementation plan
6. Set up dashboards and alerts
