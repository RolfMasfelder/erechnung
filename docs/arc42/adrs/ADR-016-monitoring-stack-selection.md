# ADR 016: Monitoring Stack Selection

## Status

**Accepted** — 2026-04-30

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

**Plain Prometheus + Grafana + Loki + Promtail + Alertmanager + kube-state-metrics**, self-hosted in beiden Deployments (Docker Compose `docker-compose.monitoring.yml` und k3s `infra/k8s/k3s/manifests/9*`). Alle Images mit explizit gepinnten Versionen (z. B. `prom/prometheus:v3.11.1`, `grafana/grafana:12.4.2`).

Kein Prometheus Operator: Für eine Single-Cluster-/Single-Namespace-Topologie überwiegt die zusätzliche CRD- und Operator-Komplexität den Nutzen. Service-Discovery erfolgt über statische Targets bzw. Kubernetes-SD ohne `ServiceMonitor`-CRDs.

Kein Thanos / VictoriaMetrics: Vorerst genügen kurze Retention-Zeiten (Prometheus 15 Tage, Loki 30 Tage). Re-Evaluation, sobald entweder >30 Tage Metric-Retention oder Multi-Cluster-Föderation gefordert sind.

Alerting via Alertmanager → SMTP über die bereits konfigurierte IONOS-Mailbox (`EMAIL_HOST=smtp.ionos.de`, `EMAIL_HOST_USER=github@nector-it-gmbh.de`, vgl. ADR-012 / `secrets/`-Strategie). Damit ist die im April 2026 fertiggestellte E-Mail-Infrastruktur (§3.5) auch der Notification-Kanal für operative Alerts — kein zusätzlicher Slack/PagerDuty-Account nötig. Routing/Severity über Alertmanager-Routes; Empfänger für initial: Operator-Mailbox.

Distributed Tracing (OpenTelemetry/Jaeger) ist explizit **nicht** Teil dieses ADR und wird unter §3.1 (Security Phase 3+4) separat verfolgt.

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

## Selected Stack

| Component | Image / Version | Rolle |
|---|---|---|
| Prometheus | `prom/prometheus:v3.11.1` | Metrik-Scraping, TSDB, Recording/Alert-Rules |
| Grafana | `grafana/grafana:12.4.2` | Dashboards (eRechnung-Overview als Default-Home) |
| Loki | `grafana/loki` (gepinnte Version) | Log-Aggregation |
| Promtail | `grafana/promtail` (gepinnte Version) | Log-Shipping zu Loki |
| Alertmanager | `prom/alertmanager` (gepinnte Version) | Alert-Routing → SMTP/IONOS |
| kube-state-metrics | gepinnte Version | k8s-Cluster-Metriken |
| redis-exporter | gepinnte Version | Redis-Metriken (Docker-Compose) |

## Implementation Notes

- **Konfiguration**: `infra/monitoring/prometheus/prometheus.yml`, `alert_rules.yml`, `infra/monitoring/grafana/{provisioning,dashboards}/`.
- **k3s-Manifeste**: `infra/k8s/k3s/manifests/9*-*.yaml` (Namespace `monitoring`, PodSecurity `privileged` wegen Promtail-Hostmount).
- **Network Policies**: `infra/k8s/k3s/policies/monitoring-network-policies.yaml` regeln Ingress/Egress zwischen Prometheus, Grafana, Loki, Promtail und der Anwendungs-Namespace.
- **Retention**: Prometheus `--storage.tsdb.retention.time=15d`, Loki retention 30d (jeweils im Konfig-File überprüfen/anpassen).
- **Alerting via SMTP**: Alertmanager nutzt dieselben SMTP-Credentials wie der Rechnungs-E-Mail-Versand (IONOS, ADR-012-konform aus Sealed Secrets bzw. `.env`).
  ```yaml
  # alertmanager.yml (Auszug)
  global:
    smtp_smarthost: smtp.ionos.de:587
    smtp_from: github@nector-it-gmbh.de
    smtp_auth_username: github@nector-it-gmbh.de
    smtp_auth_password_file: /etc/alertmanager/secrets/smtp_password
    smtp_require_tls: true
  route:
    receiver: ops-mail
    group_by: ['alertname', 'severity']
    repeat_interval: 4h
  receivers:
    - name: ops-mail
      email_configs:
        - to: ops@nector-it-gmbh.de
  ```
- **Custom Business-Metriken**: via `django-prometheus` und eigener Counter/Histograms im Backend (siehe §2.1 / `PROGRESS_PROTOCOL.md` 04.03.2026).
- **GitOps**: Deployment via `kubectl apply -k infra/k8s/k3s/`; mittelfristig durch ArgoCD übernommen (ADR-014).

## Verworfene Alternativen

- **Prometheus Operator** — zu viel Operator-/CRD-Overhead für Single-Cluster.
- **Cloud-Native Monitoring** (CloudWatch/Azure Monitor/GCP) — Vendor-Lock-in, kein Cloud-Provider im Einsatz.
- **Datadog / New Relic** — Kosten und Datenabfluss zu Drittanbieter (DSGVO/GoBD-relevant).
- **VictoriaMetrics** — kein hinreichender Vorteil bei aktueller Datenmenge; Re-Eval bei Skalierung.
- **Thanos** — keine Multi-Cluster- oder Long-Term-Retention-Anforderung; Re-Eval >30 Tage Retention.
- **ELK** — zu ressourcenintensiv für Single-Node-k3s; Loki deckt Use Cases ab.

## Consequences

**Positive:**
- Vollständig vendor-neutral, lizenzkostenfrei.
- Ein einheitlicher Stack in beiden Deployments (Docker Compose Dev + k3s Prod-like) — kein doppeltes Mental Model.
- Notification-Pfad nutzt bereits getestete SMTP-Strecke (E-Mail-Versand seit 2026-04-29 live, IONOS-bestätigt) — keine Zusatzabhängigkeit.
- Custom Business-Metriken integriert, kube-state-metrics liefert Cluster-Sicht.

**Negative / Trade-offs:**
- Manuelle Maintenance (Image-Updates, Dashboard-Pflege, Alert-Rule-Tuning) — keine Operator-Automation.
- Begrenzte Retention (15 d Metrics, 30 d Logs); historische Auswertungen >30 Tage erfordern Re-Eval (Thanos/VictoriaMetrics).
- Single-Instance-Deployment ohne HA — bei Cluster-Ausfall sind Monitoring-Daten kurzzeitig unverfügbar (für aktuellen Single-Node-Betrieb akzeptabel).
- SMTP-Alerting hängt an einer einzigen Mailbox; bei IONOS-Ausfall keine Notification — Mitigation: zusätzlich Heartbeat-Alert über externen Watchdog (Backlog).

**Re-Evaluation-Trigger:**
- Retention-Anforderung >30 Tage → Thanos oder VictoriaMetrics evaluieren.
- Multi-Cluster oder >5 Services mit Custom Metrics → Prometheus Operator evaluieren.
- Zweiter Notification-Kanal nötig (SMS/Webhook) → Alertmanager-Receiver erweitern.

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
1. Alertmanager-Deployment im k3s ergänzen (`infra/k8s/k3s/manifests/9X-alertmanager.yaml`) mit SMTP-Config aus Sealed Secret.
2. Alertmanager-`smtp_password`-Sealed-Secret erzeugen und in Kustomize einhängen (ADR-012-Pattern).
3. Recording Rules + SLO-Dashboards (Request-Latency, Error-Rate, Invoice-Throughput) ergänzen.
4. Runbook-Links als `annotations.runbook_url` in `alert_rules.yml` einpflegen.
5. End-to-End-Test der Alertkette: künstlicher Alert → Alertmanager → IONOS SMTP → Inbox.
