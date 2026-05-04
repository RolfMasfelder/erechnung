"""
Tests for invoice e-mail delivery (3.5 E-Mail-Versand).

Uses Django's locmem backend (mail.outbox) — no real network traffic.
"""

from __future__ import annotations

import pytest
from django.core import mail
from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from invoice_app.models import AuditLog, Invoice
from invoice_app.services.email_service import (
    EmailDisabledError,
    InvoiceEmailService,
)
from invoice_app.tests.factories import GovernmentPartnerFactory, InvoiceFactory


pytestmark = pytest.mark.django_db


EMAIL_TEST_SETTINGS = {
    "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    "INVOICE_EMAIL_ENABLED": True,
    "DEFAULT_FROM_EMAIL": "rechnung@example.com",
}


@pytest.fixture(autouse=True)
def _email_test_settings(settings):
    """Apply locmem email backend + enabled flag to every test in this module."""
    for key, value in EMAIL_TEST_SETTINGS.items():
        setattr(settings, key, value)
    mail.outbox = []


# ── Service-level tests ──────────────────────────────────────────────────────


class TestInvoiceEmailService:
    """Direct tests against the service layer (bypassing the API)."""

    def test_send_invoice_uses_smtp_outbox(self, sent_invoice, admin_user):
        """A successful send produces exactly one Django outbox message."""
        result = InvoiceEmailService().send_invoice(
            sent_invoice,
            "kunde@example.com",
            user=admin_user,
        )

        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert msg.to == ["kunde@example.com"]
        assert sent_invoice.invoice_number in msg.subject
        # Default: PDF/A-3 only (XML is embedded inside the PDF, EN16931).
        assert len(msg.attachments) == 1
        assert msg.attachments[0][0].endswith(".pdf")
        assert result.recipient == "kunde@example.com"

    def test_send_invoice_xml_optional(self, sent_invoice, admin_user):
        """attach_xml=True ships the structured XML as a second attachment."""
        InvoiceEmailService().send_invoice(
            sent_invoice,
            "kunde@example.com",
            attach_xml=True,
            user=admin_user,
        )

        assert len(mail.outbox) == 1
        filenames = [a[0] for a in mail.outbox[0].attachments]
        assert len(filenames) == 2
        assert any(name.endswith(".pdf") for name in filenames)
        assert any(name.endswith(".xml") for name in filenames)

    def test_send_invoice_updates_tracking_fields(self, sent_invoice, admin_user):
        """last_emailed_at and last_email_recipient are persisted."""
        assert sent_invoice.last_emailed_at is None
        InvoiceEmailService().send_invoice(
            sent_invoice,
            "kunde@example.com",
            user=admin_user,
        )
        sent_invoice.refresh_from_db()
        assert sent_invoice.last_emailed_at is not None
        assert sent_invoice.last_email_recipient == "kunde@example.com"

    def test_send_invoice_writes_audit_log(self, sent_invoice, admin_user):
        """A SEND_EMAIL audit entry is recorded with recipient + counts."""
        before = AuditLog.objects.filter(action=AuditLog.ActionType.SEND_EMAIL).count()
        InvoiceEmailService().send_invoice(
            sent_invoice,
            "kunde@example.com",
            user=admin_user,
        )

        entries = AuditLog.objects.filter(
            action=AuditLog.ActionType.SEND_EMAIL,
            object_id=str(sent_invoice.pk),
        )
        assert entries.count() == before + 1
        entry = entries.latest("timestamp")
        assert entry.severity == AuditLog.Severity.MEDIUM
        assert entry.details["recipient"] == "kunde@example.com"
        assert entry.details["with_xml"] is False
        assert any(name.endswith(".pdf") for name in entry.details["attached_files"])

    def test_send_invoice_rejects_empty_recipient(self, sent_invoice, admin_user):
        """An empty recipient raises ValueError before any SMTP traffic."""
        with pytest.raises(ValueError):
            InvoiceEmailService().send_invoice(sent_invoice, "", user=admin_user)
        assert mail.outbox == []

    @override_settings(INVOICE_EMAIL_ENABLED=False)
    def test_send_invoice_kill_switch(self, sent_invoice, admin_user):
        """When INVOICE_EMAIL_ENABLED=False the service refuses to send."""
        with pytest.raises(EmailDisabledError):
            InvoiceEmailService().send_invoice(
                sent_invoice,
                "kunde@example.com",
                user=admin_user,
            )
        assert mail.outbox == []


# ── API-level tests ──────────────────────────────────────────────────────────


class TestSendEmailEndpoint:
    """Tests for POST /api/invoices/{id}/send_email/."""

    def test_send_email_endpoint_success(self, authenticated_admin_client, sent_invoice):
        """Endpoint responds 200 and produces an outbox message."""
        url = reverse("api-invoice-send-email", kwargs={"pk": sent_invoice.pk})
        response = authenticated_admin_client.post(
            url,
            {"recipient": "kunde@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recipient"] == "kunde@example.com"
        assert data["sent_at"] is not None
        assert len(mail.outbox) == 1

    def test_send_email_endpoint_missing_recipient(self, authenticated_admin_client, sent_invoice):
        """Missing recipient yields 400 without sending."""
        url = reverse("api-invoice-send-email", kwargs={"pk": sent_invoice.pk})
        response = authenticated_admin_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert mail.outbox == []

    def test_send_email_endpoint_drafts_auto_transition(self, authenticated_admin_client, draft_invoice):
        """A DRAFT invoice is auto-marked SENT (and locked) when emailed."""
        url = reverse("api-invoice-send-email", kwargs={"pk": draft_invoice.pk})
        response = authenticated_admin_client.post(
            url,
            {"recipient": "kunde@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        draft_invoice.refresh_from_db()
        assert draft_invoice.status == Invoice.InvoiceStatus.SENT
        assert draft_invoice.is_locked is True

    @override_settings(INVOICE_EMAIL_ENABLED=False)
    def test_send_email_endpoint_kill_switch_returns_503(self, authenticated_admin_client, sent_invoice):
        """Disabled kill switch surfaces as 503 to the client."""
        url = reverse("api-invoice-send-email", kwargs={"pk": sent_invoice.pk})
        response = authenticated_admin_client.post(
            url,
            {"recipient": "kunde@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert mail.outbox == []


# ── XRechnung E-Mail tests ──────────────────────────────────────────────────


class TestSendXRechnungEndpoint:
    """Tests for POST /api/invoices/{id}/send_xrechnung/."""

    @pytest.fixture
    def gov_invoice(self, company):
        """SENT invoice with a GOVERNMENT partner that has an e-mail address and an XML file."""
        partner = GovernmentPartnerFactory(email="behoerde@example.de")
        invoice = InvoiceFactory(
            company=company,
            business_partner=partner,
            status=Invoice.InvoiceStatus.SENT,
            buyer_reference=partner.leitweg_id,
        )
        stub_xml = b"<?xml version='1.0'?><Invoice>stub</Invoice>"
        invoice.xml_file.save(
            f"{invoice.invoice_number}.xml",
            ContentFile(stub_xml),
            save=False,   # don't trigger model.save() → avoids GoBD lock check
        )
        Invoice.objects.filter(pk=invoice.pk).update(xml_file=invoice.xml_file.name)
        invoice.refresh_from_db()
        return invoice

    @pytest.fixture
    def business_invoice(self, sent_invoice):
        """Reuse the standard SENT invoice (non-GOVERNMENT partner)."""
        return sent_invoice

    def test_send_xrechnung_success(self, authenticated_admin_client, gov_invoice):
        """Returns 200, sends an XML attachment, and persists tracking fields."""
        url = reverse("api-invoice-send-xrechnung", kwargs={"pk": gov_invoice.pk})
        response = authenticated_admin_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        data = response.json()
        assert data["recipient"] == "behoerde@example.de"
        assert data["sent_at"] is not None
        assert len(mail.outbox) == 1
        filenames = [a[0] for a in mail.outbox[0].attachments]
        assert any(name.endswith(".xml") for name in filenames)
        gov_invoice.refresh_from_db()
        assert gov_invoice.xrechnung_sent_at is not None
        assert gov_invoice.xrechnung_sent_to == "behoerde@example.de"

    def test_send_xrechnung_non_government_returns_400(self, authenticated_admin_client, business_invoice):
        """Non-GOVERNMENT partner must yield 400."""
        url = reverse("api-invoice-send-xrechnung", kwargs={"pk": business_invoice.pk})
        response = authenticated_admin_client.post(
            url, {"recipient": "test@example.com"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert mail.outbox == []

    def test_send_xrechnung_no_email_returns_400(self, authenticated_admin_client, company):
        """GOVERNMENT partner without email and no explicit recipient → 400."""
        partner = GovernmentPartnerFactory(email="")
        invoice = InvoiceFactory(
            company=company,
            business_partner=partner,
            status=Invoice.InvoiceStatus.SENT,
        )
        url = reverse("api-invoice-send-xrechnung", kwargs={"pk": invoice.pk})
        response = authenticated_admin_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert mail.outbox == []
    def test_send_xrechnung_explicit_recipient_overrides_partner_email(
        self, authenticated_admin_client, gov_invoice
    ):
        """Explicit recipient in request body takes precedence over partner email."""
        url = reverse("api-invoice-send-xrechnung", kwargs={"pk": gov_invoice.pk})
        response = authenticated_admin_client.post(
            url, {"recipient": "custom@example.org"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["recipient"] == "custom@example.org"
        gov_invoice.refresh_from_db()
        assert gov_invoice.xrechnung_sent_to == "custom@example.org"

    def test_send_xrechnung_draft_auto_transitions_to_sent(
        self, authenticated_admin_client, company
    ):
        """DRAFT invoice is auto-marked SENT when XRechnung is sent."""
        partner = GovernmentPartnerFactory(email="behoerde@example.de")
        draft = InvoiceFactory(
            company=company,
            business_partner=partner,
            status=Invoice.InvoiceStatus.DRAFT,
            buyer_reference=partner.leitweg_id,
        )
        stub_xml = b"<?xml version='1.0'?><Invoice>stub</Invoice>"
        draft.xml_file.save(f"{draft.invoice_number}.xml", ContentFile(stub_xml), save=False)
        Invoice.objects.filter(pk=draft.pk).update(xml_file=draft.xml_file.name)
        draft.refresh_from_db()
        url = reverse("api-invoice-send-xrechnung", kwargs={"pk": draft.pk})
        response = authenticated_admin_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        draft.refresh_from_db()
        assert draft.status == Invoice.InvoiceStatus.SENT

