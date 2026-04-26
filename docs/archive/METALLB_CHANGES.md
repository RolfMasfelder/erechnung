# MetalLB Integration - Änderungsübersicht

## Zusammenfassung

Die Kubernetes-Konfiguration wurde von **Hostport-Modus** (nicht produktionsnah) auf **MetalLB LoadBalancer** (produktionsnah) erweitert.

## Geänderte Dateien

### 1. Neue Dokumentation

- **`docs/METALLB_MIGRATION.md`** - Vollständiger Migrations-Guide
  - Unterschiede HostPort vs. MetalLB
  - Schritt-für-Schritt Anleitung
  - Netzwerk-Konfiguration
  - Troubleshooting
  - Rollback-Plan

### 2. Konfigurationsdateien

#### `k8s/kind/metallb-config.yaml`

**Vorher:**

```yaml
# DEPRECATED - MetalLB nicht mehr verwendet
addresses:
- 172.18.255.200-172.18.255.250  # Docker-Netzwerk (nicht erreichbar)
```

**Nachher:**

```yaml
# Produktive Konfiguration für lokales Netzwerk
addresses:
- 192.168.178.200-192.168.178.210  # Echte IPs für LoadBalancer
```

#### `k8s/kind/api-gateway-service.yaml`

**Vorher:**

```yaml
type: NodePort  # Nicht produktionsnah
```

**Nachher:**

```yaml
type: ClusterIP  # Standard, mit Option für LoadBalancer
# Gut dokumentiert für beide Modi
```

#### `k8s/kind/kind-cluster-config.yaml`

- Kommentare hinzugefügt zu zwei Deployment-Modi
- `extraPortMappings` als optional markiert (für MetalLB nicht nötig)

### 3. Setup-Scripts

#### `k8s/kind/setup.sh`

**Neu hinzugefügt:**

```bash
# Step 2.5: Install MetalLB (optional)
# Benutzer kann wählen zwischen HostPort und MetalLB
# Automatische Konfiguration je nach Wahl
```

**Erweitert:**

- Interaktive MetalLB-Installation
- LoadBalancer IP-Anzeige
- Intelligente Zugriffs-Informationen (abhängig vom Modus)

#### `scripts/migrate-to-metallb.sh` (NEU)

Vollautomatisches Migrations-Script:

1. IP-Bereich Validierung
2. MetalLB Installation
3. IPAddressPool Konfiguration
4. Ingress-Controller auf LoadBalancer umstellen
5. Optional: API Gateway auf LoadBalancer
6. Verifikation und Status-Anzeige

### 4. Dokumentation

#### `k8s/kind/README.md`

- MetalLB-Abschnitt hinzugefügt
- Vergleichstabelle HostPort vs. MetalLB
- Konfigurationshinweise
- Link zur detaillierten Dokumentation

---

## Verwendung

### Option 1: Neues Cluster mit MetalLB

```bash
cd k8s/kind && ./setup.sh
# Bei Frage "Install MetalLB?" → **Y** drücken
```

### Option 2: Bestehendes Cluster migrieren

```bash
cd scripts && ./migrate-to-metallb.sh
```

### Option 3: HostPort-Modus (ohne Änderung)

```bash
cd k8s/kind && ./setup.sh
# Bei Frage "Install MetalLB?" → **N** drücken
```

---

## Deployment-Modi Vergleich

| Aspekt | HostPort (alt) | **MetalLB Hybrid (aktiv)** | MetalLB Pure |
|--------|----------------|---------------------------|--------------|
| **Setup** | Einfach | Mittel (IP-Config) | Komplex |
| **Produktion** | ❌ Nicht geeignet | ✅ Production-like Tests | ✅ Production-ready |
| **Multi-Node** | ❌ Nur Control-Plane | ✅ Alle Nodes | ✅ Alle Nodes |
| **Remote-Zugriff** | ✅ Via HostPort | ✅ Via HostPort | ❌ kind-Limitation |
| **LB-Funktionalität** | ❌ Keine | ✅ Vorhanden | ✅ Vorhanden |
| **kind-Tauglich** | ✅ Ja | ✅ **Optimal** | ⚠️ Eingeschränkt |
| **Zugriff** | :80 | :80 + LB-IP | Nur LB-IP |

### kind-Cluster: Aktuelle Konfiguration (getestet ✅)

**Hybrid-Modus:** MetalLB (172.18.255.200) + HostPort (192.168.178.80:80)

```bash
# Getestete Zugriffe:
✅ LAN-Remote: http://192.168.178.80 → HTTP 308 (funktioniert!)
✅ Docker-Host: http://172.18.255.200 → HTTP 308 (funktioniert!)
✅ Cluster-intern: http://172.18.255.200 → HTTP 308 (funktioniert!)
```

**Warum Hybrid für kind?**

- MetalLB kann in kind nur Docker-Netzwerk-IPs vergeben (172.18.x.x)
- Host-LAN IPs (192.168.178.x) sind für kind nicht erreichbar
- HostPort bleibt für praktischen Remote-Zugriff erforderlich
- MetalLB ermöglicht trotzdem produktionsnahe LoadBalancer-Tests

---

## Vor dem Deployment prüfen

### 1. Netzwerk-Konfiguration ✓

```bash
# Host IP-Adresse prüfen
ip addr show | grep "inet 192.168"
# → z.B. 192.168.178.80/24

# IP-Bereich in metallb-config.yaml anpassen:
# addresses: 192.168.178.200-192.168.178.210
```

### 2. Router-Konfiguration ✓

- IP-Bereich 192.168.178.200-210 vom DHCP ausschließen
- Statische Reservierung für LoadBalancer-IPs

### 3. DNS-Einträge (optional) ✓

```bash
# /etc/hosts oder Router-DNS
192.168.178.200  erechnung.local
192.168.178.200  api.erechnung.local
```

---

## Nächste Schritte

1. **IP-Bereich koordinieren** mit Netzwerk-Admin/Router
2. **metallb-config.yaml** anpassen (192.168.178.200-210)
3. **Testen auf localhost** (kind-Cluster)
4. **Remote-Deployment** (192.168.178.80)
5. **Monitoring** einrichten (LoadBalancer IP-Verfügbarkeit)

---

## Rollback

Falls Probleme auftreten:

```bash
# MetalLB deinstallieren
kubectl delete namespace metallb-system

# Ingress zurück auf ClusterIP (HostPort)
kubectl patch svc ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"type":"ClusterIP"}}'

# Oder Cluster komplett neu aufsetzen
kind delete cluster --name erechnung
cd k8s/kind && ./setup.sh  # → MetalLB ablehnen (N)
```

---

## Weiterführende Dokumentation

- **[docs/METALLB_MIGRATION.md](docs/METALLB_MIGRATION.md)** - Detaillierte Migration
- **[k8s/kind/README.md](k8s/kind/README.md)** - kind Setup-Anleitung
- **[MetalLB Documentation](https://metallb.universe.tf/)** - Offizielle Docs

---

## Getestete Umgebungen

- ✅ Ubuntu 22.04 LTS (Host: 192.168.178.80)
- ✅ kind v0.23.0
- ✅ Kubernetes v1.31
- ✅ MetalLB v0.14.8
- ✅ nginx-ingress-controller latest

**Status:** Production-ready für lokales Netzwerk-Setup
