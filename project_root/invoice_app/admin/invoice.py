"""Admin configuration for Invoice-related models."""

from django.contrib import admin, messages
from django.utils.html import format_html

from invoice_app.admin.inlines import InvoiceAttachmentInline, InvoiceLineInline
from invoice_app.admin.mixins import RBACPermissionMixin
from invoice_app.models import Invoice, InvoiceAttachment, InvoiceLine
from invoice_app.services.invoice_service import InvoiceService


@admin.register(Invoice)
class InvoiceAdmin(RBACPermissionMixin, admin.ModelAdmin):
    """Admin interface for Invoice model with PDF/A-3 generation."""

    list_display = (
        "invoice_number",
        "customer_name",
        "company_name",
        "issue_date",
        "due_date",
        "total_amount",
        "status",
        "pdf_actions",
    )
    list_filter = ("status", "issue_date", "due_date", "invoice_type")
    search_fields = ("invoice_number", "customer__name", "company__name")
    date_hierarchy = "issue_date"
    inlines = [InvoiceLineInline, InvoiceAttachmentInline]
    readonly_fields = ("created_at", "updated_at", "total_amount", "pdf_preview")
    actions = ["generate_pdfa3"]

    fieldsets = (
        ("Basic Information", {"fields": ("invoice_number", "invoice_type", "status")}),
        ("Organizations", {"fields": ("company", "customer")}),
        ("Dates", {"fields": ("issue_date", "due_date", "delivery_date")}),
        ("Financial Information", {"fields": ("currency", "subtotal", "tax_amount", "total_amount")}),
        ("Payment Information", {"fields": ("payment_terms", "payment_method", "payment_reference")}),
        ("Files", {"fields": ("pdf_file", "xml_file")}),
        ("Additional Information", {"fields": ("notes", "created_by", "created_at", "updated_at")}),
    )

    def customer_name(self, obj):
        """Display customer name."""
        return obj.customer.name if obj.customer else ""

    customer_name.short_description = "Customer"

    def company_name(self, obj):
        """Display company name."""
        return obj.company.name if obj.company else ""

    company_name.short_description = "Company"

    def generate_pdfa3(self, request, queryset):
        """Generate PDF/A-3 documents with embedded XML for selected invoices."""
        service = InvoiceService()
        success_count = 0
        error_count = 0

        for invoice in queryset:
            try:
                result = service.generate_invoice_files(invoice)
                if result["is_valid"]:
                    success_count += 1
                else:
                    messages.warning(
                        request,
                        f"Generated invoice #{invoice.invoice_number} but with XML validation warnings: "
                        f"{', '.join(result['validation_errors'][:3])}",
                    )
                    success_count += 1
            except Exception as e:
                error_count += 1
                messages.error(
                    request,
                    f"Error generating PDF/A-3 for invoice #{invoice.invoice_number}: {str(e)[:100]}...",
                )

        if success_count:
            messages.success(request, f"Successfully generated {success_count} PDF/A-3 document(s) with embedded XML.")

        if error_count:
            messages.error(request, f"Failed to generate {error_count} PDF/A-3 document(s).")

    generate_pdfa3.short_description = "Generate PDF/A-3 with XML"

    def pdf_actions(self, obj):
        """Display PDF action buttons in the list view."""
        buttons = []

        # Generate PDF button with correct URL
        buttons.append(
            f'<a href="/admin/invoice/{obj.pk}/generate_pdf/" class="button" '
            'style="background-color:#417690; color:white; padding:3px 8px; '
            'border-radius:4px; text-decoration:none; font-size:0.8em; margin-right:5px;">'
            "Generate PDF/A-3</a>"
        )

        # View PDF button (if exists)
        if obj.pdf_file:
            buttons.append(
                f'<a href="{obj.pdf_file.url}" target="_blank" class="button" '
                'style="background-color:#79aec8; color:white; padding:3px 8px; '
                'border-radius:4px; text-decoration:none; font-size:0.8em;">'
                "View PDF</a>"
            )

        return format_html("&nbsp;".join(buttons))

    pdf_actions.short_description = "PDF Actions"

    def pdf_preview(self, obj):
        """Display PDF preview and download link in the detail view."""
        if obj.pdf_file:
            return format_html(
                "<div>"
                '<p><a href="{}" target="_blank" class="button" '
                'style="background-color:#79aec8; color:white; padding:5px 10px; '
                'border-radius:4px; text-decoration:none;">View PDF</a></p>'
                '<p><a href="/admin/invoice/{}/generate_pdf/" class="button" '
                'style="background-color:#417690; color:white; padding:5px 10px; '
                'border-radius:4px; text-decoration:none;">Regenerate PDF/A-3</a></p>'
                "</div>",
                obj.pdf_file.url,
                obj.pk,
            )
        else:
            return format_html(
                "<div>"
                "<p>No PDF file generated yet.</p>"
                '<p><a href="/admin/invoice/{}/generate_pdf/" class="button" '
                'style="background-color:#417690; color:white; padding:5px 10px; '
                'border-radius:4px; text-decoration:none;">Generate PDF/A-3</a></p>'
                "</div>",
                obj.pk,
            )

    pdf_preview.short_description = "PDF Preview"


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    """Admin interface for InvoiceLine model."""

    list_display = ("invoice_number", "description", "quantity", "unit_price", "tax_rate", "line_total")
    list_filter = ("invoice",)
    search_fields = ("description", "product_code", "invoice__invoice_number")

    def invoice_number(self, obj):
        """Display invoice number."""
        return obj.invoice.invoice_number if obj.invoice else ""

    invoice_number.short_description = "Invoice"


@admin.register(InvoiceAttachment)
class InvoiceAttachmentAdmin(admin.ModelAdmin):
    """Admin interface for InvoiceAttachment model."""

    list_display = ("description", "invoice_number", "file", "uploaded_at")
    list_filter = ("uploaded_at",)
    search_fields = ("description", "invoice__invoice_number")

    def invoice_number(self, obj):
        """Display invoice number."""
        return obj.invoice.invoice_number if obj.invoice else ""

    invoice_number.short_description = "Invoice"
