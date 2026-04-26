"""Inline admin classes for related models."""

from django.contrib import admin

from invoice_app.models import InvoiceAttachment, InvoiceLine


class InvoiceLineInline(admin.TabularInline):
    """Inline admin for invoice line items."""

    model = InvoiceLine
    extra = 1
    fields = (
        "product",
        "description",
        "quantity",
        "unit_price",
        "unit_of_measure",
        "tax_rate",
        "discount_percentage",
        "line_total",
    )
    readonly_fields = ("line_total",)
    autocomplete_fields = ("product",)


class InvoiceAttachmentInline(admin.TabularInline):
    """Inline admin for invoice attachments."""

    model = InvoiceAttachment
    extra = 1
