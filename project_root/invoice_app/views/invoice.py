"""Views for Invoice, InvoiceLine, and InvoiceAttachment CRUD operations."""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.base import View

from invoice_app.forms import InvoiceAttachmentForm, InvoiceForm, InvoiceLineForm
from invoice_app.models import Invoice, InvoiceAttachment, InvoiceLine
from invoice_app.services.invoice_service import InvoiceService


# Invoice Views
class InvoiceListView(LoginRequiredMixin, ListView):
    """View for listing all Invoices."""

    model = Invoice
    template_name = "invoice_app/invoice_list.html"
    context_object_name = "invoices"
    ordering = ["-issue_date"]
    paginate_by = 10


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    """View for showing details of an Invoice."""

    model = Invoice
    template_name = "invoice_app/invoice_detail.html"
    context_object_name = "invoice"


class InvoicePreviewView(LoginRequiredMixin, DetailView):
    """PDF-Vorschau einer Rechnung im Browser.

    Rendert dasselbe Template wie WeasyPrint später nutzt.
    URL: /invoices/<pk>/preview/
    """

    model = Invoice
    template_name = "invoice_app/invoice_pdf.html"
    context_object_name = "invoice"


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new Invoice."""

    model = Invoice
    form_class = InvoiceForm
    template_name = "invoice_app/invoice_form.html"
    success_url = reverse_lazy("invoice-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Invoice"
        context["action"] = "Create"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Invoice created successfully!")
        return super().form_valid(form)


class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating an existing Invoice."""

    model = Invoice
    form_class = InvoiceForm
    template_name = "invoice_app/invoice_form.html"
    success_url = reverse_lazy("invoice-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Update Invoice"
        context["action"] = "Update"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Invoice updated successfully!")
        return super().form_valid(form)


class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting an Invoice."""

    model = Invoice
    template_name = "invoice_app/invoice_confirm_delete.html"
    success_url = reverse_lazy("invoice-list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Invoice deleted successfully!")
        return super().delete(request, *args, **kwargs)


# InvoiceLine Views (Nested under Invoice)
class InvoiceLineCreateView(CreateView):
    """View for creating a new InvoiceLine."""

    model = InvoiceLine
    form_class = InvoiceLineForm
    template_name = "invoice_app/invoice_line_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = Invoice.objects.get(pk=self.kwargs["invoice_pk"])
        context["invoice"] = invoice
        context["title"] = f"Add Line Item to Invoice #{invoice.invoice_number}"
        context["action"] = "Create"
        return context

    def form_valid(self, form):
        form.instance.invoice_id = self.kwargs["invoice_pk"]
        messages.success(self.request, "Invoice line added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("invoice-detail", kwargs={"pk": self.kwargs["invoice_pk"]})


class InvoiceLineUpdateView(UpdateView):
    """View for updating an existing InvoiceLine."""

    model = InvoiceLine
    form_class = InvoiceLineForm
    template_name = "invoice_app/invoice_line_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.object.invoice
        context["title"] = f"Edit Line Item on Invoice #{self.object.invoice.invoice_number}"
        context["action"] = "Update"
        return context

    def get_success_url(self):
        return reverse("invoice-detail", kwargs={"pk": self.object.invoice.pk})

    def form_valid(self, form):
        messages.success(self.request, "Invoice line updated successfully!")
        return super().form_valid(form)


class InvoiceLineDeleteView(DeleteView):
    """View for deleting an InvoiceLine."""

    model = InvoiceLine
    template_name = "invoice_app/invoice_line_confirm_delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.object.invoice
        return context

    def get_success_url(self):
        return reverse("invoice-detail", kwargs={"pk": self.object.invoice.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Invoice line deleted successfully!")
        return super().delete(request, *args, **kwargs)


# InvoiceAttachment Views (Nested under Invoice)
class InvoiceAttachmentCreateView(CreateView):
    """View for creating a new InvoiceAttachment."""

    model = InvoiceAttachment
    form_class = InvoiceAttachmentForm
    template_name = "invoice_app/invoice_attachment_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = Invoice.objects.get(pk=self.kwargs["invoice_pk"])
        context["invoice"] = invoice
        context["title"] = f"Add Attachment to Invoice #{invoice.invoice_number}"
        context["action"] = "Upload"
        return context

    def form_valid(self, form):
        form.instance.invoice_id = self.kwargs["invoice_pk"]
        messages.success(self.request, "Attachment added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("invoice-detail", kwargs={"pk": self.kwargs["invoice_pk"]})


class InvoiceAttachmentDeleteView(DeleteView):
    """View for deleting an InvoiceAttachment."""

    model = InvoiceAttachment
    template_name = "invoice_app/invoice_attachment_confirm_delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.object.invoice
        return context

    def get_success_url(self):
        return reverse("invoice-detail", kwargs={"pk": self.object.invoice.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Attachment deleted successfully!")
        return super().delete(request, *args, **kwargs)


@method_decorator(staff_member_required, name="dispatch")
class AdminGeneratePdfView(View):
    """View for generating PDF/A-3 files from the admin interface."""

    def get(self, request, pk):
        """Handle GET request to generate PDF/A-3 for an invoice."""
        # Get the invoice or return 404
        invoice = get_object_or_404(Invoice, pk=pk)

        try:
            # Initialize service
            invoice_service = InvoiceService()

            # Generate PDF/A-3 with embedded XML (using BASIC profile by default)
            result = invoice_service.generate_invoice_files(invoice)

            if result["is_valid"]:
                messages.success(
                    request, f"PDF/A-3 with embedded XML successfully generated for invoice #{invoice.invoice_number}"
                )
            else:
                messages.warning(
                    request,
                    f"PDF/A-3 generated but with XML validation warnings: {', '.join(result['validation_errors'][:3])}",
                )

        except Exception as e:
            messages.error(request, f"Error generating PDF/A-3: {str(e)[:100]}...")

        # Redirect back to the admin page
        return HttpResponseRedirect(reverse("admin:invoice_app_invoice_change", args=[invoice.pk]))
