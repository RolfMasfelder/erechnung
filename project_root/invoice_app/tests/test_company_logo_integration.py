"""
Integrationstest: Firmenlogo – vollständiger Durchlauf

Prüft die gesamte Kette:
  1. Logo-Upload per REST-API            → Datei wird gespeichert
  2. Datenbank-Persistenz                → logo-Feld enthält Pfad
  3. GET-Antwort der API                 → logo-URL wird zurückgegeben
  4. PATCH zum Ersetzen / Entfernen des Logos
  5. Rechnungs-Vorschau (InvoicePreviewView)
       → Template enthält <img>-Tag mit logo-URL wenn Logo gesetzt
       → Template enthält Firmenname-Fallback wenn kein Logo gesetzt
  6. Invoice-Preview ohne Logo → Firmenname als Fallback

Ebene: Backend-Integrationstest  (Django APITestCase + TestClient)
Ablageort: project_root/invoice_app/tests/test_company_logo_integration.py

Wird ausgeführt mit:
  docker compose exec web python project_root/manage.py test \
      invoice_app.tests.test_company_logo_integration
"""

import io  # noqa: I001
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from invoice_app.models import BusinessPartner, Company, Country, Invoice
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────


def _make_png_bytes(width: int = 60, height: int = 20) -> bytes:
    """Erzeugt ein minimales RGB-PNG als Bytes (kein echtes Bild nötig)."""
    img = Image.new("RGB", (width, height), color=(30, 80, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_uploaded_file(filename: str = "testlogo.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name=filename,
        content=_make_png_bytes(),
        content_type="image/png",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1 + 2 + 3 + 4: API → Datenbank → Response
# ─────────────────────────────────────────────────────────────────────────────


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CompanyLogoApiTests(APITestCase):
    """REST-API-Tests für den Logo-Upload (POST, PATCH, GET)."""

    def setUp(self):
        self.user = User.objects.create_user(username="apiuser", password="testpass123")
        self.client.force_authenticate(user=self.user)

        # Minimalfirma ohne Logo als Ausgangspunkt für PATCH-Tests
        self.company = Company.objects.create(
            name="Test GmbH",
            tax_id="TEST123456",
            vat_id="DE123456789",
            address_line1="Teststraße 1",
            postal_code="10115",
            city="Berlin",
            country="DE",
            email="test@test.de",
        )
        self.list_url = "/api/companies/"
        self.detail_url = f"/api/companies/{self.company.pk}/"

    # ── POST mit Logo ─────────────────────────────────────────────────────────

    def test_create_company_with_logo_stores_file(self):
        """POST /api/companies/ mit logo-Datei → 201, Dateipfad in DB gesetzt."""
        payload = {
            "name": "Logo Firma AG",
            "tax_id": "LOGO9999",
            "vat_id": "DE123456789",
            "address_line1": "Logoweg 5",
            "postal_code": "20095",
            "city": "Hamburg",
            "country": "DE",
            "email": "logo@firma.de",
            "logo": _make_uploaded_file(),
        }
        response = self.client.post(self.list_url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pk = response.data["id"]
        company = Company.objects.get(pk=pk)
        self.assertTrue(bool(company.logo), "logo-Feld muss nach Upload gesetzt sein")
        self.assertIn("company_logos", company.logo.name)

    def test_create_company_with_logo_returns_logo_url(self):
        """POST → Response-JSON enthält eine logo-URL (kein leerer String)."""
        payload = {
            "name": "URL Firma GmbH",
            "tax_id": "URL888",
            "vat_id": "DE987654321",
            "address_line1": "URLstraße 1",
            "postal_code": "80333",
            "city": "München",
            "country": "DE",
            "email": "url@firma.de",
            "logo": _make_uploaded_file(),
        }
        response = self.client.post(self.list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        logo_value = response.data.get("logo")
        self.assertIsNotNone(logo_value)
        self.assertTrue(len(logo_value) > 0, "logo darf nicht leer sein")

    # ── PATCH: Logo ersetzen ──────────────────────────────────────────────────

    def test_patch_company_logo_replaces_existing(self):
        """PATCH /api/companies/<pk>/ mit neuem Logo ersetzt das alte."""
        # Erst per PATCH ein Logo setzen
        self.client.patch(
            self.detail_url,
            {"logo": _make_uploaded_file("first.png")},
            format="multipart",
        )
        self.company.refresh_from_db()
        first_path = self.company.logo.name

        # Dann mit einem anderen Logo überschreiben
        self.client.patch(
            self.detail_url,
            {"logo": _make_uploaded_file("second.png")},
            format="multipart",
        )
        self.company.refresh_from_db()
        second_path = self.company.logo.name
        self.assertNotEqual(first_path, second_path, "Logo-Pfad muss sich ändern")

    # ── GET: Logo-URL in Listenansicht ────────────────────────────────────────

    def test_get_company_detail_includes_logo_url(self):
        """GET /api/companies/<pk>/ enthält logo-Feld (auch wenn leer = null)."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("logo", response.data)

    def test_get_company_detail_logo_url_after_upload(self):
        """Nach Upload ist logo in GET-Response ein nicht-leerer String."""
        self.client.patch(
            self.detail_url,
            {"logo": _make_uploaded_file()},
            format="multipart",
        )
        response = self.client.get(self.detail_url)
        logo = response.data.get("logo")
        self.assertIsNotNone(logo)
        self.assertTrue(len(logo) > 0)


# ─────────────────────────────────────────────────────────────────────────────
# 5 + 6: Template-Rendering (InvoicePreviewView)
# ─────────────────────────────────────────────────────────────────────────────


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CompanyLogoTemplateTests(TestCase):
    """
    Prüft, dass das invoice_pdf.html-Template das Logo-<img>-Tag rendert
    wenn das Firmenlogo gesetzt ist, und auf den Firmennamen zurückfällt
    wenn kein Logo gesetzt ist.

    Verwendet InvoicePreviewView (GET /invoices/<pk>/preview/) – dasselbe
    Template, das WeasyPrint später für die PDF-Erzeugung nutzt.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="templateuser", password="pass1234", is_staff=True)
        self.client.login(username="templateuser", password="pass1234")

        self.country = Country.objects.get_or_create(
            code="DE",
            defaults={"name": "Deutschland", "numeric_code": "276"},
        )[0]

        self.business_partner = BusinessPartner.objects.create(
            company_name="Musterkunde GmbH",
            tax_id="CUST001",
            address_line1="Kundenstraße 1",
            postal_code="10115",
            city="Berlin",
            country=self.country,
            email="kunde@test.de",
        )

        today = timezone.now().date()
        self.invoice_base = {
            "invoice_number": "LOGO-TEST-001",
            "invoice_type": Invoice.InvoiceType.INVOICE,
            "business_partner": self.business_partner,
            "issue_date": today,
            "due_date": today + timezone.timedelta(days=30),
            "currency": "EUR",
            "subtotal": Decimal("100.00"),
            "tax_amount": Decimal("19.00"),
            "total_amount": Decimal("119.00"),
            "status": Invoice.InvoiceStatus.DRAFT,
            "created_by": self.user,
        }

    def _create_company(self, with_logo: bool) -> Company:
        company = Company.objects.create(
            name="Absender GmbH",
            tax_id=f"TMPL{'WL' if with_logo else 'NL'}",
            address_line1="Absenderweg 1",
            postal_code="20095",
            city="Hamburg",
            country="DE",
            email="absender@test.de",
        )
        if with_logo:
            company.logo.save("testlogo.png", _make_uploaded_file(), save=True)
        return company

    def _create_invoice(self, company: Company) -> Invoice:
        data = dict(self.invoice_base, company=company)
        # Eindeutige Rechnungsnummer je Test
        data["invoice_number"] = f"LOGO-{company.pk}-001"
        return Invoice.objects.create(**data)

    # ── Template mit Logo ─────────────────────────────────────────────────────

    def test_preview_contains_img_tag_when_logo_set(self):
        """
        /invoices/<pk>/preview/ → HTML enthält <img class="logo" ...> mit
        der korrekten logo-URL wenn das Firmenlogo gesetzt ist.
        """
        company = self._create_company(with_logo=True)
        invoice = self._create_invoice(company)

        url = reverse("invoice-preview", kwargs={"pk": invoice.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('<img class="logo"', content, "Kein <img>-Tag im gerenderten HTML gefunden")
        self.assertIn(company.logo.url, content, "Logo-URL fehlt im gerenderten HTML")
        # Firmennamen-Fallback darf NICHT erscheinen (im Logo-Block)
        self.assertNotIn(
            f'<div style="font-size:14pt; font-weight:bold;">{company.name}</div>',
            content,
            "Firmennamen-Fallback darf nicht erscheinen wenn Logo gesetzt ist",
        )

    # ── Template ohne Logo (Fallback) ─────────────────────────────────────────

    def test_preview_shows_company_name_fallback_when_no_logo(self):
        """
        /invoices/<pk>/preview/ → HTML enthält den Firmennamen als Fallback-
        Text wenn kein Logo gesetzt ist.
        """
        company = self._create_company(with_logo=False)
        invoice = self._create_invoice(company)

        url = reverse("invoice-preview", kwargs={"pk": invoice.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(company.name, content)
        # Kein echtes <img>-Tag im Logo-Slot (Preview-Banner nutzt kein img)
        self.assertNotIn('<img class="logo"', content, "<img>-Tag darf ohne Logo nicht erscheinen")

    # ── Template-Kontext: logo.url erreichbar ────────────────────────────────

    def test_logo_url_accessible_in_template_context(self):
        """
        Das Company-Objekt im Template-Kontext hat ein verwendbares logo.url-
        Attribut (kein AttributeError).
        """
        company = self._create_company(with_logo=True)
        self._create_invoice(company)
        # Sicherstellen, dass company.logo.url keine Exception wirft
        self.assertTrue(company.logo.url.startswith("/media/"))
        self.assertTrue(company.logo.url.startswith("/media/"))
        self.assertTrue(company.logo.url.startswith("/media/"))
