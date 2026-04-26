"""
Tests for Credit Note / Invoice Cancellation (TODO 3.9).

Tests cover:
- Phase 1: TypeCode mapping (381), InvoiceReferencedDocument (BT-25), GS-prefix
- Phase 2: Line items negation, status validation (SENT/PAID only), PDF title
- Phase 4: API cancel flow, XML generation validation
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from invoice_app.api.exceptions import InvoiceStatusError
from invoice_app.models import BusinessPartner, Company, Country, Invoice, InvoiceLine, Product
from invoice_app.services.invoice_service import InvoiceService


User = get_user_model()


class CreditNoteTestMixin:
    """Shared test setup for credit note tests."""

    @classmethod
    def setUpTestData(cls):
        cls.country_de, _ = Country.objects.get_or_create(
            code="DE",
            defaults={
                "name": "Germany",
                "is_eu_member": True,
                "standard_vat_rate": Decimal("19.00"),
            },
        )
        cls.company = Company.objects.create(
            name="Test GmbH",
            legal_name="Test GmbH",
            address_line1="Teststr. 1",
            postal_code="12345",
            city="Berlin",
            country="Germany",
            tax_id="DE123456789",
            vat_id="DE123456789",
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
        )
        cls.partner = BusinessPartner.objects.create(
            company_name="Kunde GmbH",
            address_line1="Kundenstr. 1",
            postal_code="54321",
            city="München",
            country=cls.country_de,
            tax_id="DE987654321",
        )
        cls.product = Product.objects.create(
            name="Test Produkt",
            product_code="TP001",
            base_price=Decimal("100.00"),
            default_tax_rate=Decimal("19.00"),
        )
        cls.user = User.objects.create_user(
            username="credit_note_test_user",
            password="testpass123",
        )

    def _create_sent_invoice(self, **kwargs):
        """Create a SENT invoice with line items (locked, ready for cancellation)."""
        defaults = {
            "company": self.company,
            "business_partner": self.partner,
            "issue_date": timezone.now().date(),
            "due_date": timezone.now().date() + timedelta(days=30),
            "status": Invoice.InvoiceStatus.DRAFT,
            "created_by": self.user,
        }
        defaults.update(kwargs)
        invoice = Invoice.objects.create(**defaults)

        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Beratungsleistung",
            quantity=Decimal("5"),
            unit_price=Decimal("200.00"),
            tax_rate=Decimal("19.00"),
        )
        InvoiceLine.objects.create(
            invoice=invoice,
            description="Reisekosten",
            product_code="RK001",
            quantity=Decimal("1"),
            unit_price=Decimal("150.00"),
            tax_rate=Decimal("19.00"),
        )

        # Transition to SENT (auto-locks)
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()
        return invoice


# ─── Phase 1: XML/ZUGFeRD-Konformität ──────────────────────────────────────


class CreditNoteInvoiceNumberTests(CreditNoteTestMixin, TestCase):
    """Test GS- prefix for credit note invoice numbers."""

    def test_credit_note_gets_gs_prefix(self):
        """Credit notes should have GS-YYYY-NNNN format."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        self.assertTrue(credit_note.invoice_number.startswith("GS-"))

    def test_original_invoice_keeps_inv_prefix(self):
        """Original invoices should keep INV- prefix."""
        invoice = self._create_sent_invoice()
        self.assertTrue(invoice.invoice_number.startswith("INV-"))

    def test_credit_note_number_contains_year(self):
        """Credit note number should contain the current year."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        year = str(timezone.now().year)
        self.assertIn(year, credit_note.invoice_number)


class TypeCodeMappingTests(CreditNoteTestMixin, TestCase):
    """Test TypeCode mapping in convert_model_to_dict."""

    def test_invoice_type_code_380(self):
        """Standard invoice should map to TypeCode 380."""
        invoice = self._create_sent_invoice()
        service = InvoiceService()
        data = service.convert_model_to_dict(invoice)

        self.assertEqual(data["type_code"], "380")

    def test_credit_note_type_code_381(self):
        """Credit note should map to TypeCode 381."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        service = InvoiceService()
        data = service.convert_model_to_dict(credit_note)

        self.assertEqual(data["type_code"], "381")


class InvoiceReferencedDocumentTests(CreditNoteTestMixin, TestCase):
    """Test BT-25 InvoiceReferencedDocument for credit notes."""

    def test_credit_note_has_invoice_referenced_document(self):
        """Credit note dict should contain reference to original invoice."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        service = InvoiceService()
        data = service.convert_model_to_dict(credit_note)

        self.assertIn("invoice_referenced_document", data)
        ref = data["invoice_referenced_document"]
        self.assertEqual(ref["issuer_assigned_id"], invoice.invoice_number)
        self.assertEqual(ref["issue_date"], invoice.issue_date.strftime("%Y%m%d"))

    def test_regular_invoice_has_no_invoice_referenced_document(self):
        """Regular invoice should not have InvoiceReferencedDocument."""
        invoice = self._create_sent_invoice()
        service = InvoiceService()
        data = service.convert_model_to_dict(invoice)

        self.assertNotIn("invoice_referenced_document", data)

    def test_credit_note_xml_contains_type_code_381(self):
        """Generated XML should contain TypeCode 381 for credit notes."""
        from invoice_app.utils.xml.generator import ZugferdXmlGenerator

        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        service = InvoiceService()
        data = service.convert_model_to_dict(credit_note)

        generator = ZugferdXmlGenerator(profile="COMFORT")
        xml_content = generator.generate_xml(data)

        self.assertIn("<ram:TypeCode>381</ram:TypeCode>", xml_content)

    def test_credit_note_xml_contains_invoice_referenced_document(self):
        """Generated XML should contain InvoiceReferencedDocument for credit notes."""
        from invoice_app.utils.xml.generator import ZugferdXmlGenerator

        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        service = InvoiceService()
        data = service.convert_model_to_dict(credit_note)

        generator = ZugferdXmlGenerator(profile="COMFORT")
        xml_content = generator.generate_xml(data)

        self.assertIn("InvoiceReferencedDocument", xml_content)
        self.assertIn(invoice.invoice_number, xml_content)


# ─── Phase 2: Geschäftslogik ───────────────────────────────────────────────


class CancelStatusValidationTests(CreditNoteTestMixin, TestCase):
    """Test that cancellation is only allowed from SENT or PAID status."""

    def test_cancel_from_sent_succeeds(self):
        """Cancelling a SENT invoice should work."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        self.assertIsNotNone(credit_note)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.InvoiceStatus.CANCELLED)

    def test_cancel_from_paid_succeeds(self):
        """Cancelling a PAID invoice should work."""
        invoice = self._create_sent_invoice()
        invoice.status = Invoice.InvoiceStatus.PAID
        invoice.save(_skip_lock_check=True)
        invoice.refresh_from_db()

        credit_note = invoice.cancel(user=self.user, reason="Test")
        self.assertIsNotNone(credit_note)

    def test_cancel_from_draft_fails(self):
        """Cancelling a DRAFT invoice should raise InvoiceStatusError."""
        invoice = Invoice.objects.create(
            company=self.company,
            business_partner=self.partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            status=Invoice.InvoiceStatus.DRAFT,
            created_by=self.user,
        )
        with self.assertRaises(InvoiceStatusError):
            invoice.cancel(user=self.user, reason="Test")

    def test_cancel_from_overdue_fails(self):
        """Cancelling an OVERDUE invoice should raise InvoiceStatusError."""
        invoice = self._create_sent_invoice()
        invoice.status = Invoice.InvoiceStatus.OVERDUE
        invoice.save(_skip_lock_check=True)
        invoice.refresh_from_db()

        with self.assertRaises(InvoiceStatusError):
            invoice.cancel(user=self.user, reason="Test")

    def test_cancel_already_cancelled_fails(self):
        """Cancelling an already cancelled invoice should raise InvoiceStatusError."""
        invoice = self._create_sent_invoice()
        invoice.cancel(user=self.user, reason="First cancel")
        invoice.refresh_from_db()

        with self.assertRaises(InvoiceStatusError):
            invoice.cancel(user=self.user, reason="Second cancel")


class CancelLineItemTests(CreditNoteTestMixin, TestCase):
    """Test that cancel() correctly copies and negates line items."""

    def test_credit_note_has_same_number_of_lines(self):
        """Credit note should have the same number of lines as the original."""
        invoice = self._create_sent_invoice()
        original_line_count = invoice.lines.count()

        credit_note = invoice.cancel(user=self.user, reason="Test")

        self.assertEqual(credit_note.lines.count(), original_line_count)

    def test_credit_note_lines_have_negative_quantities(self):
        """Credit note lines should have negative quantities."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        for line in credit_note.lines.all():
            self.assertLess(line.quantity, 0)

    def test_credit_note_lines_have_positive_unit_prices(self):
        """Credit note lines should keep positive unit prices."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        for line in credit_note.lines.all():
            self.assertGreater(line.unit_price, 0)

    def test_credit_note_lines_descriptions_match(self):
        """Credit note lines should have the same descriptions."""
        invoice = self._create_sent_invoice()
        original_descriptions = set(invoice.lines.values_list("description", flat=True))

        credit_note = invoice.cancel(user=self.user, reason="Test")
        cn_descriptions = set(credit_note.lines.values_list("description", flat=True))

        self.assertEqual(original_descriptions, cn_descriptions)

    def test_credit_note_total_is_negated(self):
        """Credit note total_amount should be the negated original."""
        invoice = self._create_sent_invoice()
        original_total = invoice.total_amount

        credit_note = invoice.cancel(user=self.user, reason="Test")

        self.assertEqual(credit_note.total_amount, -original_total)

    def test_credit_note_subtotal_matches_line_totals(self):
        """Credit note subtotal should match the sum of its line totals."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        sum_line_totals = sum(line.line_total for line in credit_note.lines.all())
        self.assertEqual(credit_note.subtotal, sum_line_totals)

    def test_credit_note_lines_keep_tax_category(self):
        """Credit note lines should keep the same tax_category."""
        invoice = self._create_sent_invoice()
        original_categories = list(invoice.lines.values_list("tax_category", flat=True).order_by("description"))

        credit_note = invoice.cancel(user=self.user, reason="Test")
        cn_categories = list(credit_note.lines.values_list("tax_category", flat=True).order_by("description"))

        self.assertEqual(original_categories, cn_categories)


class CancelCrossReferenceTests(CreditNoteTestMixin, TestCase):
    """Test cross-references between original invoice and credit note."""

    def test_original_cancelled_by_points_to_credit_note(self):
        """Original invoice's cancelled_by should point to the credit note."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        invoice.refresh_from_db()
        self.assertEqual(invoice.cancelled_by, credit_note)

    def test_credit_note_cancels_invoice_points_to_original(self):
        """Credit note's cancels_invoice should point to the original."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        self.assertEqual(credit_note.cancels_invoice, invoice)

    def test_credit_note_notes_contain_original_number(self):
        """Credit note notes should reference the original invoice number."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Fehlrechnung")

        self.assertIn(invoice.invoice_number, credit_note.notes)
        self.assertIn("Fehlrechnung", credit_note.notes)

    def test_credit_note_is_auto_locked(self):
        """Credit note with status SENT should be auto-locked."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        self.assertTrue(credit_note.is_locked)
        self.assertEqual(credit_note.status, Invoice.InvoiceStatus.SENT)


# ─── Phase 4: API Tests ────────────────────────────────────────────────────


class CancelAPITests(CreditNoteTestMixin, TestCase):
    """Test the /api/invoices/{id}/cancel/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_cancel_via_api_returns_credit_note_info(self):
        """POST /cancel/ should return credit note ID and number."""
        invoice = self._create_sent_invoice()
        response = self.client.post(
            f"/api/invoices/{invoice.id}/cancel/",
            {"reason": "Fehlrechnung"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("credit_note_id", response.data)
        self.assertIn("credit_note_number", response.data)
        self.assertTrue(response.data["credit_note_number"].startswith("GS-"))

    def test_cancel_draft_via_api_fails(self):
        """Cancelling a DRAFT invoice via API should fail."""
        invoice = Invoice.objects.create(
            company=self.company,
            business_partner=self.partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            status=Invoice.InvoiceStatus.DRAFT,
            created_by=self.user,
        )
        response = self.client.post(
            f"/api/invoices/{invoice.id}/cancel/",
            {"reason": "Test"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_cancel_already_cancelled_via_api_fails(self):
        """Cancelling an already cancelled invoice via API should fail."""
        invoice = self._create_sent_invoice()
        self.client.post(
            f"/api/invoices/{invoice.id}/cancel/",
            {"reason": "First"},
            format="json",
        )
        response = self.client.post(
            f"/api/invoices/{invoice.id}/cancel/",
            {"reason": "Second"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_api_response_includes_cross_references(self):
        """GET invoice detail should include cancellation cross-references."""
        invoice = self._create_sent_invoice()
        credit_note = invoice.cancel(user=self.user, reason="Test")

        # Check original invoice
        response = self.client.get(f"/api/invoices/{invoice.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cancelled_by_number"], credit_note.invoice_number)
        self.assertEqual(response.data["cancelled_by_id"], credit_note.id)

        # Check credit note
        response = self.client.get(f"/api/invoices/{credit_note.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cancels_invoice_number"], invoice.invoice_number)
        self.assertEqual(response.data["cancels_invoice_id"], invoice.id)
