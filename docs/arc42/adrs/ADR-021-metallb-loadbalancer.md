# ADR 021: MetalLB for Kubernetes LoadBalancer Services

## Status

Accepted (January 2026)

## Date

2026-01-29

## Context

With Kubernetes deployment (ADR-010), we encountered a fundamental limitation: **kind (Kubernetes in Docker) does not provide a LoadBalancer implementation**. This causes all LoadBalancer-type Services to remain in `<pending>` state indefinitely.

### Problem

```bash
$ kubectl get svc -n ingress-nginx
NAME                    TYPE           EXTERNAL-IP   PORT(S)
ingress-nginx           LoadBalancer   <pending>     80:30080/TCP,443:30443/TCP
```

**Consequence:** Ingress Controller unreachable from outside the cluster, no external IP assigned.

### Requirements

1. **LoadBalancer Support**: Assign external IPs to LoadBalancer Services
2. **kind Compatibility**: Work with kind's Docker network architecture
3. **Layer 2 Mode**: Simple ARP-based load balancing for local networks
4. **No Cloud Provider**: Must work on bare-metal/local development
5. **Easy Setup**: Simple installation and configuration
6. **Production-Ready**: Used in real production environments

## Decision

**We deploy MetalLB v0.14.9 in Layer 2 mode to provide LoadBalancer functionality for the kind Kubernetes cluster.**

### Architecture

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│                     kind Docker Network (172.18.0.0/16)                     │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Kubernetes Cluster                               │  │
│  │                                                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    MetalLB Components                          │  │  │
│  │  │                                                                │  │  │
│  │  │  ┌──────────────────┐     ┌──────────────────────────────┐    │  │  │
│  │  │  │ Controller       │     │ Speaker (DaemonSet)          │    │  │  │
│  │  │  │ (Deployment)     │     │ - Runs on all 3 nodes        │    │  │  │
│  │  │  │                  │     │ - Announces IPs via ARP      │    │  │  │
│  │  │  │ - Watches Svcs   │     │ - Responds to ARP requests   │    │  │  │
│  │  │  │ - Assigns IPs    │     │                              │    │  │  │
│  │  │  └──────────────────┘     └──────────────────────────────┘    │  │  │
│  │  │                                                                │  │  │
│  │  │  ┌──────────────────────────────────────────────────────────┐ │  │  │
│  │  │  │ IPAddressPool: 172.18.255.200 - 172.18.255.250          │ │  │  │
│  │  │  │ L2Advertisement: Announce IPs on kind network            │ │  │  │
│  │  │  └──────────────────────────────────────────────────────────┘ │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │ Ingress Controller Service (LoadBalancer)                      │  │  │
│  │  │ EXTERNAL-IP: 172.18.255.200 (from MetalLB pool)               │  │  │
│  │  │ Ports: 80/TCP, 443/TCP                                        │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Host Network Stack                            │  │
│  │                                                                       │  │
│  │  ARP Table: 172.18.255.200 -> MAC address of kind node               │  │
│  │  Route: 172.18.255.200/32 via kind bridge                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                          curl https://172.18.255.200/
```

## Implementation

### MetalLB Installation

**Manifest:** `k8s/kind/metallb-native.yaml` (v0.14.9)

```bash
# Apply MetalLB manifest
kubectl apply -f k8s/kind/metallb-native.yaml

# Wait for MetalLB to be ready
kubectl wait --namespace metallb-system \
  --for=condition=ready pod \
  --selector=app=metallb \
  --timeout=90s
```

**Components:**

- **Controller**: 1 Deployment (assigns IPs to Services)
- **Speaker**: 3 DaemonSet pods (1 per node, announces IPs via ARP)

### IP Address Pool Configuration

**File:** `k8s/kind/metallb-config.yaml`

```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: erechnung-pool
  namespace: metallb-system
spec:
  addresses:
  - 172.18.255.200-172.18.255.250  # 51 IPs in kind Docker network range
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: erechnung-l2
  namespace: metallb-system
spec:
  ipAddressPools:
  - erechnung-pool
```

**Rationale for IP Range:**

- kind Docker network: `172.18.0.0/16`
- High range (255.x) avoids conflicts with container IPs
- 51 IPs sufficient for multiple LoadBalancer Services

### Ingress Controller Integration

**Before MetalLB:**

```bash
$ kubectl get svc ingress-nginx -n ingress-nginx
NAME             TYPE           EXTERNAL-IP   PORT(S)
ingress-nginx    LoadBalancer   <pending>     80:30080/TCP,443:30443/TCP
```

**After MetalLB:**

```bash
$ kubectl get svc ingress-nginx -n ingress-nginx
NAME             TYPE           EXTERNAL-IP       PORT(S)
ingress-nginx    LoadBalancer   172.18.255.200    80:30080/TCP,443:30443/TCP
```

**Application Access:**

```bash
# From host machine
curl -k https://172.18.255.200/
# → Returns Vue.js frontend

# From Kubernetes host (192.168.178.80)
ssh rolf@192.168.178.80 "curl -k https://172.18.255.200/"
# → Returns Vue.js frontend
```

## Rationale

### Why MetalLB?

**1. Production-Grade LoadBalancer:**

- Used in thousands of production bare-metal clusters
- CNCF Sandbox project with active development
- Supported by Kubernetes SIG-Network

**2. Layer 2 Mode Simplicity:**

- No BGP configuration required
- Works on any network topology
- Standard ARP/NDP for IP announcement
- Perfect for development and small clusters

**3. kind Compatibility:**

- Designed for bare-metal/non-cloud environments
- Works perfectly with kind's Docker network
- No special kind patches required

**4. Zero External Dependencies:**

- No cloud provider APIs
- No external routing infrastructure
- Self-contained solution

### How Layer 2 Mode Works

1. **Service Creation:** User creates LoadBalancer Service
2. **IP Assignment:** MetalLB Controller assigns IP from pool
3. **ARP Announcement:** MetalLB Speaker broadcasts ARP reply for assigned IP
4. **Traffic Routing:** Host routes packets to Speaker node's MAC address
5. **Forwarding:** kube-proxy forwards traffic to Service endpoints

**Key Insight:** MetalLB Speaker makes the Kubernetes node "own" the LoadBalancer IP via ARP, allowing external traffic to reach the cluster.

### Why Not NodePort?

**NodePort Limitations:**

- Requires knowledge of specific node IPs
- High port numbers (30000-32767) confusing for users
- No automatic load balancing across nodes
- Not production-like (LoadBalancers standard in cloud)

### Why Not Port-Forwarding?

**kubectl port-forward Limitations:**

- Requires active kubectl session
- Single connection (no load balancing)
- Not suitable for CI/CD or automated testing
- Debugging tool, not deployment solution

### Why Not Custom Service LoadBalancer?

**Custom Solution:**

- Reinventing the wheel
- No community support
- Maintenance burden
- MetalLB already solves this perfectly

## Layer 2 vs BGP Mode

### Layer 2 Mode (Chosen)

**Pros:**

- ✅ Simple setup (no BGP configuration)
- ✅ Works on any network
- ✅ No router configuration required
- ✅ Perfect for single-network deployments

**Cons:**

- ⚠️ No true load balancing (one node handles all traffic)
- ⚠️ Single point of failure (if node goes down, failover takes seconds)
- ⚠️ Limited to single L2 network segment

### BGP Mode (Not Used)

**Pros:**

- ✅ True load balancing across multiple nodes
- ✅ Fast failover (<1 second)
- ✅ Works across L3 networks

**Cons:**

- ❌ Requires BGP-capable router
- ❌ Complex configuration
- ❌ Overkill for development/small deployments

**Decision:** Layer 2 mode sufficient for kind development and small production clusters.

## Consequences

### Positive

- ✅ **LoadBalancer Services Work:** External IPs assigned automatically
- ✅ **Ingress Accessible:** Ingress Controller reachable from host/network
- ✅ **Production-Like:** Same Service type as cloud LoadBalancers
- ✅ **Simple Setup:** Single YAML manifest, no complex configuration
- ✅ **No External Dependencies:** Works offline, no cloud APIs
- ✅ **Kubernetes-Native:** Standard LoadBalancer API, works with any Service

### Negative

- ⚠️ **Single Node Traffic:** All traffic goes through one node (Layer 2 limitation)
- ⚠️ **Failover Lag:** ~10 seconds if node fails (ARP cache timeout)
- ⚠️ **L2 Network Only:** Cannot span multiple network segments

### Neutral

- **IP Pool Management:** Must define IP range manually (not automatic)
- **Port Conflicts:** Multiple LoadBalancers need multiple IPs (have 51 IPs available)

## Alternatives Considered

### 1. kind with ingress Workaround

**Approach:** Manually map ports in kind config + NodePort Services

**Rejected:**

- Requires kind cluster recreation
- Limited to 2-3 Services (port collision risk)
- Not scalable

### 2. Cloud LoadBalancer Simulation (MetalLB)

**Approach:** Use MetalLB to simulate cloud LoadBalancers

**Accepted:** This is our decision ✅

### 3. External LoadBalancer (HAProxy, nginx)

**Approach:** Run external HAProxy/nginx as LoadBalancer

**Rejected:**

- Requires external infrastructure
- Manual configuration for each Service
- Not Kubernetes-native

### 4. Use NodePort Only

**Approach:** NodePort Services with documentation of port numbers

**Rejected:**

- Poor user experience (high port numbers)
- Not production-like
- No automatic load balancing

## Verification

### MetalLB Status

```bash
$ kubectl get pods -n metallb-system
NAME                          READY   STATUS    AGE
controller-5f9d4f7c4-xyz      1/1     Running   10m
speaker-abc                   1/1     Running   10m
speaker-def                   1/1     Running   10m
speaker-ghi                   1/1     Running   10m
```

### LoadBalancer Service Test

```bash
$ kubectl get svc -A --field-selector spec.type=LoadBalancer
NAMESPACE       NAME                TYPE           EXTERNAL-IP       PORT(S)
ingress-nginx   ingress-nginx       LoadBalancer   172.18.255.200    80:30080/TCP,443:30443/TCP
```

### Connectivity Test

```bash
$ curl -k -H 'Host: api.erechnung.local' https://172.18.255.200/ | head -5
<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
```

## Related Decisions

- ADR-010: Kubernetes Orchestration (requires LoadBalancer solution)
- ADR-011: Ingress Controller Selection (uses LoadBalancer Service)
- ADR-020: Local HTTPS Registry (Kubernetes infrastructure)
- ADR-022: Calico CNI Provider (Kubernetes networking)

## References

- MetalLB Documentation: <https://metallb.universe.tf/>
- MetalLB Layer 2 Mode: <https://metallb.universe.tf/concepts/layer2/>
- kind LoadBalancer Guide: <https://kind.sigs.k8s.io/docs/user/loadbalancer/>
- MetalLB GitHub: <https://github.com/metallb/metallb>
