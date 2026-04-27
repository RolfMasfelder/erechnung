"""
Invoice models for the invoice_app application.

Contains Invoice, InvoiceLine, and InvoiceAttachment models for
electronic invoices compliant with ZUGFeRD/EN16931 standards.
"""

import hashlib
import json
import logging
import os
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _

from invoice_app.models.business_partner import BusinessPartner
from invoice_app.models.company import Company
from invoice_app.models.product import Product


logger = logging.getLogger(__name__)


class Invoice(models.Model):
    """
    Invoice model for electronic invoices compliant with ZUGFeRD/EN16931 standards.
    """

    class InvoiceStatus(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        SENT = "SENT", _("Sent")
        PAID = "PAID", _("Paid")
        CANCELLED = "CANCELLED", _("Cancelled")
        OVERDUE = "OVERDUE", _("Overdue")

    class InvoiceType(models.TextChoices):
        INVOICE = "INVOICE", _("Invoice")
        CREDIT_NOTE = "CREDIT_NOTE", _("Credit Note")
        DEBIT_NOTE = "DEBIT_NOTE", _("Debit Note")
        CORRECTED = "CORRECTED", _("Corrected Invoice")
        PARTIAL = "PARTIAL", _("Partial Invoice")
        FINAL = "FINAL", _("Final Invoice")

    # ── Invoice identification ──────────────────────────────────────────────
    # DESIGN: sequence_number (Integer) und invoice_number (String) werden
    # bewusst parallel geführt:
    #   - sequence_number: Fortlaufender, jahresübergreifender Zähler für
    #     ausgehende Rechnungen (§ 14 Abs. 4 Nr. 4 UStG). Quelle der Wahrheit
    #     für die Nummerierung. NULL bei Eingangsrechnungen (externe Nummern).
    #     Vergabe über PostgreSQL SEQUENCE (nextval) — atomar, keine Race
    #     Conditions. Startwert bei Inbetriebnahme über Management-Command
    #     set_sequence_start einstellbar.
    #   - invoice_number: Lesbarer Display-String für alle Rechnungen.
    #     Bei ausgehenden: automatisch generiert aus sequence_number + issue_date
    #     (Format: INV-{JJJJ}-{NNNN}). Bei eingehenden: beliebiger String des
    #     Lieferanten.
    # Die API liefert ausschließlich invoice_number als String — das Frontend
    # kennt sequence_number nicht.
    sequence_number = models.PositiveIntegerField(
        _("Sequence Number"),
        unique=True,
        null=True,
        blank=True,
        help_text=_("Fortlaufende Nummer für ausgehende Rechnungen (§ 14 UStG). NULL bei Eingangsrechnungen."),
    )
    invoice_number = models.CharField(
        _("Invoice Number"),
        max_length=50,
        unique=True,
        default="DEFAULT",  # Default value for migrations only, will be overridden by save method
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z0-9-]+$", message=_("Invoice number can only contain letters, numbers, and hyphens.")
            )
        ],
    )
    invoice_type = models.CharField(
        _("Invoice Type"), max_length=20, choices=InvoiceType.choices, default=InvoiceType.INVOICE
    )

    # Organization references
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="issued_invoices",
        verbose_name=_("Company"),
        null=True,
        blank=True,
    )
    business_partner = models.ForeignKey(
        BusinessPartner,
        on_delete=models.PROTECT,
        related_name="received_invoices",
        verbose_name=_("Business Partner"),
        null=True,
        blank=True,
    )

    # Invoice dates
    issue_date = models.DateField(_("Issue Date"), default=timezone.now)
    due_date = models.DateField(_("Due Date"), default=timezone.now)
    delivery_date = models.DateField(_("Delivery Date"), null=True, blank=True)

    # Financial information
    currency = models.CharField(_("Currency"), max_length=3, default="EUR")
    subtotal = models.DecimalField(
        _("Subtotal"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )
    tax_amount = models.DecimalField(
        _("Tax Amount"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )
    total_amount = models.DecimalField(
        _("Total Amount"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )

    # Payment information
    payment_terms = models.PositiveIntegerField(
        _("Payment Terms (days)"),
        default=30,
        blank=True,
        null=True,
        help_text=_("Number of days until payment is due (e.g. 30 for 'net 30')"),
    )
    payment_method = models.CharField(_("Payment Method"), max_length=100, blank=True)
    payment_reference = models.CharField(_("Payment Reference"), max_length=100, blank=True)

    # Business references (B2B)
    buyer_reference = models.CharField(
        _("Buyer Reference"),
        max_length=100,
        blank=True,
        help_text=_("Customer's order or reference number (Ihr Zeichen)"),
    )
    seller_reference = models.CharField(
        _("Seller Reference"),
        max_length=100,
        blank=True,
        help_text=_("Our internal reference or project number (Unser Zeichen)"),
    )

    # Status and file references
    status = models.CharField(_("Status"), max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    pdf_file = models.FileField(_("PDF File"), upload_to="invoices/pdf/", null=True, blank=True)
    xml_file = models.FileField(_("XML File"), upload_to="invoices/xml/", null=True, blank=True)

    # Tracking and audit information
    notes = models.TextField(_("Notes"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_invoices",
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    # ── Concurrent Edit Lock (Pessimistic Application-Level Locking) ────────
    editing_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editing_invoices",
        verbose_name=_("In Bearbeitung von"),
    )
    editing_since = models.DateTimeField(_("In Bearbeitung seit"), null=True, blank=True)

    # ── GoBD Compliance: Unveränderbarkeit ──────────────────────────────────
    is_locked = models.BooleanField(
        _("Gesperrt"),
        default=False,
        db_index=True,
        help_text=_("Gesperrte Dokumente können nicht mehr geändert werden (GoBD)"),
    )
    locked_at = models.DateTimeField(_("Gesperrt am"), null=True, blank=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locked_invoices",
        verbose_name=_("Gesperrt von"),
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
        blank=True,
    )

    # ── GoBD Compliance: Kryptographische Integrität ────────────────────────
    content_hash = models.CharField(
        _("Content Hash"),
        max_length=64,
        blank=True,
        help_text=_("SHA-256 Hash des Dokumentinhalts"),
    )
    hash_algorithm = models.CharField(
        _("Hash-Algorithmus"),
        max_length=20,
        default="SHA256",
    )

    # ── GoBD Compliance: Aufbewahrung & Löschsperre ────────────────────────
    retention_until = models.DateField(
        _("Aufbewahren bis"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Mindestens 10 Jahre nach Erstellung (GoBD)"),
    )
    deletion_blocked = models.BooleanField(
        _("Löschung gesperrt"),
        default=True,
    )
    is_archived = models.BooleanField(
        _("Archiviert"),
        default=False,
        db_index=True,
    )
    archived_at = models.DateTimeField(
        _("Archiviert am"),
        null=True,
        blank=True,
    )

    # ── Stornierung ──────────────────────────────────────────────────────────
    cancelled_by = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancels_invoice",
        verbose_name=_("Storniert durch"),
    )

    # Default managers: exclude archived by default
    objects = models.Manager()  # includes archived

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ["-issue_date", "-invoice_number"]
        indexes = [
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["sequence_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["issue_date"]),
            models.Index(fields=["company"]),
            models.Index(fields=["is_locked"]),
            models.Index(fields=["retention_until"]),
            models.Index(fields=["editing_since"]),
        ]

    def __str__(self):
        partner_name = self.business_partner.display_name if self.business_partner else "N/A"
        return f"{self.invoice_number} - {partner_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """Override save to ensure total_amount is calculated correctly and generate invoice number if needed.

        GoBD: Auto-locks invoice on status transition to SENT/PAID/CANCELLED.
        Locked invoices cannot be modified except for status changes to CANCELLED.
        """
        # ── GoBD: Block modifications to locked invoices ────────────────────
        skip_lock_check = kwargs.pop("_skip_lock_check", False)
        if self.pk and self.is_locked and not skip_lock_check:
            # Allow only: status change to CANCELLED (Stornierung)
            try:
                old = Invoice.objects.get(pk=self.pk)
            except Invoice.DoesNotExist:
                old = None

            if old and old.is_locked:
                # Check which fields actually changed
                # Erlaubte Felder nach Lock:
                #   status/cancelled_by_id  → Stornierung
                #   is_archived/archived_at → GoBD Soft-Delete
                allowed_lock_fields = {
                    "status",
                    "updated_at",
                    "cancelled_by_id",
                    "is_archived",
                    "archived_at",
                }
                changed_fields = set()
                for field in self._meta.fields:
                    if field.name in ("updated_at",):
                        continue
                    # Use value_from_object for reliable comparison
                    # (avoids FieldFile descriptor identity issues)
                    old_val = field.value_from_object(old)
                    new_val = field.value_from_object(self)
                    if old_val != new_val:
                        changed_fields.add(field.attname)

                disallowed = changed_fields - allowed_lock_fields
                if disallowed:
                    from invoice_app.api.exceptions import GoBDViolationError

                    raise GoBDViolationError(
                        detail=(
                            f"Gesperrte Rechnung {self.invoice_number} kann nicht geändert werden. "
                            f"Geänderte Felder: {', '.join(sorted(disallowed))}. "
                            "Erstellen Sie eine Stornorechnung."
                        )
                    )

        # Calculate total amount
        if self.subtotal is not None and self.tax_amount is not None:
            self.total_amount = self.subtotal + self.tax_amount

        # Generate invoice number if not provided or still has default placeholder
        if not self.invoice_number or self.invoice_number == "DEFAULT":
            self._assign_sequence_number()
            self.invoice_number = self._format_invoice_number()

        # ── GoBD: Set retention period (10 years from issue_date) ──────────
        if not self.retention_until and self.issue_date:
            from datetime import date

            issue = self.issue_date
            if isinstance(issue, str):
                issue = date.fromisoformat(issue)
            self.retention_until = issue + timedelta(days=3653)  # ~10 years

        # ── GoBD: Auto-lock on status transition to SENT/PAID ──────────────
        if self.status in (self.InvoiceStatus.SENT, self.InvoiceStatus.PAID, self.InvoiceStatus.CANCELLED):
            if not self.is_locked:
                self.is_locked = True
                self.locked_at = timezone.now()
                self.lock_reason = self.status

        super().save(*args, **kwargs)

        # ── GoBD: Calculate content hash after save (needs pk for lines) ───
        if self.is_locked and not self.content_hash:
            content_hash = self.calculate_content_hash()
            if content_hash:
                Invoice.objects.filter(pk=self.pk).update(content_hash=content_hash)
                self.content_hash = content_hash

    # ── Concurrent Edit Lock helpers ─────────────────────────────────────────

    def is_edit_locked_by_other(self, user):
        """Return True if locked by a different user and the lock has not expired."""
        from django.conf import settings as django_settings

        timeout = getattr(django_settings, "INVOICE_EDIT_LOCK_TIMEOUT_MINUTES", 30)
        cutoff = timezone.now() - timedelta(minutes=timeout)
        return (
            self.editing_by_id is not None
            and self.editing_by_id != user.pk
            and self.editing_since is not None
            and self.editing_since > cutoff
        )

    def acquire_edit_lock(self, user):
        """Atomically acquire the edit lock. Returns (success: bool, holder: User|None).

        Uses select_for_update() within a single DB transaction to prevent race
        conditions when two users attempt to lock the same invoice simultaneously.
        """
        from django.conf import settings as django_settings
        from django.db import transaction

        timeout = getattr(django_settings, "INVOICE_EDIT_LOCK_TIMEOUT_MINUTES", 30)
        now = timezone.now()
        cutoff = now - timedelta(minutes=timeout)

        with transaction.atomic():
            fresh = Invoice.objects.select_for_update().get(pk=self.pk)
            if (
                fresh.editing_by_id is not None
                and fresh.editing_by_id != user.pk
                and fresh.editing_since is not None
                and fresh.editing_since > cutoff
            ):
                return False, fresh.editing_by

            Invoice.objects.filter(pk=self.pk).update(editing_by=user, editing_since=now)
            self.editing_by = user
            self.editing_since = now
            return True, user

    def release_edit_lock(self, user):
        """Release the edit lock. Only the current lock holder can release it."""
        if self.editing_by_id == user.pk:
            Invoice.objects.filter(pk=self.pk).update(editing_by=None, editing_since=None)
            self.editing_by = None
            self.editing_by_id = None
            self.editing_since = None

    def recalculate_totals(self):
        """Aggregate subtotal, tax_amount and total_amount from all related lines
        and header-level allowances/charges.

        After recalculation:
        - subtotal    = Nettobetrag der Zeilen minus header Allowances plus header Charges
                        (= Steuerbasis / TaxBasisTotalAmount)
        - tax_amount  = Σ(gruppenweise Steuer nach Allowance-Verteilung)
        - total_amount = subtotal + tax_amount
        """
        from decimal import Decimal

        from django.db.models import Q, Sum

        agg = self.lines.aggregate(
            subtotal=Sum("line_total"),
            tax_amount=Sum("tax_amount"),
        )
        lines_subtotal = agg["subtotal"] or Decimal("0")
        lines_tax = agg["tax_amount"] or Decimal("0")

        # Include header-level allowances/charges in subtotal (= tax basis)
        if self.pk:
            ac_agg = self.allowance_charges.filter(invoice_line__isnull=True).aggregate(
                charges=Sum("actual_amount", filter=Q(is_charge=True)),
                allowances=Sum("actual_amount", filter=Q(is_charge=False)),
            )
            charges = ac_agg["charges"] or Decimal("0")
            allowances = ac_agg["allowances"] or Decimal("0")
        else:
            charges = allowances = Decimal("0")

        self.subtotal = lines_subtotal - allowances + charges  # = tax basis

        # Adjust tax: distribute header allowances/charges proportionally across
        # VAT-rate groups (same algorithm as the XML generator, EN16931 BR-S-08/BR-CO-5).
        # For each rate group:  adjusted_basis = line_total_group + net_adjustment * share
        #                       group_tax      = adjusted_basis * rate / 100
        # This keeps tax_amount consistent with ApplicableTradeTax/CalculatedAmount in the XML.
        net_adjustment = charges - allowances  # positive = surcharge, negative = discount
        if self.pk and net_adjustment != Decimal("0"):
            groups = self.lines.values("tax_rate").annotate(group_total=Sum("line_total"))
            total_line = lines_subtotal or Decimal("0")
            tax_adjustment = Decimal("0")
            for g in groups:
                rate = g["tax_rate"]
                group_total = g["group_total"] or Decimal("0")
                share = group_total / total_line if total_line else Decimal("0")
                adjusted_basis = group_total + net_adjustment * share
                # Round each rate contribution to 2 dp for consistent cent-level arithmetic.
                old_tax = (group_total * (rate / Decimal("100"))).quantize(Decimal("0.01"))
                new_tax = (adjusted_basis * (rate / Decimal("100"))).quantize(Decimal("0.01"))
                tax_adjustment += new_tax - old_tax
            self.tax_amount = (lines_tax + tax_adjustment).quantize(Decimal("0.01"))
        else:
            self.tax_amount = lines_tax

        self.total_amount = (self.subtotal + self.tax_amount).quantize(Decimal("0.01"))
        self.__class__.objects.filter(pk=self.pk).update(
            subtotal=self.subtotal,
            tax_amount=self.tax_amount,
            total_amount=self.total_amount,
        )

    SEQUENCE_NAME = "invoice_sequence_number_seq"

    def _assign_sequence_number(self):
        """Assign the next global sequence number for outgoing invoices.

        Uses PostgreSQL SEQUENCE (nextval) — atomic, no race conditions.
        The counter never resets across years (§ 14 Abs. 4 Nr. 4 UStG).
        Starting value can be set via: manage.py set_sequence_start <N>
        """
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(f"SELECT nextval('{self.SEQUENCE_NAME}')")
            self.sequence_number = cursor.fetchone()[0]

    def _format_invoice_number(self):
        """Format the display string from sequence_number + issue_date.

        Format: INV-YYYY-NNNN (invoices) or GS-YYYY-NNNN (credit notes).
        Zero-padded to 4 digits, extends beyond 9999.
        """
        year = self.issue_date.year if self.issue_date else timezone.now().year
        prefix = "GS" if self.invoice_type == self.InvoiceType.CREDIT_NOTE else "INV"
        return f"{prefix}-{year}-{self.sequence_number:04d}"

    def generate_invoice_number(self):
        """Generate a unique invoice number (legacy compatibility wrapper)."""
        self._assign_sequence_number()
        return self._format_invoice_number()

    def is_paid(self):
        """Check if the invoice is paid."""
        return self.status == self.InvoiceStatus.PAID

    def is_overdue(self):
        """Check if the invoice is overdue."""
        return (
            self.status not in (self.InvoiceStatus.PAID, self.InvoiceStatus.CANCELLED)
            and self.due_date < timezone.now().date()
        )

    # ── GoBD: Soft-Delete ────────────────────────────────────────────────────

    def delete(self, *args, **kwargs):
        """GoBD-konformes Löschen: Soft-Delete statt physischer Löschung.

        Rechnungen innerhalb der Aufbewahrungsfrist werden archiviert,
        nicht gelöscht. Draft-Rechnungen können gelöscht werden.
        """
        # DRAFT invoices that are NOT locked can be hard-deleted
        if self.status == self.InvoiceStatus.DRAFT and not self.is_locked:
            return super().delete(*args, **kwargs)

        # Check retention period
        if self.retention_until and self.retention_until > timezone.now().date():
            from invoice_app.api.exceptions import GoBDViolationError

            raise GoBDViolationError(
                detail=(f"Löschung vor Ablauf der Aufbewahrungsfrist ({self.retention_until}) nicht erlaubt (GoBD).")
            )

        # Soft-Delete: archive instead of deleting
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(_skip_lock_check=True)
        logger.info(f"Invoice {self.invoice_number} archived (soft-delete, GoBD)")
        return (0, {})  # mimic delete return signature

    # ── GoBD: Stornierung ────────────────────────────────────────────────────

    def cancel(self, user=None, reason=""):
        """Erstellt eine Stornorechnung statt Löschung (GoBD-konform).

        Returns the new credit note invoice.
        """
        if self.status == self.InvoiceStatus.CANCELLED:
            from invoice_app.api.exceptions import InvoiceStatusError

            raise InvoiceStatusError(detail="Rechnung ist bereits storniert.")

        if self.status not in (self.InvoiceStatus.SENT, self.InvoiceStatus.PAID):
            from invoice_app.api.exceptions import InvoiceStatusError

            raise InvoiceStatusError(detail="Nur versendete oder bezahlte Rechnungen können storniert werden.")

        # Create credit note
        credit_note = Invoice(
            invoice_type=self.InvoiceType.CREDIT_NOTE,
            company=self.company,
            business_partner=self.business_partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date(),
            delivery_date=self.delivery_date,
            currency=self.currency,
            subtotal=-self.subtotal,
            tax_amount=-self.tax_amount,
            total_amount=-self.total_amount,
            payment_terms=self.payment_terms,
            payment_method=self.payment_method,
            buyer_reference=self.buyer_reference,
            seller_reference=self.seller_reference,
            notes=f"Storno zu {self.invoice_number}: {reason}".strip(),
            created_by=user,
            status=self.InvoiceStatus.SENT,
        )
        credit_note.save()

        # Copy line items with negated quantities (save() recalculates totals)
        for line in self.lines.all():
            InvoiceLine = line.__class__
            InvoiceLine.objects.create(
                invoice=credit_note,
                product=line.product,
                description=line.description,
                product_code=line.product_code,
                quantity=-line.quantity,
                unit_price=line.unit_price,
                unit_of_measure=line.unit_of_measure,
                tax_rate=line.tax_rate,
                tax_category=line.tax_category,
                tax_exemption_reason=line.tax_exemption_reason,
                discount_percentage=line.discount_percentage,
                discount_reason=line.discount_reason,
            )

        # Mark original as cancelled
        self.status = self.InvoiceStatus.CANCELLED
        self.cancelled_by = credit_note
        self.save(_skip_lock_check=True)

        logger.info(f"Invoice {self.invoice_number} cancelled, credit note {credit_note.invoice_number} created")
        return credit_note

    # ── GoBD: Content Hash ───────────────────────────────────────────────────

    def calculate_content_hash(self):
        """Berechnet SHA-256 Hash des Rechnungsinhalts.

        Deterministische Serialisierung aller buchhalterisch relevanten Felder.
        """
        data = {
            "invoice_number": self.invoice_number,
            "invoice_type": self.invoice_type,
            "company_id": self.company_id,
            "business_partner_id": self.business_partner_id,
            "issue_date": str(self.issue_date) if self.issue_date else "",
            "due_date": str(self.due_date) if self.due_date else "",
            "currency": self.currency,
            "subtotal": str(self.subtotal),
            "tax_amount": str(self.tax_amount),
            "total_amount": str(self.total_amount),
            "lines": [
                {
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price),
                    "tax_rate": str(line.tax_rate),
                    "line_total": str(line.line_total),
                }
                for line in self.lines.all().order_by("id")
            ],
        }

        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def verify_integrity(self):
        """Prüft ob der gespeicherte Hash noch mit dem Inhalt übereinstimmt.

        Returns:
            tuple: (is_valid: bool, error_message: str | None)
        """
        if not self.content_hash:
            return True, None  # Kein Hash vorhanden (z.B. Draft)

        current_hash = self.calculate_content_hash()
        if current_hash != self.content_hash:
            return False, (
                f"Integritätsverletzung bei {self.invoice_number}: "
                f"erwartet {self.content_hash}, berechnet {current_hash}"
            )
        return True, None


class InvoiceLine(models.Model):
    """
    Model for individual line items within an invoice.
    Now supports both product-based and custom line items.
    """

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines", verbose_name=_("Invoice"))

    # Product reference (optional for custom line items)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoice_lines",
        verbose_name=_("Product"),
    )

    # Line item details (can override product defaults)
    description = models.CharField(_("Description"), max_length=255, default="Item")
    product_code = models.CharField(_("Product Code"), max_length=100, blank=True)

    # Pricing and quantities
    quantity = models.DecimalField(
        _("Quantity"), max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal("0"))], default=1
    )
    unit_price = models.DecimalField(
        _("Unit Price"), max_digits=15, decimal_places=6, validators=[MinValueValidator(Decimal("0"))], default=0
    )
    unit_of_measure = models.IntegerField(
        _("Unit of Measure"),
        choices=Product.UnitOfMeasure.choices,
        default=Product.UnitOfMeasure.PCE,
    )

    # Tax information
    tax_rate = models.DecimalField(
        _("Tax Rate"), max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )
    tax_amount = models.DecimalField(
        _("Tax Amount"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )
    tax_category = models.CharField(
        _("Tax Category Code"),
        max_length=5,
        blank=True,
        default="S",
        help_text=_("EN16931 tax category: S=Standard, Z=Zero, E=Exempt, AE=Reverse Charge, G=Export"),
    )
    tax_exemption_reason = models.CharField(
        _("Tax Exemption Reason"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Required for AE/G categories (e.g., 'Reverse Charge' or 'Export')"),
    )

    # Calculated totals
    line_subtotal = models.DecimalField(
        _("Line Subtotal"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )
    line_total = models.DecimalField(
        _("Line Total"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )

    # Optional discounts (line-level per EN16931 SpecifiedTradeAllowanceCharge)
    discount_percentage = models.DecimalField(
        _("Discount %"), max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )
    discount_amount = models.DecimalField(
        _("Discount Amount"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )
    # EN16931 BR-41: reason or reason code required when AllowanceCharge is present
    discount_reason = models.CharField(_("Discount Reason"), max_length=255, blank=True, default="")

    class Meta:
        verbose_name = _("Invoice Line")
        verbose_name_plural = _("Invoice Lines")
        indexes = [
            models.Index(fields=["invoice", "product"]),
            models.Index(fields=["product_code"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(unit_of_measure__in=Product.UnitOfMeasure.values),
                name="invoiceline_unit_of_measure_valid",
            ),
        ]

    def __str__(self):
        return f"{self.description} - {self.line_total} {self.invoice.currency}"

    def save(self, *args, **kwargs):
        """Override save to populate fields from product and calculate totals."""
        # Populate from product if available
        if self.product and not self._state.adding:
            # Only auto-populate on creation, not updates
            pass
        elif self.product:
            if not self.description or self.description == "Item":
                self.description = self.product.name
            if not self.product_code:
                self.product_code = self.product.product_code
            if self.unit_price == 0:
                self.unit_price = self.product.current_price
            if self.unit_of_measure is None or self.unit_of_measure == Product.UnitOfMeasure.PCE:
                self.unit_of_measure = self.product.unit_of_measure
            if self.tax_rate == 0:
                # Get full tax determination from product + partner scenario
                partner = self.invoice.business_partner if self.invoice else None
                determination = self.product.get_tax_determination_for_partner(partner)
                self.tax_rate = determination.tax_rate
                self.tax_category = determination.tax_category_code
                self.tax_exemption_reason = determination.exemption_reason

        # Calculate totals
        self.line_subtotal = self.quantity * self.unit_price

        # Apply discount (round to 2 dp before subtraction to avoid
        # propagation of intermediate precision into line_total).
        if self.discount_percentage > 0:
            self.discount_amount = ((self.line_subtotal * self.discount_percentage) / 100).quantize(Decimal("0.01"))

        # Calculate net line total (after discount, before tax)
        self.line_total = (self.line_subtotal - self.discount_amount).quantize(Decimal("0.01"))

        # Apply line-level allowances/charges (only on subsequent saves)
        if not self._state.adding and self.pk:
            from django.db.models import Q as _Q
            from django.db.models import Sum as _Sum

            ac_agg = self.allowance_charges.aggregate(
                charges=_Sum("actual_amount", filter=_Q(is_charge=True)),
                allowances=_Sum("actual_amount", filter=_Q(is_charge=False)),
            )
            ac_charges = ac_agg["charges"] or Decimal("0")
            ac_allowances = ac_agg["allowances"] or Decimal("0")
            self.line_total = self.line_total - ac_allowances + ac_charges

        # Calculate tax amount
        self.tax_amount = ((self.line_total * self.tax_rate) / 100).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)

        # Update parent invoice totals
        if self.invoice_id:
            self.invoice.recalculate_totals()

    def recalculate(self):
        """Recalculate line totals (called when line-level A/Cs are added/deleted)."""
        from decimal import Decimal

        from django.db.models import Q as _Q
        from django.db.models import Sum as _Sum

        self.line_subtotal = self.quantity * self.unit_price
        if self.discount_percentage > 0:
            self.discount_amount = ((self.line_subtotal * self.discount_percentage) / 100).quantize(Decimal("0.01"))
        self.line_total = (self.line_subtotal - self.discount_amount).quantize(Decimal("0.01"))

        # Line-level allowances/charges
        ac_agg = self.allowance_charges.aggregate(
            charges=_Sum("actual_amount", filter=_Q(is_charge=True)),
            allowances=_Sum("actual_amount", filter=_Q(is_charge=False)),
        )
        ac_charges = ac_agg["charges"] or Decimal("0")
        ac_allowances = ac_agg["allowances"] or Decimal("0")
        self.line_total = self.line_total - ac_allowances + ac_charges

        self.tax_amount = ((self.line_total * self.tax_rate) / Decimal("100")).quantize(Decimal("0.01"))

        InvoiceLine.objects.filter(pk=self.pk).update(
            line_subtotal=self.line_subtotal,
            discount_amount=self.discount_amount,
            line_total=self.line_total,
            tax_amount=self.tax_amount,
        )

    @property
    def effective_unit_price(self):
        """Return the effective unit price after discounts."""
        if self.discount_percentage > 0:
            return self.unit_price * (1 - self.discount_percentage / 100)
        return self.unit_price - (self.discount_amount / self.quantity if self.quantity > 0 else 0)

    # ZUGFeRD-specific properties for XML generation
    @property
    def unit_code(self):
        """
        UN/ECE Recommendation 20 unit code für ZUGFeRD XML.
        Übersetzt die interne numerische ID in den offiziellen UN/CEFACT-Code.
        Default: C62 (Stück/Einheit)
        """
        return Product.UNIT_UNCEFACT_CODES.get(self.unit_of_measure, "C62")

    @property
    def tax_category_code(self):
        """
        Tax category code for ZUGFeRD XML.

        Returns the stored tax_category field if set, otherwise
        derives the code from the tax_rate:
        - S: Standard rate (>0%)
        - Z: Zero rated (0%)
        - E: Exempt from tax
        - AE: Reverse Charge (EU, partner has valid VAT ID)
        - G: Export outside EU (Drittland)
        """
        # Use the stored field if explicitly set
        if self.tax_category and self.tax_category != "S":
            return self.tax_category

        # Fallback: derive from tax_rate (backward compatibility)
        if self.tax_rate == 0:
            return self.tax_category if self.tax_category in ("Z", "AE", "G", "E") else "Z"
        return "S"

    @property
    def net_price_indicator(self):
        """Indicator whether price is net (before tax). Always True for our system."""
        return True

    def update_from_product(self):
        """Update line item fields from the referenced product."""
        if self.product:
            self.description = self.product.name
            self.product_code = self.product.product_code
            self.unit_price = self.product.current_price
            self.unit_of_measure = self.product.unit_of_measure
            partner = self.invoice.business_partner if self.invoice else None
            determination = self.product.get_tax_determination_for_partner(partner)
            self.tax_rate = determination.tax_rate
            self.tax_category = determination.tax_category_code
            self.tax_exemption_reason = determination.exemption_reason


def attachment_upload_path(instance, filename):
    """Generate upload path: invoices/attachments/invoice_{number}/{safe_filename}.

    Preserves original filename (sanitized) and groups files by invoice.
    """
    safe_name = get_valid_filename(filename)
    invoice_number = instance.invoice.invoice_number if instance.invoice_id else "unknown"
    return os.path.join("invoices", "attachments", f"invoice_{invoice_number}", safe_name)


class AttachmentType(models.TextChoices):
    SUPPORTING_DOCUMENT = "supporting_document", _("Supporting Document")
    DELIVERY_NOTE = "delivery_note", _("Delivery Note")
    TIMESHEET = "timesheet", _("Timesheet")
    OTHER = "other", _("Other")


# Maximum upload size: 10 MB
ATTACHMENT_MAX_SIZE = 10 * 1024 * 1024

ATTACHMENT_ALLOWED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "csv", "xlsx"]


class InvoiceAttachment(models.Model):
    """
    Rechnungsbegründende Dokumente (supporting documents) for invoices.

    Files are stored separately on disk under invoices/attachments/invoice_{number}/
    to preserve traceability of which files were embedded into the PDF/A-3.
    After PDF/A-3 generation, files remain on disk for auditing/GoBD compliance.
    """

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="attachments", verbose_name=_("Invoice")
    )
    file = models.FileField(
        _("File"),
        upload_to=attachment_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=ATTACHMENT_ALLOWED_EXTENSIONS)],
    )
    original_filename = models.CharField(
        _("Original Filename"),
        max_length=255,
        blank=True,
        help_text=_("Original filename as uploaded by the user"),
    )
    description = models.CharField(_("Description"), max_length=255)
    attachment_type = models.CharField(
        _("Attachment Type"),
        max_length=30,
        choices=AttachmentType.choices,
        default=AttachmentType.SUPPORTING_DOCUMENT,
    )
    mime_type = models.CharField(
        _("MIME Type"),
        max_length=100,
        blank=True,
        help_text=_("Detected MIME type of the uploaded file"),
    )
    uploaded_at = models.DateTimeField(_("Uploaded At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Invoice Attachment")
        verbose_name_plural = _("Invoice Attachments")
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"{self.original_filename or self.description} - {self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        if self.file and not self.original_filename:
            self.original_filename = self.file.name.split("/")[-1]
        if self.file and not self.mime_type:
            self.mime_type = self._detect_mime_type()
        super().save(*args, **kwargs)

    def _detect_mime_type(self):
        """Detect MIME type from file extension."""
        ext_map = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        name = self.file.name.lower() if self.file else ""
        _, ext = os.path.splitext(name)
        return ext_map.get(ext, "application/octet-stream")


class InvoiceAllowanceCharge(models.Model):
    """
    Allowance (Rabatt) or charge (Zuschlag) — either at header or line level.

    EN16931 mapping:
    - ``invoice_line`` is NULL  → header-level (ApplicableHeaderTradeSettlement/SpecifiedTradeAllowanceCharge)
      * is_charge=False → reduces TaxBasisTotalAmount
      * is_charge=True  → increases TaxBasisTotalAmount
    - ``invoice_line`` is set  → line-level (SpecifiedLineTradeSettlement/SpecifiedTradeAllowanceCharge)
      * affects the line's ``line_total`` via InvoiceLine.recalculate()

    EN16931 rules:
    - BR-41: reason OR reason_code required (we default to generic text if both empty)
    - Header-level CategoryTradeTax is generated by the XML generator from the
      proportional split; no per-record tax_rate needed.
    """

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="allowance_charges", verbose_name=_("Invoice")
    )
    invoice_line = models.ForeignKey(
        "invoice_app.InvoiceLine",
        on_delete=models.CASCADE,
        related_name="allowance_charges",
        verbose_name=_("Invoice Line"),
        null=True,
        blank=True,
        help_text=_(
            "Set for line-level allowance/charge (EN16931 SpecifiedLineTradeSettlement). "
            "Leave null for header-level (ApplicableHeaderTradeSettlement)."
        ),
    )
    is_charge = models.BooleanField(
        _("Is Charge"),
        default=False,
        help_text=_("True = Zuschlag (charge), False = Rabatt (allowance)"),
    )
    actual_amount = models.DecimalField(
        _("Amount"),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    calculation_percent = models.DecimalField(
        _("Calculation %"),
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text=_("Optional: percentage on basis_amount that gives actual_amount"),
    )
    basis_amount = models.DecimalField(
        _("Basis Amount"),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text=_("Optional: base for calculation_percent"),
    )
    # EN16931 UNTDID 5189 (allowance) / UNTDID 7161 (charge) code
    reason_code = models.CharField(
        _("Reason Code"),
        max_length=10,
        blank=True,
        default="",
        help_text=_("UNTDID 5189 (Rabatt) or 7161 (Zuschlag) code, e.g. '95' for discount"),
    )
    reason = models.CharField(
        _("Reason"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Free-text reason (used if reason_code is empty)"),
    )

    sort_order = models.PositiveSmallIntegerField(_("Sort Order"), default=0)

    class Meta:
        verbose_name = _("Invoice Allowance/Charge")
        verbose_name_plural = _("Invoice Allowances/Charges")
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        """Save and trigger recalculation + PDF cache invalidation."""
        super().save(*args, **kwargs)
        if self.invoice_line_id:
            # Line-level: recalculate line first, then invoice
            self.invoice_line.recalculate()
        self.invoice.recalculate_totals()
        # Invalidate cached PDF – amounts have changed, regeneration required
        if self.invoice.pdf_file:
            self.invoice.pdf_file.delete(save=False)
            self.__class__.objects.filter(pk=self.pk)  # noop; avoid re-save loop
            type(self.invoice).objects.filter(pk=self.invoice.pk).update(pdf_file="")

    def delete(self, *args, **kwargs):
        """Delete and trigger recalculation + PDF cache invalidation."""
        invoice = self.invoice
        invoice_line = self.invoice_line
        result = super().delete(*args, **kwargs)
        if invoice_line:
            invoice_line.recalculate()
        invoice.recalculate_totals()
        if invoice.pdf_file:
            invoice.pdf_file.delete(save=False)
            type(invoice).objects.filter(pk=invoice.pk).update(pdf_file="")
        return result

    def __str__(self):
        kind = _("Zuschlag") if self.is_charge else _("Rabatt")
        label = self.reason or self.reason_code or str(self.actual_amount)
        return f"{kind}: {label} ({self.actual_amount} EUR)"
