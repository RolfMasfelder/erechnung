# ADR 012: Secrets Management Strategy

## Status

**Accepted** — 2026-04-30

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

**Sealed Secrets (Bitnami) als Default-Mechanismus für statische Geheimnisse im k3s-Deployment.**

Docker-Compose-Deployment behält unverändert `.env`-Dateien aus `secrets/` (Status quo, außerhalb des Git-Trees, durch Dateirechte geschützt).

### Begründung

1. **GitOps-Konsistenz mit ADR-014:** ArgoCD pulled Manifeste aus Git. Sealed Secrets ist die einzige Variante, bei der verschlüsselte Geheimnisse sauber im selben Git-Tree liegen können — kein paralleler Secret-Store nötig.
2. **Operativer Aufwand passt zur Projektgröße:** Single-Maintainer-Setup mit ~10 Geheimnissen. Vault-HA-Cluster (3 Pods + Storage + Unsealing) wäre unverhältnismäßig.
3. **Footprint:** Ein Controller-Pod genügt; minimaler CPU/Memory-Overhead.
4. **Audit/Compliance genügt:** Git-History dokumentiert sämtliche Änderungen an Geheimnissen. Inhaltliche Audit-Trails liegen ohnehin in Django (`AuditLog`) und am Gateway (nginx). GoBD-Anforderungen werden dadurch nicht berührt.
5. **Wachstumspfad bleibt offen:** Sealed Secrets blockiert spätere Ergänzungen nicht. Wenn Dynamic Secrets (kurzlebige DB-Credentials), Multi-Cluster oder externe Compliance-Audits erforderlich werden, kann **External Secrets Operator + OpenBao/Vault** zusätzlich eingeführt werden — beide Mechanismen koexistieren problemlos (statische Konfig via Sealed Secrets, dynamische Credentials via ESO).

### Verworfene Alternativen

- **HashiCorp Vault / OpenBao (alleinstehend):** Operativer Aufwand (HA, Unseal, Backup, Upgrades) für aktuellen Skalierungsgrad nicht gerechtfertigt. Lizenz-Wechsel von Vault auf BSL ist ein zusätzlicher Negativpunkt; OpenBao wäre die vendor-neutralere Wahl, falls später umgestellt wird.
- **External Secrets Operator (allein):** Synchronisiert nur — braucht zwingend einen Backend-Store (Vault/OpenBao oder Cloud-KMS). Ohne Cloud-Anschluss und ohne Vault am Ende doppelter Aufwand. Sinnvoll erst zusammen mit OpenBao in einer späteren Ausbaustufe.
- **Kubernetes Native Secrets + etcd-Encryption:** Keine Verschlüsselung im Git, kein einfaches GitOps-Workflow, kein Audit-Trail über Inhaltsänderungen. Wird intern weiterhin als Ziel-Datentyp verwendet (Sealed Secrets entschlüsselt zu nativen Secrets), aber nicht als primärer Verwaltungsmechanismus.

### Migration Path (falls später erforderlich)

1. **Heute (Phase 1):** Sealed Secrets für alle k3s-Geheimnisse.
2. **Trigger für Re-Evaluation:** Eines der folgenden Kriterien wird erfüllt:
   - Bedarf an Dynamic Secrets (kurzlebige DB-/PKI-Credentials)
   - Mehrere k3s-Cluster müssen synchron mit Geheimnissen versorgt werden
   - Externe Compliance-Audits verlangen zentralisiertes Secret-Audit-Log
3. **Phase 2 (bei Bedarf):** OpenBao + External Secrets Operator zusätzlich einführen; Sealed Secrets für die einfachen statischen Fälle behalten.

## Implementation Notes

### Komponenten

- **Controller:** `sealed-secrets-controller` im Namespace `kube-system` (oder `sealed-secrets`), an explizite Chart-Version gepinnt (kein `:latest`).
- **CLI:** `kubeseal` lokal beim Maintainer, gegen den Cluster-Public-Key des Controllers.
- **Workflow:**
  ```bash
  kubectl create secret generic mysecret --from-literal=key=value \
    --dry-run=client -o yaml \
    | kubeseal --controller-namespace kube-system -o yaml \
    > infra/k8s/k3s/secrets/mysecret.sealed.yaml
  git add infra/k8s/k3s/secrets/mysecret.sealed.yaml
  ```
- **Speicherort:** `infra/k8s/k3s/secrets/*.sealed.yaml` — wird von ArgoCD/Kustomize zusammen mit dem Rest deployt.

### Master-Key-Backup (sicherheitskritisch)

Der Cluster-Master-Key entschlüsselt **alle** Sealed Secrets. Verlust = alle Geheimnisse müssen neu generiert werden. Kompromittierung = alle Geheimnisse exponiert.

- Master-Key liegt im Cluster als Secret `sealed-secrets-key*` im Controller-Namespace.
- **Offline-Backup** des Keys verschlüsselt (GPG/age) auf separatem Medium.
- Schlüssel-Rotation halbjährlich (Sealed Secrets unterstützt mehrere aktive Schlüssel parallel — alte bleiben für Entschlüsselung gültig, neue werden für neue Versiegelungen verwendet).
- Restore-Prozedur in `docs/arc42/production-operations.md` dokumentieren.

### Access Control

- `kubeseal`-CLI benötigt nur Zugriff auf Cluster-Public-Key (über Service oder explizit gespeichert).
- RBAC am Controller-Pod beschränkt, wer Sealed Secrets erstellen/auslesen darf (Standard: ServiceAccount des Controllers selbst).
- Verschlüsselte `SealedSecret`-Manifeste sind unbedenklich im Git-Repo (auch in öffentlichen Forks, solange der Master-Key sicher ist).

### Integration mit ArgoCD (ADR-014)

- ArgoCD synchronisiert `SealedSecret`-CRDs ins Cluster.
- Sealed-Secrets-Controller entschlüsselt sie zu nativen `Secret`-Objekten.
- Pods mounten/lesen die nativen Secrets unverändert.
- Kein zusätzliches Tooling im ArgoCD selbst nötig.

### Docker-Compose-Deployment

- Außerhalb des Scopes dieses ADRs: bleibt bei `.env`-Dateien aus `secrets/`, geschützt durch Dateirechte (`chmod 600`).
- Konsistenz mit k3s erfolgt logisch (gleiche Secret-Namen / -Werte), nicht technisch.

## Consequences

### Positive

- Geheimnisse leben im Git zusammen mit dem übrigen Cluster-State — GitOps-konform mit ADR-014.
- Sehr geringer Operations-Overhead: ein Controller-Pod, ein CLI.
- Backup fällt automatisch mit Git-Backup ab; zusätzlich nur Master-Key offline sichern.
- Wachstumspfad zu OpenBao/ESO bleibt offen, ohne dass aktuelle Investitionen verloren gehen.
- Vendor-neutral: läuft auf jedem Kubernetes ohne Cloud-Bindung.

### Negative / Risiken

- **Keine Dynamic Secrets** — alle Geheimnisse sind statisch, Rotation ist manuell (Re-Seal + Git-Commit).
- **Master-Key ist Single Point of Failure:** Verlust oder Kompromittierung wirkt clusterweit. Mitigation über Offline-Backup + halbjährliche Rotation.
- **Audit-Tiefe begrenzt:** Wer wann welches Geheimnis im Cluster gelesen hat, ist nicht nachvollziehbar (Sealed Secrets entschlüsselt einmalig zum nativen Secret, dann gilt K8s-RBAC). Für aktuelle Anforderungen ausreichend, für externe Compliance-Audits ggf. nicht.
- **Cluster-Bindung:** Sealed Secrets aus Cluster A können nicht in Cluster B entschlüsselt werden (außer durch expliziten Master-Key-Transfer). Bei Multi-Cluster müsste pro Cluster re-sealed werden.

### Mitigationen

- Master-Key-Backup-Prozedur dokumentieren und vierteljihrlich testen (Restore in einem Sandbox-Cluster).
- Sealed-Secrets-Controller-Version explizit pinnen.
- Für besonders sensible Geheimnisse (z. B. JWT-Signing-Key) zusätzlich `git crypt` oder externe Verwahrung erwägen.

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
1. Sealed-Secrets-Controller-Version pinnen und Manifest unter `infra/k8s/k3s/sealed-secrets/` ablegen.
2. Bestehende `Secret`-Ressourcen migrieren: pro Secret `kubeseal` ausführen, Ergebnis nach `infra/k8s/k3s/secrets/*.sealed.yaml` einchecken, alten Klartext entfernen.
3. Master-Key-Backup-Prozedur dokumentieren in `docs/arc42/production-operations.md` (inkl. Restore-Test).
4. README in `infra/k8s/k3s/secrets/` mit `kubeseal`-Workflow ergänzen.
5. Re-Evaluation-Trigger explizit in TODO/Roadmap aufnehmen (Dynamic Secrets / Multi-Cluster / externe Audits).
