# ADR 011: Ingress Controller Selection

## Status

Accepted

## Context

Kubernetes requires an Ingress Controller to manage external access to services within the cluster. The Ingress Controller is responsible for:
- HTTP/HTTPS routing and load balancing
- SSL/TLS termination
- Path-based and host-based routing
- Integration with certificate management (cert-manager)
- Rate limiting and security features
- WebSocket support (for future features)

For the eRechnung system, the Ingress Controller must support:
- High availability and performance
- Easy integration with certificate management
- Vendor-neutral approach (avoid cloud lock-in)
- Cost-effective solution (preferably open-source)
- Good documentation and community support
- ZUGFeRD PDF downloads (potentially large files)

## Decision

We will use **NGINX Ingress Controller** as the primary Ingress solution for the eRechnung Kubernetes deployment.

Specifically, we will use the community-maintained **ingress-nginx** (https://github.com/kubernetes/ingress-nginx), not the NGINX Inc. commercial version.

## Rationale

### Why NGINX Ingress Controller?

1. **Vendor Neutrality**:
   - Open-source and community-driven
   - Works on any Kubernetes platform (on-premises, AWS, Azure, GCP)
   - No vendor lock-in to specific cloud providers
   - Can be migrated between infrastructure providers

2. **Cost-Effective**:
   - Completely free and open-source (Apache 2.0 license)
   - No licensing costs regardless of scale
   - Minimal resource overhead compared to service mesh solutions

3. **Maturity and Stability**:
   - One of the oldest and most battle-tested Ingress controllers
   - Used by millions of Kubernetes deployments worldwide
   - Well-understood behavior and troubleshooting

4. **Feature Completeness**:
   - Full HTTP/HTTPS support with SNI
   - WebSocket and gRPC support
   - Rate limiting and throttling
   - Authentication (Basic Auth, OAuth, etc.)
   - Custom error pages
   - URL rewriting and redirects
   - Supports large file uploads/downloads (important for PDF generation)

5. **Certificate Management Integration**:
   - Seamless integration with cert-manager
   - Automatic SSL/TLS certificate provisioning
   - Let's Encrypt support out of the box

6. **Performance**:
   - Efficient request handling with minimal latency
   - Connection pooling and keep-alive
   - Configurable buffer sizes for large files

7. **Community and Documentation**:
   - Extensive documentation and examples
   - Large community with active support
   - Regular security updates and bug fixes
   - Kubernetes official project (part of kubernetes/ingress-nginx)

8. **Flexibility**:
   - Extensive configuration via annotations
   - ConfigMap-based global configuration
   - Support for custom NGINX configurations when needed

## Configuration Strategy

### Basic Setup
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: erechnung-ingress
  namespace: erechnung
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"  # For large PDF uploads
spec:
  tls:
  - hosts:
    - api.erechnung.example.com
    secretName: erechnung-tls
  rules:
  - host: api.erechnung.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: django-app
            port:
              number: 8000
```

### Key Configuration Aspects
- **SSL/TLS**: Automatic certificate management via cert-manager
- **File Size Limits**: Configured for large PDF downloads (up to 50MB)
- **Rate Limiting**: Can be enabled per endpoint via annotations
- **Timeouts**: Adjusted for long-running PDF generation requests

## Consequences

### Positive

- **No Vendor Lock-in**: Can run on any Kubernetes distribution
- **Zero Licensing Costs**: Completely free to use at any scale
- **Proven Reliability**: Battle-tested in production environments worldwide
- **Easy Migration**: Standard Ingress resources work across providers
- **Strong Ecosystem**: Rich set of integrations and tools
- **Performance**: Efficient and performant for our use case
- **Familiarity**: NGINX is well-known by operations teams

### Negative

- **Limited Advanced Features**: Less sophisticated than service mesh solutions (Istio, Linkerd)
  - *Mitigation*: Service mesh can be added later if needed (see ADR-013)
- **Configuration Complexity**: Some advanced features require NGINX-specific knowledge
  - *Mitigation*: Good documentation available, start with simple configurations
- **No Built-in Service Mesh Features**: No automatic mTLS between services
  - *Mitigation*: Can be addressed separately with service mesh if required

### Neutral

- **Annotations-based Configuration**: Heavy use of annotations for configuration
  - *Note*: This is the Kubernetes-native approach, consistent with ecosystem

## Alternatives Considered

### Traefik
- **Pros**: Modern, dynamic configuration, good UI, built-in Let's Encrypt
- **Cons**: Higher resource usage, less mature than NGINX, smaller community
- **Decision**: Rejected due to higher complexity and resource overhead

### HAProxy Ingress
- **Pros**: Very high performance, advanced load balancing features
- **Cons**: Smaller community, more complex configuration, less common
- **Decision**: Rejected due to smaller ecosystem and less widespread adoption

### Cloud Provider Load Balancers (AWS ALB, Azure Application Gateway, GCP Load Balancer)
- **Pros**: Fully managed, cloud-native integration, good performance
- **Cons**: **Vendor lock-in**, costs can scale significantly, migration difficulty
- **Decision**: **Rejected to avoid vendor lock-in** - primary concern for eRechnung

### Istio/Envoy Gateway
- **Pros**: Advanced traffic management, service mesh integration, modern
- **Cons**: High complexity, significant resource overhead, steep learning curve
- **Decision**: Rejected for initial deployment, can be added later (see ADR-013)

### Kong Ingress Controller
- **Pros**: API gateway features, plugin ecosystem, good for API management
- **Cons**: Commercial features behind paywall, heavier than needed
- **Decision**: Rejected due to commercial aspects and complexity

## Migration Path

If future requirements necessitate a change:

1. **To Service Mesh** (Istio/Linkerd): Can be added on top of NGINX Ingress
2. **To Different Ingress**: Standard Kubernetes Ingress resources are portable
3. **To API Gateway**: Kong or similar can be added in front of NGINX

## Implementation Notes

### High Availability
- Deploy NGINX Ingress Controller with multiple replicas (min 2, recommended 3)
- Use anti-affinity to spread pods across nodes
- Configure health checks and readiness probes

### Monitoring
- Prometheus metrics endpoint available by default
- Integration with Grafana for dashboards
- Alert on high error rates, latency, certificate expiration

### Security
- Regular updates via automated image scanning
- TLS 1.2+ only (TLS 1.3 preferred)
- Strong cipher suites configuration
- Rate limiting to prevent abuse

## Cost Considerations

| Aspect | Cost |
|--------|------|
| Software License | $0 (Open Source) |
| Cloud Load Balancer | Minimal (single LB for Ingress) |
| Compute Resources | Low (2-3 small pods) |
| Maintenance | Moderate (community support, documentation) |
| **Total Ongoing Cost** | **Very Low** |

**vs. Cloud-Native Alternatives:**
- AWS ALB: ~$22/month + $0.008 per LCU-hour (~$50-200/month at scale)
- Azure Application Gateway: ~$125/month + data processing fees
- GCP Load Balancer: ~$18/month + forwarding rules + traffic fees

**Savings**: ~$50-200/month with NGINX vs. managed cloud solutions

## Related Decisions

- ADR-010: Kubernetes Orchestration (provides the platform)
- ADR-012: Secrets Management Strategy (certificate storage)
- ADR-013: Service Mesh Decision (potential future enhancement)

## References

- [NGINX Ingress Controller Documentation](https://kubernetes.github.io/ingress-nginx/)
- [Kubernetes Ingress Specification](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [cert-manager Integration](https://cert-manager.io/docs/usage/ingress/)
- [NGINX Ingress Performance Tuning](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/)
