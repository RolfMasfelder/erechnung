# Implementierungsplan: PDF & XML Download-Funktionalität

**Branch:** `feature/download`
**Datum:** 10. Februar 2026
**Status:** PLANUNG

---

## 📋 Übersicht

Die Frontend-Buttons "PDF herunterladen" und "XML herunterladen" in der Invoice-Detailansicht (z.B. `http://192.168.178.200/invoices/41`) sind bereits implementiert, aber die Backend-API-Endpoints fehlen noch.

### Aktueller Stand

**✅ Frontend (Vue.js) - FERTIG:**
- Buttons in `InvoiceDetailView.vue` vorhanden
- Service-Methoden implementiert:
  - `invoiceService.downloadPDF(id)` → GET `/invoices/${id}/download_pdf/`
  - `invoiceService.downloadXML(id)` → GET `/invoices/${id}/download_xml/`
- View-Methoden erstellen Download mit Blob URL

**✅ Backend - TEILWEISE FERTIG:**
- Invoice-Modell hat FileFields: `pdf_file`, `xml_file`
- `InvoiceService.generate_invoice_files()` generiert PDF/XML
- `generate_pdf` Action existiert (POST für Generierung)

**❌ Backend - FEHLT:**
- `download_pdf` Action (GET) für tatsächlichen Download
- `download_xml` Action (GET) für tatsächlichen Download
- Backend-Tests für die neuen Endpoints

---

## 🎯 Implementierungsschritte

### Phase 1: Backend API-Endpoints (2-3h)

#### 1.1 Download PDF Endpoint
**Datei:** `project_root/invoice_app/api/rest_views.py`

```python
@swagger_auto_schema(
    responses={
        200: openapi.Response("PDF file", schema=openapi.Schema(type=openapi.TYPE_FILE)),
        404: openapi.Response("PDF not found")
    },
    operation_description="Download PDF file for the invoice"
)
@action(detail=True, methods=["get"], url_path="download_pdf")
def download_pdf(self, request, pk=None):
    """
    Download the PDF file for an invoice.
    Automatically generates the PDF if it doesn't exist.
    """
    invoice = self.get_object()

    # Check if PDF file exists
    if not invoice.pdf_file or not invoice.pdf_file.storage.exists(invoice.pdf_file.name):
        # Auto-generate if missing
        try:
            from invoice_app.services.invoice_service import InvoiceService
            invoice_service = InvoiceService()
            result = invoice_service.generate_invoice_files(invoice, zugferd_profile="BASIC")
        except Exception as e:
            logger.error(f"Failed to generate PDF for invoice {invoice.id}: {str(e)}")
            return Response(
                {"error": f"PDF not found and generation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Serve the file
    try:
        pdf_path = invoice.pdf_file.path
        return FileResponse(
            open(pdf_path, 'rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=f"invoice_{invoice.invoice_number}.pdf"
        )
    except Exception as e:
        logger.error(f"Failed to serve PDF for invoice {invoice.id}: {str(e)}")
        return Response(
            {"error": f"Failed to serve PDF: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

#### 1.2 Download XML Endpoint
**Datei:** `project_root/invoice_app/api/rest_views.py`

```python
@swagger_auto_schema(
    responses={
        200: openapi.Response("XML file", schema=openapi.Schema(type=openapi.TYPE_FILE)),
        404: openapi.Response("XML not found")
    },
    operation_description="Download ZUGFeRD/Factur-X XML file for the invoice"
)
@action(detail=True, methods=["get"], url_path="download_xml")
def download_xml(self, request, pk=None):
    """
    Download the ZUGFeRD/Factur-X XML file for an invoice.
    Automatically generates the XML if it doesn't exist.
    """
    invoice = self.get_object()

    # Check if XML file exists
    if not invoice.xml_file or not invoice.xml_file.storage.exists(invoice.xml_file.name):
        # Auto-generate if missing
        try:
            from invoice_app.services.invoice_service import InvoiceService
            invoice_service = InvoiceService()
            result = invoice_service.generate_invoice_files(invoice, zugferd_profile="BASIC")
        except Exception as e:
            logger.error(f"Failed to generate XML for invoice {invoice.id}: {str(e)}")
            return Response(
                {"error": f"XML not found and generation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Serve the file
    try:
        xml_path = invoice.xml_file.path
        return FileResponse(
            open(xml_path, 'rb'),
            content_type='application/xml',
            as_attachment=True,
            filename=f"invoice_{invoice.invoice_number}.xml"
        )
    except Exception as e:
        logger.error(f"Failed to serve XML for invoice {invoice.id}: {str(e)}")
        return Response(
            {"error": f"Failed to serve XML: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

**Benötigte Imports:**
```python
from django.http import FileResponse
```

---

### Phase 2: Backend-Tests (1-2h)

**Datei:** `project_root/invoice_app/tests/test_api_invoice_download.py` (NEUE DATEI)

```python
import os
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from invoice_app.models import Invoice, Company, Customer
from decimal import Decimal

User = get_user_model()

class InvoiceDownloadAPITest(TestCase):
    """Test cases for Invoice PDF/XML download endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create test company
        self.company = Company.objects.create(
            name="Test Company",
            address="Test Street 1",
            city="Test City",
            postal_code="12345",
            country="DE",
            tax_number="DE123456789"
        )

        # Create test customer
        self.customer = Customer.objects.create(
            company_name="Customer Inc",
            address="Customer Street 1",
            city="Customer City",
            postal_code="54321",
            country="DE",
            tax_number="DE987654321"
        )

        # Create test invoice
        self.invoice = Invoice.objects.create(
            company=self.company,
            business_partner=self.customer,
            invoice_number="INV-2026-001",
            issue_date="2026-02-10",
            due_date="2026-03-10",
            currency="EUR",
            total_amount=Decimal("100.00"),
            status="sent",
            created_by=self.user
        )

    def test_download_pdf_with_existing_file(self):
        """Test PDF download when file exists."""
        # Generate PDF first
        pdf_url = reverse('invoice-generate-pdf', kwargs={'pk': self.invoice.id})
        self.client.post(pdf_url)

        # Now download
        download_url = reverse('invoice-download-pdf', kwargs={'pk': self.invoice.id})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('invoice_INV-2026-001.pdf', response['Content-Disposition'])

    def test_download_pdf_auto_generate_when_missing(self):
        """Test PDF download auto-generates when file doesn't exist."""
        download_url = reverse('invoice-download-pdf', kwargs={'pk': self.invoice.id})
        response = self.client.get(download_url)

        # Should auto-generate and return PDF
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # Verify file was created in model
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.pdf_file)

    def test_download_xml_with_existing_file(self):
        """Test XML download when file exists."""
        # Generate XML first
        pdf_url = reverse('invoice-generate-pdf', kwargs={'pk': self.invoice.id})
        self.client.post(pdf_url)

        # Now download
        download_url = reverse('invoice-download-xml', kwargs={'pk': self.invoice.id})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/xml')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('invoice_INV-2026-001.xml', response['Content-Disposition'])

    def test_download_xml_auto_generate_when_missing(self):
        """Test XML download auto-generates when file doesn't exist."""
        download_url = reverse('invoice-download-xml', kwargs={'pk': self.invoice.id})
        response = self.client.get(download_url)

        # Should auto-generate and return XML
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/xml')

        # Verify file was created in model
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.xml_file)

    def test_download_pdf_unauthenticated(self):
        """Test PDF download requires authentication."""
        self.client.logout()
        download_url = reverse('invoice-download-pdf', kwargs={'pk': self.invoice.id})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_download_xml_unauthenticated(self):
        """Test XML download requires authentication."""
        self.client.logout()
        download_url = reverse('invoice-download-xml', kwargs={'pk': self.invoice.id})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_download_pdf_nonexistent_invoice(self):
        """Test PDF download with non-existent invoice returns 404."""
        download_url = reverse('invoice-download-pdf', kwargs={'pk': 99999})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_xml_nonexistent_invoice(self):
        """Test XML download with non-existent invoice returns 404."""
        download_url = reverse('invoice-download-xml', kwargs={'pk': 99999})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

---

### Phase 3: Dokumentation aktualisieren (30min)

#### 3.1 API-Dokumentation
**Datei:** `docs/API_SPECIFICATION.md`

Abschnitt hinzufügen:

```markdown
### Download PDF

**Endpoint:** `GET /api/invoices/{id}/download_pdf/`

**Beschreibung:** Lädt die PDF-Datei einer Rechnung herunter. Generiert automatisch das PDF, falls es noch nicht existiert.

**Response:**
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="invoice_{invoice_number}.pdf"`

**Status Codes:**
- 200: Erfolgreich
- 401: Nicht authentifiziert
- 404: Rechnung nicht gefunden
- 500: Fehler bei Generierung/Download

### Download XML

**Endpoint:** `GET /api/invoices/{id}/download_xml/`

**Beschreibung:** Lädt die ZUGFeRD/Factur-X XML-Datei einer Rechnung herunter. Generiert automatisch das XML, falls es noch nicht existiert.

**Response:**
- Content-Type: `application/xml`
- Content-Disposition: `attachment; filename="invoice_{invoice_number}.xml"`

**Status Codes:**
- 200: Erfolgreich
- 401: Nicht authentifiziert
- 404: Rechnung nicht gefunden
- 500: Fehler bei Generierung/Download
```

#### 3.2 Progress Protocol aktualisieren
**Datei:** `docs/PROGRESS_PROTOCOL.md`

Neuen Eintrag hinzufügen mit Datum, Issue-Beschreibung, und Implementierungsdetails.

---

### Phase 4: E2E Tests (Optional, 1-2h)

**Datei:** `frontend/e2e/invoice-download.spec.js` (NEUE DATEI)

```javascript
import { test, expect } from '@playwright/test'

test.describe('Invoice Download Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('http://localhost:5173/login')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'testpass123')
    await page.click('button[type="submit"]')
    await page.waitForURL('http://localhost:5173/')
  })

  test('should download PDF from invoice detail view', async ({ page }) => {
    // Navigate to invoice detail
    await page.goto('http://localhost:5173/invoices')
    await page.click('tr:first-child a[href*="/invoices/"]')

    // Wait for invoice detail to load
    await expect(page.locator('h1')).toContainText('Rechnung')

    // Click PDF download button
    const downloadPromise = page.waitForEvent('download')
    await page.click('button:has-text("PDF herunterladen")')

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/invoice.*\.pdf/)
  })

  test('should download XML from invoice detail view', async ({ page }) => {
    // Navigate to invoice detail
    await page.goto('http://localhost:5173/invoices')
    await page.click('tr:first-child a[href*="/invoices/"]')

    // Wait for invoice detail to load
    await expect(page.locator('h1')).toContainText('Rechnung')

    // Click XML download button
    const downloadPromise = page.waitForEvent('download')
    await page.click('button:has-text("XML herunterladen")')

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/invoice.*\.xml/)
  })

  test('should handle download error gracefully', async ({ page, context }) => {
    // Mock API to return error
    await context.route('**/api/invoices/*/download_pdf/', route => {
      route.fulfill({ status: 500, body: 'Server error' })
    })

    // Navigate to invoice detail
    await page.goto('http://localhost:5173/invoices')
    await page.click('tr:first-child a[href*="/invoices/"]')

    // Try to download (should fail gracefully)
    await page.click('button:has-text("PDF herunterladen")')

    // Check for error toast/message (adjust selector based on your error handling)
    await expect(page.locator('.toast, .alert')).toBeVisible({ timeout: 5000 })
  })
})
```

---

## 🧪 Testplan

### Backend-Tests
```bash
# Container-basiert
cd scripts && ./run_tests_docker.sh invoice_app.tests.test_api_invoice_download

# Lokal (falls venv aktiviert)
docker compose exec web python project_root/manage.py test invoice_app.tests.test_api_invoice_download
```

**Erwartete Ergebnisse:**
- ✅ 8/8 Tests bestehen
- ✅ Coverage > 90% für neue download-Methoden

### E2E Tests (Optional)
```bash
cd scripts && ./run_e2e_container.sh
```

**Erwartete Ergebnisse:**
- ✅ 3/3 neue E2E Tests bestehen
- ✅ Keine Regressionen in bestehenden Tests

---

## ⚠️ Edge Cases & Fehlerbehandlung

| Szenario | Verhalten |
|----------|-----------|
| PDF existiert | ✅ Direkt ausliefern |
| PDF fehlt | ⚠️ Auto-generieren, dann ausliefern |
| Generierung schlägt fehl | ❌ HTTP 500 mit Fehlermeldung |
| Datei nicht lesbar | ❌ HTTP 500 mit Fehlermeldung |
| Unauthentifiziert | ❌ HTTP 401 |
| Rechnung existiert nicht | ❌ HTTP 404 |
| XML fehlt | ⚠️ Auto-generieren (zusammen mit PDF) |

---

## 📦 Betroffene Dateien

### Änderungen (Modified)
- `project_root/invoice_app/api/rest_views.py` (2 neue Actions)
- `docs/API_SPECIFICATION.md` (Dokumentation)
- `docs/PROGRESS_PROTOCOL.md` (Projektfortschritt)

### Neu erstellt (Created)
- `project_root/invoice_app/tests/test_api_invoice_download.py` (Backend-Tests)
- `frontend/e2e/invoice-download.spec.js` (E2E Tests, optional)

### Keine Änderungen nötig
- ✅ Frontend (bereits implementiert)
- ✅ Invoice-Model (FileFields vorhanden)
- ✅ InvoiceService (Generierung vorhanden)

---

## 🚀 Deployment-Checkliste

### Entwicklung (Docker Compose)
- [ ] Backend-Endpoints implementiert
- [ ] Backend-Tests bestehen (8/8)
- [ ] Manuelle Tests in Development-Umgebung
- [ ] Dokumentation aktualisiert

### Kubernetes (k3s auf 192.168.178.80)
- [ ] Code in Main gemerged
- [ ] Images neu gebaut und in lokale Registry gepusht
- [ ] Deployment aktualisiert (kubectl rollout restart)
- [ ] E2E-Smoke-Tests gegen k3s-Cluster (scripts/run_e2e_k3s.sh)
- [ ] Manueller Funktionstest auf http://192.168.178.200

---

## 📊 Aufwandsschätzung

| Phase | Aufwand | Priorität |
|-------|---------|-----------|
| Backend-Endpoints | 2-3h | 🔴 HOCH |
| Backend-Tests | 1-2h | 🔴 HOCH |
| Dokumentation | 30min | 🟡 MITTEL |
| E2E Tests | 1-2h | 🟢 NIEDRIG (optional) |
| **Gesamt** | **4-7h** | |

---

## ✅ Erfolgskriterien

1. ✅ Beide Download-Buttons funktionieren in Development und Kubernetes
2. ✅ PDF/XML werden korrekt heruntergeladen mit richtigen Dateinamen
3. ✅ Auto-Generierung funktioniert bei fehlenden Dateien
4. ✅ Alle Backend-Tests bestehen (8/8)
5. ✅ Dokumentation ist aktuell
6. ✅ Keine Regressionen in bestehenden Tests

---

## 🔗 Referenzen

- **Frontend-Code:** `frontend/src/views/InvoiceDetailView.vue`
- **Frontend-Service:** `frontend/src/api/services/invoiceService.js`
- **Backend-ViewSet:** `project_root/invoice_app/api/rest_views.py`
- **Invoice-Model:** `project_root/invoice_app/models/invoice_models.py`
- **Invoice-Service:** `project_root/invoice_app/services/invoice_service.py`
- **PDF-Generator:** `project_root/invoice_app/utils/pdf.py`
- **XML-Generator:** `project_root/invoice_app/utils/xml/`

---

## 📝 Nächste Schritte

1. ✅ Branch `feature/download` erstellt
2. ✅ Implementierungsplan erstellt
3. ⏳ Backend-Endpoints implementieren (Phase 1)
4. ⏳ Backend-Tests schreiben (Phase 2)
5. ⏳ Dokumentation aktualisieren (Phase 3)
6. ⏳ Manuell testen (Development)
7. ⏳ E2E Tests (Optional, Phase 4)
8. ⏳ Pull Request erstellen
9. ⏳ Code Review
10. ⏳ Merge in Main
11. ⏳ Deployment auf Kubernetes

---

**Erstellt:** 10. Februar 2026
**Autor:** AI Coding Agent (Claude Sonnet 4.5)
**Branch:** feature/download
**Tickets:** Keine (Internal Enhancement)
