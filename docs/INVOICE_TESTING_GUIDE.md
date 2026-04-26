# 📋 Rechnungs-Testleitfaden: ZUGFeRD/Factur-X PDF & XML

**Erstellt:** 2025-11-12
**Zweck:** Konsolidierung und Verifikation der Invoice-PDF/XML-Generierung

---

## 🎯 Testziele

1. ✅ Verifizieren, dass **PDF-Generierung** funktioniert
2. ✅ Verifizieren, dass **XML eingebettet** wird (ZUGFeRD/Factur-X)
3. ✅ Validieren, dass **XML konform** ist
4. ✅ End-to-End-Test über **Web-Interface**

---

## 📊 Vorhandene Tests (Übersicht)

### Unit Tests

| Testdatei | Fokus | Status |
|-----------|-------|--------|
| `test_invoice_service.py` | InvoiceService, PDF/XML-Generierung | ✅ Vorhanden |
| `test_pdf_utils.py` | PDF-A/3 Generierung, XML-Embedding | ✅ Vorhanden |
| `test_xml_utils.py` | ZUGFeRD XML-Generierung & Validierung | ✅ Vorhanden |
| `test_modern_xml_validation.py` | Moderne Schematron-Validierung | ✅ Vorhanden |
| `test_validation_utils.py` | Datei-Validierung & Management | ✅ Vorhanden |

### Integrationstests

| Script | Zweck |
|--------|-------|
| `scripts/extract_pdf_xml.py` | XML aus PDF extrahieren und validieren |
| `scripts/inspect_pdf_xml.py` | PDF-Struktur inspizieren |
| `scripts/comprehensive_invoice_validator.py` | Vollständige Validierung |

---

## 🧪 Testplan für Morgen

### Teil 1: Unit-Tests ausführen (10 Min)

```bash
# Alle Invoice-bezogenen Tests
./run_tests_docker.sh invoice_app.tests.test_invoice_service
./run_tests_docker.sh invoice_app.tests.test_pdf_utils
./run_tests_docker.sh invoice_app.tests.test_xml_utils
./run_tests_docker.sh invoice_app.tests.test_modern_xml_validation

# Oder alle auf einmal:
./run_tests_docker.sh invoice_app.tests
```

**Erwartetes Ergebnis:** Alle Tests grün ✅

---

### Teil 2: Backend-Test über Django Shell (15 Min)

#### 2.1 Verbindung zum Container

```bash
docker-compose exec web python project_root/manage.py shell
```

#### 2.2 Testrechnung erstellen

```python
from invoice_app.models import Company, BusinessPartner, Invoice, InvoiceLine
from invoice_app.services.invoice_service import InvoiceService
from decimal import Decimal
from django.utils import timezone

# 1. Supplier (Firma) erstellen oder abrufen
supplier, created = Company.objects.get_or_create(
    name="Test Lieferant GmbH",
    defaults={
        'tax_id': 'DE123456789',
        'vat_id': 'DE987654321',
        'address_line1': 'Musterstraße 123',
        'postal_code': '10115',
        'city': 'Berlin',
        'country': 'Germany',
        'email': 'kontakt@lieferant.de'
    }
)

# 2. BusinessPartner erstellen oder abrufen
partner, created = BusinessPartner.objects.get_or_create(
    company_name="Test Kunde AG",
    defaults={
        'tax_id': 'DE987654321',
        'address_line1': 'Kundenweg 456',
        'postal_code': '80333',
        'city': 'München',
        'country': 'Germany',
        'email': 'info@kunde.de'
    }
)

# 3. Rechnung erstellen
today = timezone.now().date()
invoice = Invoice.objects.create(
    invoice_number=f"TEST-{today.strftime('%Y%m%d')}-001",
    invoice_type=Invoice.InvoiceType.INVOICE,
    company=supplier,
    business_partner=partner,
    issue_date=today,
    due_date=today + timezone.timedelta(days=30),
    currency="EUR",
    subtotal=Decimal("500.00"),
    tax_amount=Decimal("95.00"),
    total_amount=Decimal("595.00"),
    status=Invoice.InvoiceStatus.DRAFT,
    notes="Dies ist eine Testrechnung zur Verifikation der PDF/XML-Generierung."
)

# 4. Positionen hinzufügen
line1 = InvoiceLine.objects.create(
    invoice=invoice,
    description="Consulting-Dienstleistung",
    quantity=Decimal("5"),
    unit_price=Decimal("100.00"),
    tax_rate=Decimal("19.00"),
    line_total=Decimal("500.00"),
    product_code="CONSULT-001",
    unit_of_measure="HUR"  # Hour
)

# 5. PDF und XML generieren
service = InvoiceService()
result = service.generate_invoice_files(invoice, profile="BASIC")

# 6. Ergebnis überprüfen
print(f"\n✅ PDF erstellt: {result['pdf_path']}")
print(f"✅ XML erstellt: {result['xml_path']}")
print(f"✅ Validierung: {'OK' if result['is_valid'] else 'FEHLER'}")
if result['validation_errors']:
    print(f"⚠️  Fehler: {result['validation_errors']}")

# 7. Invoice-Objekt aktualisieren
invoice.refresh_from_db()
print(f"\n📄 PDF-Datei im Modell: {invoice.pdf_file.name if invoice.pdf_file else 'Nicht gesetzt'}")
print(f"📝 XML-Datei im Modell: {invoice.xml_file.name if invoice.xml_file else 'Nicht gesetzt'}")
```

**Erwartetes Ergebnis:**
- ✅ PDF-Datei wird erstellt
- ✅ XML-Datei wird erstellt
- ✅ Validierung schlägt nicht fehl
- ✅ Files werden im Invoice-Modell gespeichert

---

### Teil 3: PDF/XML-Dateien inspizieren (10 Min)

#### 3.1 Dateien finden

```bash
# Im Container
docker-compose exec web ls -lh /app/media/invoices/

# Oder vom Host
ls -lh media/invoices/
```

#### 3.2 XML aus PDF extrahieren

```bash
# Script ausführen (findet automatisch neueste PDF)
docker-compose exec web python scripts/extract_pdf_xml.py
```

**Das Script zeigt:**
- ✅ PDF-Größe und Metadaten
- ✅ Eingebettetes XML
- ✅ Validierungsergebnisse
- ✅ Gespeicherte XML-Datei

#### 3.3 Vollständige Validierung

```bash
docker-compose exec web python scripts/comprehensive_invoice_validator.py
```

**Prüft:**
- ✅ XML-Wohlgeformtheit
- ✅ XSD-Schema-Konformität
- ✅ Schematron-Regeln (EN16931)
- ✅ PDF/A-3 Konformität

---

### Teil 4: Frontend-Test (manuell) (20 Min)

#### 4.1 Frontend starten

```bash
docker-compose -f docker-compose.frontend.yml up -d
```

Öffne Browser: `http://localhost:5173`

#### 4.2 Testablauf

1. **Login**
   - Benutzername: `admin`
   - Passwort: `admin123`

2. **Kunde anlegen** (falls nicht vorhanden)
   - Navigation: Kunden → Neuer Kunde
   - Name: "Test Kunde GmbH"
   - Adresse ausfüllen
   - Speichern

3. **Rechnung erstellen**
   - Navigation: Rechnungen → Neue Rechnung
   - Kunde auswählen
   - Position hinzufügen:
     - Beschreibung: "Beratungsleistung"
     - Menge: 5
     - Einzelpreis: 100.00 EUR
     - MwSt: 19%
   - Weitere Position:
     - Beschreibung: "Software-Lizenz"
     - Menge: 1
     - Einzelpreis: 299.00 EUR
     - MwSt: 19%
   - **Speichern**

4. **PDF generieren**
   - Button "PDF generieren" klicken
   - Warten auf Download-Dialog
   - PDF öffnen und visuell prüfen

5. **XML extrahieren und prüfen**
   - Zurück zur Shell (siehe Teil 3.2)
   - XML aus generiertem PDF extrahieren
   - Validierung überprüfen

---

## ✅ Erfolgskriterien

### Minimal (Must-Have)
- [ ] Unit-Tests laufen durch (0 Fehler)
- [ ] PDF wird generiert (kann geöffnet werden)
- [ ] XML ist im PDF eingebettet (kann extrahiert werden)
- [ ] XML ist wohlgeformt (kein Parsing-Fehler)

### Standard (Should-Have)
- [ ] XML validiert gegen XSD-Schema
- [ ] PDF hat korrekte Metadaten (PDF/A-3)
- [ ] Rechnung kann über Frontend erstellt werden
- [ ] Download-Funktion funktioniert

### Optimal (Nice-to-Have)
- [ ] XML validiert gegen Schematron (EN16931)
- [ ] Alle Edge-Cases abgedeckt (Rabatte, mehrere MwSt-Sätze)
- [ ] PDF ist visuell ansprechend
- [ ] Performance akzeptabel (< 2 Sek. für Generierung)

---

## 🐛 Bekannte Probleme & Lösungen

### Problem: "PDF can't be opened"
**Lösung:** Prüfe, ob `reportlab` und `pikepdf` installiert sind:
```bash
docker-compose exec web pip list | grep -E "reportlab|pikepdf"
```

### Problem: "XML validation fails"
**Lösung:** Prüfe, ob Schematron-Dateien vorhanden sind:
```bash
docker-compose exec web ls -l /app/*.sch
```

### Problem: "No embedded XML found"
**Lösung:** Prüfe `pdf_utils.py` → `embed_xml_in_pdf()` Funktion

---

## 📝 Testprotokoll-Vorlage

Kopiere diese Vorlage und fülle sie während des Tests aus:

```markdown
# Testprotokoll: Invoice PDF/XML Generation
**Datum:** 2025-11-13
**Tester:** [Dein Name]

## Teil 1: Unit Tests
- [ ] test_invoice_service: ✅/❌
- [ ] test_pdf_utils: ✅/❌
- [ ] test_xml_utils: ✅/❌
- [ ] test_modern_xml_validation: ✅/❌

## Teil 2: Backend Shell Test
- [ ] Invoice erstellt: ✅/❌
- [ ] PDF generiert: ✅/❌ (Pfad: _____________)
- [ ] XML generiert: ✅/❌ (Pfad: _____________)
- [ ] Validierung OK: ✅/❌

## Teil 3: Inspektion
- [ ] XML extrahiert: ✅/❌
- [ ] XML wohlgeformt: ✅/❌
- [ ] XSD-Validierung: ✅/❌
- [ ] Schematron-Validierung: ✅/❌

## Teil 4: Frontend Test
- [ ] Login funktioniert: ✅/❌
- [ ] Kunde angelegt: ✅/❌
- [ ] Rechnung erstellt: ✅/❌
- [ ] PDF-Download: ✅/❌
- [ ] PDF kann geöffnet werden: ✅/❌

## Gefundene Probleme
1. ____________________________________________
2. ____________________________________________

## Notizen
____________________________________________
____________________________________________
```

---

## 🚀 Nächste Schritte nach erfolgreichen Tests

1. **Wenn alles funktioniert:**
   - ✅ Issue #9 als "Verified" markieren
   - ✅ Phase 5 (UX-Optimierung) beginnen
   - ✅ Dokumentation erweitern

2. **Bei Problemen:**
   - 🐛 Issues dokumentieren
   - 🔧 Fixes priorisieren
   - 🧪 Tests erweitern

---

## 📚 Hilfreiche Ressourcen

- **ZUGFeRD-Spezifikation:** `/docs/ZUGFERD_CONFORMANCE.md`
- **API-Dokumentation:** `/docs/API_SPECIFICATION.md`
- **XSD-Schema:** `/schemas/D16B SCRDM (Subset) CII/` (offizielles UN/CEFACT CII Schema)
- **Schematron-Rules:** `/schemas/en16931-schematron/` (offizielle EN16931 Validierung)

---

**Viel Erfolg beim Testen morgen! 🎯**
