# GoBD Compliance Implementation Plan

## Übersicht

**GoBD** (Grundsätze zur ordnungsmäßigen Führung und Aufbewahrung von Büchern, Aufzeichnungen und Unterlagen in elektronischer Form sowie zum Datenzugriff) sind die deutschen Anforderungen an die digitale Buchführung.

Dieses Dokument beschreibt den Implementation Plan für die vollständige GoBD-Konformität der eRechnung Django App.

**Erstellt:** 3. Dezember 2025
**Branch:** `feature/gobd-compliance`
**Fortschritts-Protokoll:** [GOBD_PROTOCOL.md](./GOBD_PROTOCOL.md)

---

## Aktueller Stand

### ✅ Bereits implementiert

| Komponente | Status | Details |
|------------|--------|---------|
| AuditLog-Model | ✅ | Compliance-relevante Events markiert (`is_compliance_relevant`) |
| Retention-Policy | ✅ | 10-Jahre für compliance-relevante Einträge |
| Audit-Trail Unveränderbarkeit | ✅ | Read-only API für AuditLog |
| Benutzer/IP/Zeitstempel-Tracking | ✅ | Vollständig im AuditLog |
| Import-Schutz | ✅ | Nur `create_only` Mode (keine Überschreibung) |
| Invoice-Status-Workflow | ✅ | Status-Tracking (DRAFT → SENT → PAID) |

### ❌ Fehlende Komponenten

| Anforderung | Priorität | Komplexität | Phase |
|-------------|-----------|-------------|-------|
| Unveränderbarkeit von Dokumenten | 🔴 HOCH | HOCH | 1 |
| Kryptographische Integrität (Hash-Ketten) | 🔴 HOCH | HOCH | 2 |
| Löschsperren | 🟡 MITTEL | MITTEL | 3 |
| Verfahrensdokumentation | 🟡 MITTEL | NIEDRIG | 4 |
| GDPdU/GoBD-Export für Finanzbehörden | 🟡 MITTEL | MITTEL | 5 |
| Qualifizierte Zeitstempel (Optional) | 🟢 NIEDRIG | HOCH | 6 |

---

## Konzept: Unveränderbarkeit ohne WORM-Speicher

### Was fordert die GoBD?

Die GoBD fordert **"Unveränderbarkeit"**, aber **nicht zwingend WORM-Speicher** (Write Once Read Many):

> *"Die Unveränderbarkeit kann [...] durch geeignete technische und organisatorische Maßnahmen sichergestellt werden."* (BMF-Schreiben, Rz. 59)

### Zwei Ebenen der Unveränderbarkeit

| Ebene | Beschreibung | Schutz gegen | In diesem Plan |
|-------|--------------|--------------|----------------|
| **Logische Unveränderbarkeit** | `is_locked` Flag + `save()` Override | Normale Benutzer, UI, API | ✅ Phase 1 |
| **Physische Unveränderbarkeit** | WORM-Storage (Hardware/Cloud) | Alle, inkl. DB-Admins | ⭐ Optional |

### Akzeptierte Maßnahmen laut GoBD

| Maßnahme | Phase | Rechtlich ausreichend |
|----------|-------|----------------------|
| Zugriffskontrollen (RBAC) | ✅ Bereits | ✅ Ja |
| Protokollierung aller Änderungen (Audit-Trail) | ✅ Bereits | ✅ Ja |
| Logische Sperre (`is_locked`) | Phase 1 | ✅ Ja (Basis) |
| Kryptographische Prüfsummen (Hash) | Phase 2 | ✅ Ja (empfohlen) |
| Verfahrensdokumentation | Phase 4 | ✅ Ja (Pflicht) |
| WORM-Speicher | ❌ Nicht geplant | ⭐ Optional |

**Fazit:** Mit Phase 1-4 ist die Anwendung **GoBD-konform**, auch ohne WORM-Speicher.

### Was der Hash-Mechanismus (Phase 2) bietet

Auch ohne WORM kann **nachgewiesen** werden, ob manipuliert wurde:

```
Rechnung erstellt → Hash berechnet → Hash gespeichert (+ Audit-Log)
                         ↓
        Spätere Prüfung: Hash neu berechnen
                         ↓
        Hash stimmt überein? → ✅ Keine Manipulation
        Hash stimmt nicht?   → ❌ ALARM! Manipulation erkannt
```

Dies ist für Betriebsprüfungen ausreichend, da:
1. Manipulation **nachweisbar** ist
2. Der ursprüngliche Hash im Audit-Trail steht
3. Die Audit-Trail-Kette selbst auch gehasht ist

### Wann ist WORM-Speicher sinnvoll?

WORM-Speicher ist sinnvoll bei:
- Sehr hohen Compliance-Anforderungen (Banken, Versicherungen)
- Misstrauen gegenüber eigenen Datenbankadministratoren
- Expliziter Forderung durch Wirtschaftsprüfer

**WORM-Optionen (falls später gewünscht):**

| Anbieter | Typ | Kosten |
|----------|-----|--------|
| AWS S3 Object Lock | Cloud | €€ |
| Azure Immutable Blob Storage | Cloud | €€ |
| NetApp SnapLock | On-Premise | €€€ |
| Lokale WORM-Festplatten | Hardware | €€€ |

### PostgreSQL Rollenkonzept für zusätzliche Sicherheit

Um auch direkten SQL-Zugriff durch Administratoren einzuschränken, kann ein **differenziertes PostgreSQL-Rollenkonzept** implementiert werden:

#### Empfohlene Rollen-Architektur

```sql
-- 1. Anwendungsbenutzer (Django)
CREATE ROLE app_user WITH LOGIN PASSWORD 'secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- Django verwendet diese Rolle für normale Operationen

-- 2. Readonly-Rolle für Reporting/Backup
CREATE ROLE readonly_user WITH LOGIN PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
-- Für Backups, Reporting, Auswertungen

-- 3. DBA-Rolle (eingeschränkt)
CREATE ROLE dba_admin WITH LOGIN PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE erechnung TO dba_admin;
GRANT USAGE ON SCHEMA public TO dba_admin;
-- KEIN GRANT auf Anwendungstabellen!
-- Nur für: Vacuum, Reindex, Monitoring, User-Management

-- 4. Superuser (nur für Notfälle)
-- Zugriff nur mit 4-Augen-Prinzip und Dokumentation
```

#### Row-Level Security (RLS) für gesperrte Rechnungen

```sql
-- Verhindert UPDATE/DELETE auf gesperrte Rechnungen auch per SQL
ALTER TABLE invoice_app_invoice ENABLE ROW LEVEL SECURITY;

-- Policy: Gesperrte Rechnungen können nicht geändert werden
CREATE POLICY invoice_lock_policy ON invoice_app_invoice
    FOR UPDATE
    USING (is_locked = FALSE);

CREATE POLICY invoice_delete_policy ON invoice_app_invoice
    FOR DELETE
    USING (is_locked = FALSE);

-- Anwendungsbenutzer unterliegt dieser Policy
ALTER ROLE app_user SET row_security = on;
```

#### Audit-Tabelle zusätzlich schützen

```sql
-- Audit-Log nur INSERT erlauben, kein UPDATE/DELETE
REVOKE UPDATE, DELETE ON invoice_app_auditlog FROM app_user;
GRANT INSERT, SELECT ON invoice_app_auditlog TO app_user;

-- Trigger verhindert jegliche Änderung
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit-Log-Einträge dürfen nicht geändert oder gelöscht werden (GoBD)';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_immutable_trigger
    BEFORE UPDATE OR DELETE ON invoice_app_auditlog
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
```

#### Vorteile dieses Konzepts

| Maßnahme | Schützt gegen |
|----------|---------------|
| Separate DB-Rollen | Privilege Escalation |
| Row-Level Security | Direkten SQL-Zugriff auf gesperrte Daten |
| Trigger auf Audit-Log | Manipulation des Audit-Trails |
| Kein Superuser für Django | Kompromittierte Anwendung |

#### Implementation als optionale Phase 1b

Diese PostgreSQL-Härtung kann als **optionale Erweiterung** nach Phase 1 implementiert werden:

- **Aufwand:** 0.5-1 Tag
- **Voraussetzung:** Phase 1 abgeschlossen
- **Migrations-Skript:** Erstellt Rollen und Policies

---

## Phase 1: Dokumenten-Unveränderbarkeit

**Ziel:** Nach Versand dürfen Rechnungen nicht mehr geändert werden
**Aufwand:** 2-3 Tage
**Abhängigkeiten:** Keine

### 1.1 Model-Erweiterungen

Neue Felder im `Invoice` Model:

```python
class Invoice(models.Model):
    # ... existing fields ...

    # GoBD Compliance - Unveränderbarkeit
    is_locked = models.BooleanField(
        _("Gesperrt"),
        default=False,
        help_text=_("Gesperrte Dokumente können nicht mehr geändert werden")
    )
    locked_at = models.DateTimeField(
        _("Gesperrt am"),
        null=True,
        blank=True
    )
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locked_invoices",
        verbose_name=_("Gesperrt von")
    )
    lock_reason = models.CharField(
        _("Sperrgrund"),
        max_length=50,
        choices=[
            ("SENT", _("Versendet")),
            ("PAID", _("Bezahlt")),
            ("CANCELLED", _("Storniert")),
            ("MANUAL", _("Manuell gesperrt")),
        ],
        blank=True
    )
```

### 1.2 Geschäftslogik

**`save()` Override:**
```python
def save(self, *args, **kwargs):
    if self.pk:  # Existing invoice
        if self.is_locked:
            # Erlaube nur Status-Änderungen zu CANCELLED
            allowed_updates = {'status', 'updated_at'}
            # ... validation logic
            raise GoBDViolationError(
                "Gesperrte Rechnungen können nicht geändert werden. "
                "Erstellen Sie eine Stornorechnung."
            )

    # Auto-Lock bei Status-Wechsel
    if self.status in [self.InvoiceStatus.SENT, self.InvoiceStatus.PAID]:
        if not self.is_locked:
            self.is_locked = True
            self.locked_at = timezone.now()
            self.lock_reason = self.status

    super().save(*args, **kwargs)
```

### 1.3 Stornierung statt Löschung

```python
class Invoice(models.Model):
    # Referenz auf Stornorechnung
    cancelled_by = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancels_invoice',
        verbose_name=_("Storniert durch")
    )

    def cancel(self, user, reason=""):
        """Erstellt eine Stornorechnung statt Löschung."""
        if self.status == self.InvoiceStatus.CANCELLED:
            raise ValueError("Rechnung ist bereits storniert")

        # Erstelle Stornorechnung (Credit Note)
        credit_note = Invoice.objects.create(
            invoice_type=Invoice.InvoiceType.CREDIT_NOTE,
            company=self.company,
            business_partner=self.business_partner,
            # ... weitere Felder kopieren mit negativen Beträgen
            notes=f"Storno zu {self.invoice_number}: {reason}",
            created_by=user,
        )

        self.status = self.InvoiceStatus.CANCELLED
        self.cancelled_by = credit_note
        self.save()

        return credit_note
```

### 1.4 Admin & API Anpassungen

- Admin-UI: Gesperrte Rechnungen als read-only anzeigen
- API: 403 Forbidden bei Änderungsversuchen an gesperrten Dokumenten
- Neue Action: "Rechnung stornieren" statt "Löschen"

### 1.5 Tests

- [ ] Test: Gesperrte Rechnung kann nicht geändert werden
- [ ] Test: Auto-Lock bei Status SENT
- [ ] Test: Auto-Lock bei Status PAID
- [ ] Test: Stornierung erstellt Credit Note
- [ ] Test: API gibt 403 bei Änderungsversuch

---

## Phase 2: Kryptographische Integrität

**Ziel:** Manipulationen an Dokumenten nachweisbar machen
**Aufwand:** 3-4 Tage
**Abhängigkeiten:** Phase 1

### 2.1 Model-Erweiterungen

**Invoice Model:**
```python
class Invoice(models.Model):
    # Kryptographische Integrität
    content_hash = models.CharField(
        _("Content Hash"),
        max_length=64,
        blank=True,
        help_text=_("SHA-256 Hash des Dokumentinhalts")
    )
    hash_algorithm = models.CharField(
        _("Hash-Algorithmus"),
        max_length=20,
        default="SHA256"
    )
    hash_created_at = models.DateTimeField(
        _("Hash erstellt am"),
        null=True,
        blank=True
    )
    previous_invoice_hash = models.CharField(
        _("Vorheriger Hash"),
        max_length=64,
        blank=True,
        help_text=_("Hash der vorherigen Rechnung (Kette)")
    )
```

**AuditLog Model:**
```python
class AuditLog(models.Model):
    # Hash-Kette für Audit-Trail
    entry_hash = models.CharField(
        _("Entry Hash"),
        max_length=64,
        blank=True
    )
    previous_entry_hash = models.CharField(
        _("Vorheriger Entry Hash"),
        max_length=64,
        blank=True
    )
```

### 2.2 Integrity Service

```python
# invoice_app/services/integrity_service.py

import hashlib
import json
from typing import List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class IntegrityViolation:
    object_type: str
    object_id: str
    expected_hash: str
    actual_hash: str
    detected_at: datetime

class IntegrityService:
    """Service für kryptographische Integritätsprüfung."""

    HASH_ALGORITHM = "sha256"

    @classmethod
    def calculate_invoice_hash(cls, invoice: Invoice) -> str:
        """Berechnet SHA-256 Hash des Rechnungsinhalts."""
        # Deterministische Serialisierung
        data = {
            "invoice_number": invoice.invoice_number,
            "invoice_type": invoice.invoice_type,
            "company_id": invoice.company_id,
            "business_partner_id": invoice.business_partner_id,
            "issue_date": invoice.issue_date.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "currency": invoice.currency,
            "subtotal": str(invoice.subtotal),
            "tax_amount": str(invoice.tax_amount),
            "total_amount": str(invoice.total_amount),
            "lines": [
                {
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price),
                    "tax_rate": str(line.tax_rate),
                }
                for line in invoice.lines.all().order_by('id')
            ],
        }

        # Kanonische JSON-Serialisierung
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    @classmethod
    def verify_invoice_integrity(cls, invoice: Invoice) -> Tuple[bool, Optional[str]]:
        """Prüft ob Rechnung unverändert ist."""
        if not invoice.content_hash:
            return True, None  # Kein Hash vorhanden (Legacy-Daten)

        current_hash = cls.calculate_invoice_hash(invoice)
        if current_hash != invoice.content_hash:
            return False, f"Hash mismatch: expected {invoice.content_hash}, got {current_hash}"
        return True, None

    @classmethod
    def calculate_audit_chain_hash(cls, audit_log: AuditLog) -> str:
        """Berechnet Hash für Audit-Log-Eintrag inkl. Vorgänger."""
        data = {
            "event_id": str(audit_log.event_id),
            "timestamp": audit_log.timestamp.isoformat(),
            "action": audit_log.action,
            "username": audit_log.username,
            "object_type": audit_log.object_type,
            "object_id": audit_log.object_id,
            "description": audit_log.description,
            "previous_hash": audit_log.previous_entry_hash or "",
        }
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    @classmethod
    def verify_audit_chain(cls, limit: int = 1000) -> List[IntegrityViolation]:
        """Prüft Integrität der Audit-Log-Kette."""
        violations = []

        audit_logs = AuditLog.objects.order_by('timestamp')[:limit]

        for audit_log in audit_logs:
            if not audit_log.entry_hash:
                continue  # Legacy-Eintrag

            expected_hash = cls.calculate_audit_chain_hash(audit_log)
            if expected_hash != audit_log.entry_hash:
                violations.append(IntegrityViolation(
                    object_type="AuditLog",
                    object_id=str(audit_log.event_id),
                    expected_hash=audit_log.entry_hash,
                    actual_hash=expected_hash,
                    detected_at=timezone.now(),
                ))

        return violations

    @classmethod
    def generate_integrity_report(cls) -> dict:
        """Erstellt Integritätsbericht für alle Dokumente."""
        report = {
            "generated_at": timezone.now().isoformat(),
            "invoice_count": 0,
            "invoice_violations": [],
            "audit_log_count": 0,
            "audit_log_violations": [],
            "status": "OK",
        }

        # Prüfe Rechnungen
        for invoice in Invoice.objects.filter(is_locked=True):
            report["invoice_count"] += 1
            valid, error = cls.verify_invoice_integrity(invoice)
            if not valid:
                report["invoice_violations"].append({
                    "invoice_number": invoice.invoice_number,
                    "error": error,
                })

        # Prüfe Audit-Log
        report["audit_log_violations"] = [
            v.__dict__ for v in cls.verify_audit_chain()
        ]
        report["audit_log_count"] = AuditLog.objects.count()

        if report["invoice_violations"] or report["audit_log_violations"]:
            report["status"] = "VIOLATIONS_FOUND"

        return report
```

### 2.3 Celery Tasks

```python
# invoice_app/tasks/integrity_tasks.py

@shared_task
def daily_integrity_check():
    """Tägliche Integritätsprüfung aller Dokumente."""
    from invoice_app.services.integrity_service import IntegrityService

    report = IntegrityService.generate_integrity_report()

    if report["status"] != "OK":
        # Alert senden
        send_integrity_alert(report)

        # AuditLog-Eintrag
        AuditLog.log_action(
            action=AuditLog.ActionType.SECURITY_EVENT,
            description="Integritätsverletzung erkannt",
            details=report,
            severity=AuditLog.Severity.CRITICAL,
        )

    return report
```

### 2.4 Tests

- [ ] Test: Hash-Berechnung ist deterministisch
- [ ] Test: Hash ändert sich bei Datenänderung
- [ ] Test: Audit-Chain-Verifikation erkennt Manipulation
- [ ] Test: Integrity-Report enthält alle Violations

---

## Phase 3: Löschsperren & Aufbewahrungsfristen

**Ziel:** 10-Jahre Aufbewahrungspflicht technisch durchsetzen
**Aufwand:** 2 Tage
**Abhängigkeiten:** Phase 1

### 3.1 Model-Erweiterungen

```python
class Invoice(models.Model):
    # Aufbewahrung
    retention_until = models.DateField(
        _("Aufbewahren bis"),
        null=True,
        blank=True,
        help_text=_("Mindestens 10 Jahre nach Erstellung (GoBD)")
    )
    deletion_blocked = models.BooleanField(
        _("Löschung gesperrt"),
        default=True
    )
    is_archived = models.BooleanField(
        _("Archiviert"),
        default=False
    )
    archived_at = models.DateTimeField(
        _("Archiviert am"),
        null=True,
        blank=True
    )
```

### 3.2 Custom Exception

```python
# invoice_app/exceptions.py

class GoBDViolationError(Exception):
    """Wird geworfen bei Verletzung von GoBD-Anforderungen."""
    pass
```

### 3.3 Delete Override

```python
class Invoice(models.Model):
    def delete(self, *args, **kwargs):
        if self.deletion_blocked:
            if self.retention_until and self.retention_until > timezone.now().date():
                raise GoBDViolationError(
                    f"Löschung vor Ablauf der Aufbewahrungsfrist "
                    f"({self.retention_until}) nicht erlaubt (GoBD)"
                )

        # Soft-Delete statt Hard-Delete
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save()

        AuditLog.log_action(
            action=AuditLog.ActionType.DELETE,
            object_instance=self,
            description=f"Rechnung {self.invoice_number} archiviert (Soft-Delete)",
        )

    def save(self, *args, **kwargs):
        # Setze Aufbewahrungsfrist bei Erstellung
        if not self.retention_until:
            self.retention_until = (
                timezone.now().date() + timezone.timedelta(days=3650)  # 10 Jahre
            )
        super().save(*args, **kwargs)
```

### 3.4 Celery Tasks

```python
@shared_task
def check_retention_expiry():
    """Prüft abgelaufene Aufbewahrungsfristen und benachrichtigt."""
    expiring_soon = Invoice.objects.filter(
        retention_until__lte=timezone.now().date() + timezone.timedelta(days=30),
        retention_until__gt=timezone.now().date(),
        is_archived=False,
    )

    if expiring_soon.exists():
        # Benachrichtigung senden
        send_retention_expiry_notification(expiring_soon)
```

### 3.5 Tests

- [ ] Test: Löschung vor Ablauf der Frist wird blockiert
- [ ] Test: Soft-Delete nach Ablauf möglich
- [ ] Test: Aufbewahrungsfrist wird automatisch gesetzt (10 Jahre)
- [ ] Test: Archivierte Rechnungen sind weiterhin lesbar

---

## Phase 4: Verfahrensdokumentation

**Ziel:** Nachvollziehbare Dokumentation aller Prozesse (GoBD-Pflicht!)
**Aufwand:** 1-2 Tage
**Abhängigkeiten:** Keine

### 4.1 Dokumentationsstruktur

```
docs/gobd/
├── README.md                       # Übersicht
├── 01_systemuebersicht.md          # Beschreibung des Systems
├── 02_datenfluss.md                # Wie fließen Daten?
├── 03_zugriffsrechte.md            # Wer darf was? (RBAC)
├── 04_aenderungsprotokoll.md       # Was wird protokolliert?
├── 05_aufbewahrungsfristen.md      # 10-Jahre-Regel
├── 06_pruefbarkeit.md              # Zugriff für Finanzbehörden
├── 07_integritaetssicherung.md     # Hash-Verfahren
└── 08_notfallverfahren.md          # Wiederherstellung
```

### 4.2 Pflichtinhalte

1. **Systemübersicht**
   - Name und Version des Systems
   - Hersteller/Entwickler
   - Einsatzzweck

2. **Datenfluss**
   - Eingabe → Verarbeitung → Speicherung → Ausgabe
   - Diagramme (Mermaid)

3. **Zugriffsberechtigungen**
   - Rollenkonzept (Admin, Manager, Accountant, Viewer)
   - Berechtigungsmatrix

4. **Änderungsprotokoll**
   - Was wird protokolliert?
   - Wie lange?
   - Wo gespeichert?

5. **Aufbewahrungsfristen**
   - 10-Jahre-Regel für Rechnungen
   - Automatische Berechnung

6. **Prüfbarkeit**
   - GDPdU-Export
   - Zugriffsmöglichkeiten für Prüfer

---

## Phase 5: GDPdU/GoBD-Export für Finanzbehörden

**Ziel:** Daten in prüfbarem Format exportieren
**Aufwand:** 2-3 Tage
**Abhängigkeiten:** Phase 1-3

### 5.1 Export Service

```python
# invoice_app/services/gobd_export_service.py

class GoBDExportService:
    """Export im GDPdU/GoBD-Format für Betriebsprüfungen."""

    def export_gdpdu_index_xml(
        self,
        date_from: date,
        date_to: date
    ) -> str:
        """Erstellt index.xml gemäß GDPdU-Standard."""
        # XML-Struktur gemäß BMF-Vorgaben
        pass

    def export_invoices_csv(
        self,
        date_from: date,
        date_to: date
    ) -> bytes:
        """Exportiert Rechnungen als CSV."""
        pass

    def export_audit_trail_csv(
        self,
        date_from: date,
        date_to: date
    ) -> bytes:
        """Exportiert Audit-Trail als CSV."""
        pass

    def create_pruefpaket(
        self,
        date_from: date,
        date_to: date
    ) -> bytes:
        """
        Erstellt komplettes Prüfpaket als ZIP:
        - index.xml (GDPdU)
        - rechnungen.csv
        - audit_trail.csv
        - PDF/A-3 Rechnungen
        - verfahrensdokumentation/
        """
        pass
```

### 5.2 Admin Action

```python
@admin.action(description="GoBD-Prüfpaket exportieren")
def export_gobd_pruefpaket(modeladmin, request, queryset):
    """Admin-Action zum Export eines Prüfpakets."""
    pass
```

### 5.3 API Endpoint

```python
# GET /api/export/gobd/?from=2024-01-01&to=2024-12-31
class GoBDExportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Erstellt und liefert GoBD-Prüfpaket."""
        pass
```

### 5.4 Tests

- [ ] Test: index.xml entspricht GDPdU-Schema
- [ ] Test: CSV-Export enthält alle Pflichtfelder
- [ ] Test: ZIP-Paket ist vollständig
- [ ] Test: Nur Admins können exportieren

---

## Phase 6: Qualifizierte Zeitstempel (Optional)

**Ziel:** Rechtssichere Zeitstempel durch externe TSA
**Aufwand:** 3-4 Tage
**Abhängigkeiten:** Phase 2
**Priorität:** NIEDRIG (optional für erhöhte Rechtssicherheit)

### 6.1 TSA-Optionen

| Anbieter | Typ | Kosten | Qualifiziert (eIDAS) |
|----------|-----|--------|---------------------|
| DFN-PKI | Forschung/Bildung | Kostenlos | ⚠️ Teilweise |
| D-Trust | Kommerziell | €€ | ✅ Ja |
| Bundesdruckerei | Kommerziell | €€€ | ✅ Ja |
| FreeTSA | Open Source | Kostenlos | ❌ Nein |

### 6.2 Timestamp Service

```python
# invoice_app/services/timestamp_service.py

class TimestampService:
    """Qualifizierte Zeitstempel gemäß eIDAS/RFC 3161."""

    TSA_URL = settings.GOBD_TSA_URL  # z.B. "https://freetsa.org/tsr"

    @classmethod
    def request_timestamp(cls, data_hash: str) -> bytes:
        """Holt Zeitstempel-Token von TSA."""
        # RFC 3161 TimeStampReq erstellen
        pass

    @classmethod
    def verify_timestamp(cls, data_hash: str, token: bytes) -> bool:
        """Verifiziert Zeitstempel-Token."""
        pass
```

### 6.3 Model-Erweiterungen

```python
class Invoice(models.Model):
    # Qualifizierter Zeitstempel
    timestamp_token = models.BinaryField(
        _("Zeitstempel-Token"),
        null=True,
        blank=True
    )
    timestamp_authority = models.CharField(
        _("Zeitstempel-Autorität"),
        max_length=255,
        blank=True
    )
    timestamp_created_at = models.DateTimeField(
        _("Zeitstempel erstellt am"),
        null=True,
        blank=True
    )
```

---

## Technische Entscheidungen

### Offene Entscheidungen

| # | Frage | Optionen | Entscheidung |
|---|-------|----------|--------------|
| 1 | Hash-Algorithmus | SHA-256, SHA-3, BLAKE3 | **TBD** |
| 2 | Zeitstempel-Anbieter | FreeTSA, D-Trust, Bundesdruckerei | **TBD** |
| 3 | Soft-Delete vs Archivierung | Separate Tabelle vs Flag | **TBD** |
| 4 | Hash-Kette vs Merkle-Tree | Linear vs Baum | **TBD** |

### Getroffene Entscheidungen

| # | Frage | Entscheidung | Begründung |
|---|-------|--------------|------------|
| - | - | - | - |

---

## Zeitplan

| Phase | Aufwand | Start | Ende | Status |
|-------|---------|-------|------|--------|
| 1: Unveränderbarkeit | 2-3 Tage | TBD | TBD | ⏳ Geplant |
| 2: Kryptographische Integrität | 3-4 Tage | TBD | TBD | ⏳ Geplant |
| 3: Löschsperren | 2 Tage | TBD | TBD | ⏳ Geplant |
| 4: Verfahrensdokumentation | 1-2 Tage | TBD | TBD | ⏳ Geplant |
| 5: GDPdU-Export | 2-3 Tage | TBD | TBD | ⏳ Geplant |
| 6: Qualifizierte Zeitstempel | 3-4 Tage | TBD | TBD | ⏳ Optional |

**Gesamtaufwand:** 13-18 Arbeitstage

---

## Risiken & Mitigation

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Performance durch Hash-Berechnung | Mittel | Niedrig | Async/Celery, Caching |
| TSA-Ausfälle | Niedrig | Hoch | Fallback-TSA, Retry-Logic |
| Migrationsprobleme (bestehende Daten) | Hoch | Mittel | Migrations-Skript mit Hash-Neuberechnung |
| Komplexität der Verfahrensdoku | Mittel | Mittel | Templates, Checklisten |
| Inkompatibilität mit bestehenden Workflows | Mittel | Mittel | Feature-Flags, schrittweise Aktivierung |

---

## Referenzen

- [GoBD](https://ao.bundesfinanzministerium.de/ao/2023/Anhaenge/BMF-Schreiben-und-gleichlautende-Laendererlasse/Anhang-64/inhalt.html)
    enthält: (BMF-Schreiben vom 28.11.2019 - IV A 4 - 0316/19/10003:001 -, BStBl I S. 1269)
- [GoDB erste Änderung(11.03.2024)](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Weitere_Steuerthemen/Abgabenordnung/AO-Anwendungserlass/2024-03-11-aenderung-gobd.html)
- [GoDB zweite Änderung(14.07.2025)](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Weitere_Steuerthemen/Abgabenordnung/2025-07-14-GoBD-2-aenderung.html)

- [GDPdU-Beschreibungsstandard](https://www.bzst.de/DE/Unternehmen/Aussenpruefungen/gdpdu/gdpdu_node.html) führt zu 404, alternativ:
  [GDPdU Dokumentation (PDF)](https://www.bzst.de/SharedDocs/Downloads/DE/Unternehmen/Aussenpruefungen/gdpdu/gdpdu_beschreibungsstandard.pdf?__blob=publicationFile&v=3)
- [eIDAS-Verordnung (EU)](https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX%3A32014R0910)
- [RFC 3161 - Time-Stamp Protocol](https://datatracker.ietf.org/doc/html/rfc3161)

---

**Dokument-Version:** 1.0
**Letzte Aktualisierung:** 3. Dezember 2025
**Autor:** AI Assistant / Development Team
