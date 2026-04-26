# Django Migrations-Strategie

**Erstellt:** 04.03.2026
**Status:** Aktiv
**Quelle:** TD-01 (req42/07-risks-technical-debt)

---

## 1. Übersicht: Aktuelle Migrationen

| Migration | Typ | Beschreibung | Reversibel |
|-----------|-----|--------------|------------|
| `0001_initial` | Schema | Vollständiges Initialschema (Company, Country, BusinessPartner, Product, Invoice, InvoiceLine, InvoiceAttachment, InvoiceAllowanceCharge, UserRole, UserProfile, AuditLog, SystemConfig) | Ja (destroy all) |
| `0002_load_countries` | Data | Länderdaten mit EU-USt-Sätzen aus `fixtures/countries.json` laden | Ja (`unload_countries`) |
| `0003_unit_of_measure_check_constraint` | Schema | CheckConstraints für `InvoiceLine.unit_of_measure` und `Product.unit_of_measure` | Ja (remove constraints) |
| `0004_add_tax_category_to_invoiceline` | Schema | `tax_category` + `tax_exemption_reason` auf InvoiceLine (EN16931) | Ja (remove fields) |
| `0005_gobd_compliance` | Schema | GoBD-Felder: `is_locked`, `content_hash`, `retention_until`, `is_archived`, `cancelled_by`, AuditLog-Hash-Kette | Ja (remove fields/indexes) |

### Abhängigkeitskette

```
auth.User (Django built-in)
    ↓
0001_initial (alle Models)
    ↓
0002_load_countries (Data: Country-Fixtures)
    ↓
0003_unit_of_measure_check_constraint (Schema: Constraints)
    ↓
0004_add_tax_category_to_invoiceline (Schema: Tax-Felder)
    ↓
0005_gobd_compliance (Schema: GoBD-Felder + Indexes)
```

---

## 2. Rollback-Strategie

### 2.1 Grundprinzip

Jede Migration muss reversibel sein. Django unterstützt Rollbacks nativ:

```bash
# Rollback zur vorherigen Migration
docker compose exec web python project_root/manage.py migrate invoice_app 0004

# Rollback aller invoice_app Migrationen
docker compose exec web python project_root/manage.py migrate invoice_app zero
```

### 2.2 Rollback-Matrix

| Rollback auf | Befehl | Datenverlust | Vorbedingung |
|-------------|--------|--------------|--------------|
| `0004` ← `0005` | `migrate invoice_app 0004` | GoBD-Felder (is_locked, content_hash, retention_until, etc.) | Keine gesperrten Rechnungen |
| `0003` ← `0004` | `migrate invoice_app 0003` | tax_category, tax_exemption_reason auf InvoiceLine | Keine kritischen Steuerdaten |
| `0002` ← `0003` | `migrate invoice_app 0002` | CheckConstraints | Keine |
| `0001` ← `0002` | `migrate invoice_app 0001` | Alle Länderdaten | Backup vorher! |
| `zero` ← `0001` | `migrate invoice_app zero` | **ALLE DATEN** | Nur Development! |

### 2.3 Rollback-Prozedur (Production)

```bash
# 1. Backup IMMER zuerst
docker compose exec web python project_root/manage.py backup_database

# 2. Aktuelle Migration prüfen
docker compose exec web python project_root/manage.py showmigrations invoice_app

# 3. Rollback durchführen
docker compose exec web python project_root/manage.py migrate invoice_app <ZIEL>

# 4. Status verifizieren
docker compose exec web python project_root/manage.py showmigrations invoice_app

# 5. Application Health Check
curl -s http://localhost:8000/api/health/ | python -m json.tool
```

### 2.4 Regeln für reversible Data-Migrations

Data-Migrations **müssen** immer eine Reverse-Funktion haben:

```python
# ✅ Korrekt: Mit Reverse-Funktion
def load_data(apps, schema_editor):
    MyModel = apps.get_model("invoice_app", "MyModel")
    MyModel.objects.create(name="Example")

def unload_data(apps, schema_editor):
    MyModel = apps.get_model("invoice_app", "MyModel")
    MyModel.objects.filter(name="Example").delete()

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(load_data, unload_data),
    ]

# ❌ Falsch: RunPython ohne Reverse
class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(load_data),  # Kein Rollback möglich!
    ]
```

---

## 3. Zero-Downtime-Migration-Pattern

### 3.1 Grundprinzip

Bei Deployments dürfen Migrationen keinen Service-Ausfall verursachen. Das erfordert **Backward-Compatible Migrations**: Der alte Code muss mit dem neuen Schema funktionieren und umgekehrt.

### 3.2 Erlaubte Operationen (Zero-Downtime-kompatibel)

| Operation | Kompatibel? | Begründung |
|-----------|-------------|-------------|
| `AddField` mit `null=True` oder `default` | ✅ Ja | Alter Code ignoriert neue Spalte |
| `AddIndex` | ✅ Ja | `CREATE INDEX CONCURRENTLY` verwenden |
| `AddConstraint` | ⚠️ Bedingt | Daten müssen die Constraint erfüllen |
| `RemoveField` | ❌ Nein | Alter Code referenziert die Spalte noch |
| `RenameField` | ❌ Nein | Alter Code kennt neuen Namen nicht |
| `AlterField` (Typ-Änderung) | ❌ Nein | Ggf. Lock auf gesamter Tabelle |
| `RunPython` (Data) | ✅ Ja | Wenn idempotent und batch-basiert |

### 3.3 Pattern: Feld hinzufügen (sicher)

```python
# Migration: Neues Feld mit Default
migrations.AddField(
    model_name="invoice",
    name="new_field",
    field=models.CharField(
        max_length=100,
        blank=True,
        default="",  # Default für bestehende Rows
    ),
),
```

### 3.4 Pattern: Feld entfernen (3-Phasen)

Felder dürfen **nie direkt entfernt** werden. Stattdessen 3 Deployment-Phasen:

**Phase 1 — Code-Änderung (ohne Migration):**
- Feld im Code nicht mehr verwenden (Views, Serializers, Templates)
- Deploy

**Phase 2 — Migration:**
```python
# Migration: Feld entfernen
migrations.RemoveField(
    model_name="invoice",
    name="deprecated_field",
),
```
- Deploy (Feld ist nun aus DB entfernt)

**Phase 3 — Cleanup:**
- Model-Klasse bereinigen (Feld-Definition entfernen)

### 3.5 Pattern: Feld umbenennen (3-Phasen)

**Phase 1 — Neues Feld + Daten kopieren:**
```python
# Migration 1: Neues Feld hinzufügen
migrations.AddField(
    model_name="invoice",
    name="new_name",
    field=models.CharField(max_length=100, blank=True, default=""),
),
# Migration 2: Daten kopieren
migrations.RunPython(copy_old_to_new, copy_new_to_old),
```

**Phase 2 — Code auf neues Feld umstellen:**
- Views, Serializers, Templates auf `new_name` ändern
- Deploy

**Phase 3 — Altes Feld entfernen:**
```python
migrations.RemoveField(model_name="invoice", name="old_name"),
```

### 3.6 Pattern: Data-Migration mit Batch-Processing

```python
from django.db import migrations

BATCH_SIZE = 1000

def migrate_data(apps, schema_editor):
    """Batch-basierte Data-Migration für große Tabellen."""
    Invoice = apps.get_model("invoice_app", "Invoice")

    total = Invoice.objects.count()
    for start in range(0, total, BATCH_SIZE):
        batch = Invoice.objects.order_by("pk")[start:start + BATCH_SIZE]
        updates = []
        for invoice in batch.select_related("supplier"):
            invoice.new_field = compute_value(invoice)
            updates.append(invoice)
        Invoice.objects.bulk_update(updates, ["new_field"])

def reverse_migrate_data(apps, schema_editor):
    """Reverse: Feld zurücksetzen."""
    Invoice = apps.get_model("invoice_app", "Invoice")
    Invoice.objects.all().update(new_field="")

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(migrate_data, reverse_migrate_data),
    ]
```

### 3.7 PostgreSQL-spezifisch: Concurrent Indexes

Für große Tabellen sollten Indexes **concurrent** erstellt werden:

```python
from django.contrib.postgres.operations import AddIndexConcurrently

class Migration(migrations.Migration):
    atomic = False  # Erforderlich für CONCURRENTLY

    operations = [
        AddIndexConcurrently(
            model_name="invoice",
            index=models.Index(fields=["created_at"], name="invoice_created_idx"),
        ),
    ]
```

---

## 4. Checkliste: Vor jedem Deployment

### 4.1 Automatisierte Prüfung

```bash
# Prüfen ob unapplied Migrations existieren
docker compose exec web python project_root/manage.py check_migrations

# Prüfen ob Model-Änderungen eine neue Migration erfordern
docker compose exec web python project_root/manage.py makemigrations --check --dry-run
```

### 4.2 Manuelle Checkliste

- [ ] **Backup erstellt** (`manage.py backup_database`)
- [ ] **Migration reversibel?** (RunPython hat Reverse-Funktion)
- [ ] **Zero-Downtime-kompatibel?** (Keine RemoveField/RenameField ohne Phase)
- [ ] **Batch-Processing?** (Data-Migrations für >1000 Rows)
- [ ] **select_related/prefetch_related?** (Keine N+1-Queries in Migrations)
- [ ] **Tests vorhanden?** (Mindestens Forward + Reverse testen)
- [ ] **Rollback getestet?** (In Development rückwärts migriert)

---

## 5. Anti-Pattern-Vermeidung

### 5.1 Behobene Anti-Pattern

| Anti-Pattern | Beschreibung | Status |
|-------------|-------------|--------|
| N+1 in Migration 0002 | Altes `0002_auto_20250724_1549.py` hatte `Invoice.objects.all()` ohne `select_related` | ✅ Behoben — Migration ersetzt durch `0002_load_countries.py` |

### 5.2 Verbotene Muster in Migrations

```python
# ❌ Unbegrenzter QuerySet ohne Batching
for obj in MyModel.objects.all():
    obj.field = compute(obj)
    obj.save()

# ❌ RunPython ohne Reverse-Funktion
migrations.RunPython(forward_only)

# ❌ Import von App-Code in Migrations
from invoice_app.models import Invoice  # NICHT verwenden!

# ❌ Direkte Model-Referenz statt apps.get_model()
Invoice.objects.all()  # NICHT verwenden!
```

### 5.3 Best Practices

```python
# ✅ Batch-Processing mit select_related
BATCH_SIZE = 1000
Model = apps.get_model("invoice_app", "Model")
qs = Model.objects.select_related("fk_field").order_by("pk")
for start in range(0, qs.count(), BATCH_SIZE):
    batch = qs[start:start + BATCH_SIZE]
    # ... process batch ...

# ✅ Immer apps.get_model() verwenden
Model = apps.get_model("invoice_app", "Model")

# ✅ Idempotente Migrations (sicher bei Retry)
if not Model.objects.filter(name="X").exists():
    Model.objects.create(name="X")
```

---

## 6. Deployment-Ablauf

### 6.1 Docker Compose (Entwicklung + Small Business)

```bash
# 1. Backup
docker compose exec web python project_root/manage.py backup_database

# 2. Neuen Code deployen
docker compose pull && docker compose up -d

# 3. Migrationen ausführen
docker compose exec web python project_root/manage.py migrate

# 4. Verifizieren
docker compose exec web python project_root/manage.py showmigrations
docker compose exec web python project_root/manage.py check_migrations
```

### 6.2 Kubernetes (Enterprise)

```bash
# 1. Backup
kubectl exec deploy/erechnung-web -- python project_root/manage.py backup_database

# 2. Migration als Job ausführen (vor dem Rolling Update)
kubectl apply -f k8s/jobs/migrate.yaml
kubectl wait --for=condition=complete job/django-migrate

# 3. Rolling Update
kubectl set image deploy/erechnung-web web=registry/erechnung:new-tag

# 4. Verifizieren
kubectl exec deploy/erechnung-web -- python project_root/manage.py check_migrations
```

---

## 7. Notfall-Rollback

### Szenario: Migration schlägt fehl

```bash
# 1. Fehler identifizieren
docker compose exec web python project_root/manage.py showmigrations invoice_app

# 2. Rollback zur letzten stabilen Migration
docker compose exec web python project_root/manage.py migrate invoice_app <LETZTE_STABILE>

# 3. Alten Code deployen
git checkout <LETZTER_STABILER_TAG>
docker compose up -d --build

# 4. Wenn Datenbank korrupt: Restore from Backup
docker compose exec db pg_restore -d erechnung /backups/latest.dump
```

### Szenario: Data-Migration hat fehlerhafte Daten erzeugt

```bash
# 1. Reverse-Migration ausführen
docker compose exec web python project_root/manage.py migrate invoice_app <VOR_DER_DATA_MIGRATION>

# 2. Daten manuell prüfen
docker compose exec web python project_root/manage.py shell
>>> from invoice_app.models import Invoice
>>> Invoice.objects.filter(problematic_field="bad_value").count()
```
