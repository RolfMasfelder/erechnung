"""Views for BusinessPartner model CRUD operations."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from invoice_app.forms import BusinessPartnerForm
from invoice_app.models import BusinessPartner


class BusinessPartnerListView(LoginRequiredMixin, ListView):
    """View for listing all Business Partners."""

    model = BusinessPartner
    template_name = "invoice_app/business_partner_list.html"
    context_object_name = "partners"
    ordering = ["partner_number"]
    paginate_by = 10


class BusinessPartnerDetailView(LoginRequiredMixin, DetailView):
    """View for showing details of a Business Partner."""

    model = BusinessPartner
    template_name = "invoice_app/business_partner_detail.html"
    context_object_name = "partner"


class BusinessPartnerCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new Business Partner."""

    model = BusinessPartner
    form_class = BusinessPartnerForm
    template_name = "invoice_app/business_partner_form.html"
    success_url = reverse_lazy("business-partner-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Business Partner"
        context["action"] = "Create"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Business Partner created successfully!")
        return super().form_valid(form)


class BusinessPartnerUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating an existing Business Partner."""

    model = BusinessPartner
    form_class = BusinessPartnerForm
    template_name = "invoice_app/business_partner_form.html"
    success_url = reverse_lazy("business-partner-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Update Business Partner"
        context["action"] = "Update"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Business Partner updated successfully!")
        return super().form_valid(form)


class BusinessPartnerDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting a Business Partner."""

    model = BusinessPartner
    template_name = "invoice_app/business_partner_confirm_delete.html"
    success_url = reverse_lazy("business-partner-list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Business Partner deleted successfully!")
        return super().delete(request, *args, **kwargs)
