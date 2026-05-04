"""
Invoice e-mail delivery service.

Sends an invoice (PDF/A-3 + optional XML) to a recipient. The service is
strictly transport-agnostic — it relies on Django's configured EMAIL_BACKEND.
For development, point EMAIL_HOST at Mailpit; for production, at IONOS SMTP.

A hard kill switch (settings.INVOICE_EMAIL_ENABLED) allows operators to disable
outgoing mail without changing the backend (e.g. during incident response).
"""

from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from invoice_app.models.audit import AuditLog
from invoice_app.models.invoice_models import Invoice
from invoice_app.services.invoice_service import InvoiceService


logger = logging.getLogger(__name__)


class EmailDisabledError(RuntimeError):
    """Raised when invoice e-mail delivery is disabled via settings."""


class EmailDeliveryError(RuntimeError):
    """Raised when the SMTP backend fails to deliver the message."""


@dataclass
class EmailSendResult:
    recipient: str
    subject: str
    attached_filenames: list[str]
    sent_at: timezone.datetime


class InvoiceEmailService:
    """Generate (if needed) and send an invoice as e-mail with PDF + XML."""

    DEFAULT_SUBJECT = "Rechnung {invoice_number} von {company_name}"

    def send_invoice(
        self,
        invoice: Invoice,
        recipient: str,
        *,
        message: str = "",
        attach_pdf: bool = True,
        attach_xml: bool = False,
        request=None,
        user=None,
    ) -> EmailSendResult:
        """Send the given invoice to ``recipient``.

        Generates PDF (and XML if requested) on demand if missing. Records an
        AuditLog entry (action=SEND_EMAIL) and updates ``last_emailed_at``.
        Set ``attach_pdf=False`` for XRechnung (B2G) where only the XML is the
        legal document and no PDF is expected.
        """
        if not getattr(settings, "INVOICE_EMAIL_ENABLED", True):
            raise EmailDisabledError("E-Mail-Versand ist deaktiviert (INVOICE_EMAIL_ENABLED=False).")

        if not recipient:
            raise ValueError("recipient must not be empty")

        # Ensure files exist (auto-generate on demand).
        invoice_service = InvoiceService()
        if attach_pdf and (not invoice.pdf_file or not invoice.pdf_file.storage.exists(invoice.pdf_file.name)):
            invoice_service.generate_invoice_files(invoice, zugferd_profile="COMFORT")
            invoice.refresh_from_db()
        if attach_xml and (not invoice.xml_file or not invoice.xml_file.storage.exists(invoice.xml_file.name)):
            invoice_service.generate_invoice_files(invoice, zugferd_profile="COMFORT")
            invoice.refresh_from_db()

        company_name = invoice.company.name if invoice.company_id else "eRechnung"
        partner = invoice.business_partner
        partner_name = partner.display_name if partner else ""

        subject = self.DEFAULT_SUBJECT.format(
            invoice_number=invoice.invoice_number,
            company_name=company_name,
        )

        context = {
            "invoice": invoice,
            "company_name": company_name,
            "partner_name": partner_name,
            "custom_message": message.strip(),
        }
        text_body = render_to_string("email/invoice_sent.txt", context)
        html_body = render_to_string("email/invoice_sent.html", context)

        from_email = settings.DEFAULT_FROM_EMAIL
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=[recipient],
            reply_to=[from_email],
        )
        email.attach_alternative(html_body, "text/html")

        attached: list[str] = []
        if attach_pdf and invoice.pdf_file:
            attached.append(self._attach_file(email, invoice.pdf_file, default_ext=".pdf"))
        if attach_xml and invoice.xml_file:
            attached.append(self._attach_file(email, invoice.xml_file, default_ext=".xml"))

        try:
            sent = email.send(fail_silently=False)
        except Exception as exc:  # pragma: no cover - re-raised below
            logger.exception("Invoice e-mail delivery failed: invoice=%s", invoice.id)
            raise EmailDeliveryError(str(exc)) from exc

        if sent != 1:
            raise EmailDeliveryError(f"SMTP backend reported {sent} delivered messages (expected 1).")

        sent_at = timezone.now()

        # Update invoice tracking fields (allowed even when GoBD-locked).
        invoice.last_emailed_at = sent_at
        invoice.last_email_recipient = recipient
        invoice.save(update_fields=["last_emailed_at", "last_email_recipient", "updated_at"])

        AuditLog.log_action(
            action=AuditLog.ActionType.SEND_EMAIL,
            user=user,
            request=request,
            object_instance=invoice,
            description=f"Rechnung {invoice.invoice_number} per E-Mail an {recipient} versendet",
            severity=AuditLog.Severity.MEDIUM,
            details={
                "recipient": recipient,
                "subject": subject,
                "attached_files": attached,
                "with_xml": bool(attach_xml and invoice.xml_file),
                "from_email": from_email,
            },
        )

        return EmailSendResult(
            recipient=recipient,
            subject=subject,
            attached_filenames=attached,
            sent_at=sent_at,
        )

    @staticmethod
    def _attach_file(email: EmailMultiAlternatives, fieldfile, *, default_ext: str) -> str:
        """Attach a Django FieldFile to the message and return its filename."""
        filename = fieldfile.name.rsplit("/", 1)[-1]
        if not filename.lower().endswith(default_ext):
            filename = f"{filename}{default_ext}"
        with fieldfile.open("rb") as fp:
            content = fp.read()
        mimetype, _ = mimetypes.guess_type(filename)
        email.attach(filename, content, mimetype or "application/octet-stream")
        return filename

    def send_xrechnung(
        self,
        invoice: Invoice,
        recipient: str,
        *,
        message: str = "",
        request=None,
        user=None,
    ) -> EmailSendResult:
        """Send XRechnung (XML mandatory) to a B2G recipient and track the delivery.

        Delegates actual sending to ``send_invoice`` with ``attach_xml=True``,
        then records the B2G-specific tracking fields ``xrechnung_sent_at`` and
        ``xrechnung_sent_to``.
        """
        result = self.send_invoice(
            invoice,
            recipient,
            message=message,
            attach_pdf=False,
            attach_xml=True,
            request=request,
            user=user,
        )

        # Persist B2G-specific tracking (separate from general last_emailed_at).
        invoice.xrechnung_sent_at = result.sent_at
        invoice.xrechnung_sent_to = recipient
        invoice.save(update_fields=["xrechnung_sent_at", "xrechnung_sent_to", "updated_at"])

        return result


def send_invoice_email(
    invoice: Invoice,
    recipient: str,
    *,
    message: str = "",
    attach_xml: bool = True,
    request=None,
    user=None,
) -> EmailSendResult:
    """Module-level convenience wrapper."""
    return InvoiceEmailService().send_invoice(
        invoice,
        recipient,
        message=message,
        attach_xml=attach_xml,
        request=request,
        user=user,
    )
