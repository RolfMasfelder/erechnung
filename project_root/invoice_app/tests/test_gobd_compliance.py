"""
Tests for GoBD Compliance (Task 1.3).

Tests cover:
- Invoice locking (auto-lock on SENT/PAID, manual lock check)
- Locked invoice protection (no modification, GoBDViolationError)
- Content hash calculation + verification
- Soft-delete (retention period, archiving)
- Cancellation (credit note creation)
- AuditLog hash chain (entry_hash, previous_entry_hash, verification)
- IntegrityService (report generation, violation detection)
- Compliance API endpoints
- Management command
"""

from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from invoice_app.api.exceptions import GoBDViolationError
from invoice_app.models import AuditLog, BusinessPartner, Company, Country, Invoice, InvoiceLine, Product
from invoice_app.services.integrity_service import IntegrityService


User = get_user_model()


class GoBDTestMixin:
    """Shared test setup for GoBD tests."""

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
            address_line1="Teststr. 1",
            postal_code="12345",
            city="Berlin",
            country="Germany",
            tax_id="DE123456789",
            vat_id="DE123456789",
        )
        cls.partner = BusinessPartner.objects.create(
            company_name="Kunde GmbH",
            address_line1="Kundenstr. 1",
            postal_code="54321",
            city="München",
            country=cls.country_de,
        )
        cls.product = Product.objects.create(
            name="Test Produkt",
            product_code="TP001",
            base_price=Decimal("100.00"),
            default_tax_rate=Decimal("19.00"),
        )
        cls.user = User.objects.create_user(
            username="gobd_test_user",
            password="testpass123",
        )

    def _create_draft_invoice(self, **kwargs):
        """Create a DRAFT invoice with a line item."""
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
            description="Test Produkt",
            quantity=Decimal("2"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
        )
        return invoice


# ─── Invoice Locking Tests ──────────────────────────────────────────────────


class InvoiceLockingTests(GoBDTestMixin, TestCase):
    """Test auto-locking of invoices on status transitions."""

    def test_draft_invoice_is_not_locked(self):
        """DRAFT invoices should not be locked."""
        invoice = self._create_draft_invoice()
        self.assertFalse(invoice.is_locked)
        self.assertIsNone(invoice.locked_at)

    def test_auto_lock_on_sent(self):
        """Invoice should auto-lock when status changes to SENT."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()

        invoice.refresh_from_db()
        self.assertTrue(invoice.is_locked)
        self.assertIsNotNone(invoice.locked_at)
        self.assertEqual(invoice.lock_reason, "SENT")

    def test_auto_lock_on_paid(self):
        """Invoice should auto-lock when status changes to PAID."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.PAID
        invoice.save()

        invoice.refresh_from_db()
        self.assertTrue(invoice.is_locked)
        self.assertEqual(invoice.lock_reason, "PAID")

    def test_locked_invoice_blocks_modification(self):
        """Modifying a locked invoice should raise GoBDViolationError."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()

        invoice.refresh_from_db()
        invoice.notes = "Versuch einer Änderung"
        with self.assertRaises(GoBDViolationError):
            invoice.save()

    def test_locked_invoice_allows_cancellation(self):
        """Locked invoices can have their status changed to CANCELLED."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()

        invoice.refresh_from_db()
        invoice.status = Invoice.InvoiceStatus.CANCELLED
        invoice.save(_skip_lock_check=True)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.InvoiceStatus.CANCELLED)


# ─── Content Hash Tests ─────────────────────────────────────────────────────


class ContentHashTests(GoBDTestMixin, TestCase):
    """Test content hash calculation and verification."""

    def test_content_hash_set_on_lock(self):
        """Content hash should be calculated when invoice is locked."""
        invoice = self._create_draft_invoice()
        self.assertEqual(invoice.content_hash, "")

        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()

        invoice.refresh_from_db()
        self.assertTrue(len(invoice.content_hash) == 64)  # SHA-256 hex digest

    def test_content_hash_is_deterministic(self):
        """Same invoice should always produce same hash."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        hash1 = invoice.calculate_content_hash()
        hash2 = invoice.calculate_content_hash()
        self.assertEqual(hash1, hash2)

    def test_verify_integrity_passes(self):
        """Integrity check should pass for unmodified invoice."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        is_valid, error = invoice.verify_integrity()
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_verify_integrity_detects_tampering(self):
        """Integrity check should fail if data was tampered with."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        # Tamper directly in DB (bypass save() lock check)
        Invoice.objects.filter(pk=invoice.pk).update(subtotal=Decimal("99999.99"))
        invoice.refresh_from_db()

        is_valid, error = invoice.verify_integrity()
        self.assertFalse(is_valid)
        self.assertIn("Integritätsverletzung", error)

    def test_no_hash_on_draft(self):
        """Draft invoices should not have a content hash."""
        invoice = self._create_draft_invoice()
        self.assertEqual(invoice.content_hash, "")

    def test_verify_integrity_no_hash_is_valid(self):
        """Invoice without hash (draft) should pass verification."""
        invoice = self._create_draft_invoice()
        is_valid, error = invoice.verify_integrity()
        self.assertTrue(is_valid)


# ─── Retention & Soft-Delete Tests ───────────────────────────────────────────


class RetentionTests(GoBDTestMixin, TestCase):
    """Test 10-year retention and soft-delete."""

    def test_retention_auto_set(self):
        """Retention should be auto-set to ~10 years from issue_date."""
        invoice = self._create_draft_invoice()
        invoice.refresh_from_db()

        self.assertIsNotNone(invoice.retention_until)
        # Should be approximately 10 years from now
        expected = invoice.issue_date + timedelta(days=3653)
        self.assertEqual(invoice.retention_until, expected)

    def test_draft_can_be_hard_deleted(self):
        """DRAFT invoices (not locked) can be truly deleted."""
        invoice = self._create_draft_invoice()
        pk = invoice.pk
        invoice.delete()
        self.assertFalse(Invoice.objects.filter(pk=pk).exists())

    def test_sent_invoice_deletion_blocked_in_retention(self):
        """SENT invoice within retention period cannot be deleted at all."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        pk = invoice.pk

        # Should raise GoBDViolationError within retention period
        with self.assertRaises(GoBDViolationError):
            invoice.delete()

        # Still in DB, unarchived
        self.assertTrue(Invoice.objects.filter(pk=pk).exists())

    def test_sent_invoice_soft_deleted_after_retention(self):
        """SENT invoice after retention period is archived (soft-delete)."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        # Set retention to the past to allow soft-delete
        Invoice.objects.filter(pk=invoice.pk).update(retention_until=timezone.now().date() - timedelta(days=1))
        invoice.refresh_from_db()

        pk = invoice.pk
        invoice.delete()

        # Should still exist, but archived
        invoice.refresh_from_db()
        self.assertTrue(invoice.is_archived)
        self.assertIsNotNone(invoice.archived_at)
        self.assertTrue(Invoice.objects.filter(pk=pk).exists())

    def test_deletion_blocked_within_retention(self):
        """Cannot hard-delete invoice within retention period."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        # Verify retention_until is in the future
        self.assertGreater(invoice.retention_until, timezone.now().date())

    def test_deletion_blocked_default_true(self):
        """Default deletion_blocked should be True."""
        invoice = self._create_draft_invoice()
        self.assertTrue(invoice.deletion_blocked)


# ─── Cancellation Tests ─────────────────────────────────────────────────────


class CancellationTests(GoBDTestMixin, TestCase):
    """Test GoBD-compliant invoice cancellation."""

    def test_cancel_creates_credit_note(self):
        """Cancelling should create a credit note."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        credit_note = invoice.cancel(user=self.user, reason="Fehlrechnung")

        self.assertIsNotNone(credit_note)
        self.assertEqual(credit_note.invoice_type, Invoice.InvoiceType.CREDIT_NOTE)
        self.assertEqual(credit_note.total_amount, -invoice.total_amount)
        self.assertEqual(credit_note.business_partner, invoice.business_partner)
        self.assertIn("Storno", credit_note.notes)

    def test_cancel_marks_original_as_cancelled(self):
        """Original invoice should be marked CANCELLED."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        credit_note = invoice.cancel(user=self.user)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.InvoiceStatus.CANCELLED)
        self.assertEqual(invoice.cancelled_by, credit_note)

    def test_cancel_already_cancelled_raises_error(self):
        """Cancelling an already cancelled invoice should raise error."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        invoice.cancel(user=self.user)
        invoice.refresh_from_db()

        from invoice_app.api.exceptions import InvoiceStatusError

        with self.assertRaises(InvoiceStatusError):
            invoice.cancel(user=self.user)

    def test_credit_note_is_locked(self):
        """Credit note should be auto-locked (status SENT)."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        credit_note = invoice.cancel(user=self.user)
        self.assertTrue(credit_note.is_locked)


# ─── AuditLog Hash Chain Tests ──────────────────────────────────────────────


class AuditLogHashChainTests(TestCase):
    """Test AuditLog hash chain integrity."""

    def test_entry_hash_set_on_log_action(self):
        """AuditLog.log_action should set entry_hash."""
        entry = AuditLog.log_action(
            action=AuditLog.ActionType.CREATE,
            description="Test entry",
        )
        self.assertTrue(len(entry.entry_hash) == 64)

    def test_hash_chain_links(self):
        """Second entry should reference first entry's hash."""
        entry1 = AuditLog.log_action(
            action=AuditLog.ActionType.CREATE,
            description="First entry",
        )
        entry2 = AuditLog.log_action(
            action=AuditLog.ActionType.UPDATE,
            description="Second entry",
        )

        self.assertEqual(entry2.previous_entry_hash, entry1.entry_hash)

    def test_hash_is_deterministic(self):
        """Same entry data should produce same hash."""
        entry = AuditLog.log_action(
            action=AuditLog.ActionType.CREATE,
            description="Deterministic test",
        )
        recalculated = entry.calculate_entry_hash()
        self.assertEqual(entry.entry_hash, recalculated)

    def test_verify_chain_passes(self):
        """Chain verification should pass for unmodified entries."""
        AuditLog.log_action(action=AuditLog.ActionType.CREATE, description="Entry 1")
        AuditLog.log_action(action=AuditLog.ActionType.UPDATE, description="Entry 2")
        AuditLog.log_action(action=AuditLog.ActionType.DELETE, description="Entry 3")

        violations = AuditLog.verify_chain()
        self.assertEqual(violations, [])

    def test_verify_chain_detects_tampering(self):
        """Chain verification should detect tampered entries."""
        entry = AuditLog.log_action(
            action=AuditLog.ActionType.CREATE,
            description="Original Entry",
        )

        # Tamper directly in DB
        AuditLog.objects.filter(pk=entry.pk).update(description="TAMPERED")

        violations = AuditLog.verify_chain()
        self.assertGreater(len(violations), 0)
        self.assertEqual(violations[0]["event_id"], str(entry.event_id))

    def test_compliance_entry_has_10_year_retention(self):
        """Compliance-relevant entries should have 10-year retention."""
        entry = AuditLog.log_action(
            action=AuditLog.ActionType.CREATE,
            description="Compliance entry",
        )
        self.assertTrue(entry.is_compliance_relevant)
        self.assertIsNotNone(entry.retention_until)
        # Should be approximately 10 years from now
        expected = timezone.now() + timedelta(days=3650)
        self.assertAlmostEqual(
            entry.retention_until.timestamp(),
            expected.timestamp(),
            delta=60,  # Allow 60 seconds tolerance
        )


# ─── IntegrityService Tests ─────────────────────────────────────────────────


class IntegrityServiceTests(GoBDTestMixin, TestCase):
    """Test the IntegrityService report generation."""

    def test_report_ok_when_no_violations(self):
        """Report should be OK when everything is clean."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()

        report = IntegrityService.generate_integrity_report()

        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["invoice_violations"], [])
        self.assertEqual(report["audit_chain_violations"], [])
        self.assertGreater(report["invoices_locked"], 0)

    def test_report_detects_invoice_tampering(self):
        """Report should detect tampered invoices."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        invoice.refresh_from_db()

        # Tamper in DB
        Invoice.objects.filter(pk=invoice.pk).update(subtotal=Decimal("99999.99"))

        report = IntegrityService.generate_integrity_report()

        self.assertEqual(report["status"], "VIOLATIONS_FOUND")
        self.assertGreater(len(report["invoice_violations"]), 0)

    def test_report_detects_audit_chain_tampering(self):
        """Report should detect tampered audit chain."""
        entry = AuditLog.log_action(
            action=AuditLog.ActionType.CREATE,
            description="Test entry",
        )
        AuditLog.objects.filter(pk=entry.pk).update(description="TAMPERED")

        report = IntegrityService.generate_integrity_report()

        self.assertEqual(report["status"], "VIOLATIONS_FOUND")
        self.assertGreater(len(report["audit_chain_violations"]), 0)

    def test_retention_summary(self):
        """Retention summary should include correct counts."""
        self._create_draft_invoice()

        summary = IntegrityService.get_retention_summary()

        self.assertIn("invoices_within_retention", summary)
        self.assertIn("audit_logs_within_retention", summary)
        self.assertGreaterEqual(summary["invoices_within_retention"], 1)


# ─── Compliance API Tests ───────────────────────────────────────────────────


class ComplianceAPITests(GoBDTestMixin, TestCase):
    """Test compliance API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username="gobd_admin",
            password="adminpass123",
        )
        self.regular_user = User.objects.create_user(
            username="gobd_regular",
            password="regularpass123",
        )

    def test_integrity_report_admin_access(self):
        """Integrity report should be accessible to admins."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/compliance/integrity-report/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("status", response.data)

    def test_integrity_report_denied_for_regular_user(self):
        """Integrity report should be denied for non-admins."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/compliance/integrity-report/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retention_summary_admin_access(self):
        """Retention summary should be accessible to admins."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/compliance/retention-summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("invoices_within_retention", response.data)

    def test_retention_summary_denied_unauthenticated(self):
        """Retention summary should require authentication."""
        response = self.client.get("/api/compliance/retention-summary/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── Cancel API Tests ───────────────────────────────────────────────────────


class CancelAPITests(GoBDTestMixin, TestCase):
    """Test invoice cancellation via API."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_cancel_via_api(self):
        """Cancel endpoint should create credit note."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()

        response = self.client.post(
            f"/api/invoices/{invoice.pk}/cancel/",
            {"reason": "Fehlerhaft"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("credit_note_id", response.data)
        self.assertIn("credit_note_number", response.data)

    def test_cancel_already_cancelled_returns_error(self):
        """Cancelling an already cancelled invoice should return error."""
        invoice = self._create_draft_invoice()
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()

        # First cancel
        self.client.post(f"/api/invoices/{invoice.pk}/cancel/", format="json")

        # Second cancel should fail
        response = self.client.post(f"/api/invoices/{invoice.pk}/cancel/", format="json")
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT])


# ─── Management Command Tests ───────────────────────────────────────────────


class GoBDAuditCommandTests(GoBDTestMixin, TestCase):
    """Test the gobd_audit management command."""

    def test_command_runs_successfully(self):
        """Command should run without errors when no violations."""
        out = StringIO()
        call_command("gobd_audit", stdout=out)
        output = out.getvalue()
        self.assertIn("GoBD Compliance Audit", output)
        self.assertIn("Alle Prüfungen bestanden", output)

    def test_command_json_output(self):
        """Command --json flag should produce valid JSON."""
        out = StringIO()
        call_command("gobd_audit", "--json", stdout=out)
        output = out.getvalue()
        # Should contain JSON
        self.assertIn('"status"', output)

    def test_command_with_retention_flag(self):
        """Command --retention flag should show retention info."""
        out = StringIO()
        call_command("gobd_audit", "--retention", stdout=out)
        output = out.getvalue()
        self.assertIn("Aufbewahrungsfristen", output)

    def test_command_creates_audit_log(self):
        """Running the command should create an audit log entry."""
        count_before = AuditLog.objects.count()
        out = StringIO()
        call_command("gobd_audit", stdout=out)
        count_after = AuditLog.objects.count()
        self.assertGreater(count_after, count_before)


# ─── Invoice Serializer GoBD Fields Tests ────────────────────────────────────


class InvoiceSerializerGoBDTests(GoBDTestMixin, TestCase):
    """Test that GoBD fields are exposed in the API as read-only."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_gobd_fields_in_response(self):
        """GoBD fields should appear in invoice detail response."""
        invoice = self._create_draft_invoice()
        response = self.client.get(f"/api/invoices/{invoice.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("is_locked", response.data)
        self.assertIn("content_hash", response.data)
        self.assertIn("retention_until", response.data)
        self.assertIn("is_archived", response.data)

    def test_gobd_fields_are_read_only(self):
        """GoBD fields should not be writable via API."""
        invoice = self._create_draft_invoice()
        self.client.patch(
            f"/api/invoices/{invoice.pk}/",
            {"is_locked": True, "content_hash": "fake_hash"},
            format="json",
        )

        invoice.refresh_from_db()
        # is_locked should not have been set to True by API
        self.assertFalse(invoice.is_locked)
        self.assertEqual(invoice.content_hash, "")
