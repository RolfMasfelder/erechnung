"""Views for Company model CRUD operations."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from invoice_app.forms import CompanyForm
from invoice_app.models import Company


class CompanyListView(LoginRequiredMixin, ListView):
    """View for listing all Companies."""

    model = Company
    template_name = "invoice_app/company_list.html"
    context_object_name = "companies"
    ordering = ["name"]
    paginate_by = 10


class CompanyDetailView(LoginRequiredMixin, DetailView):
    """View for showing details of a Company."""

    model = Company
    template_name = "invoice_app/company_detail.html"
    context_object_name = "company"


class CompanyCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new Company."""

    model = Company
    form_class = CompanyForm
    template_name = "invoice_app/company_form.html"
    success_url = reverse_lazy("company-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Company"
        context["action"] = "Create"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Company created successfully!")
        return super().form_valid(form)


class CompanyUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating an existing Company."""

    model = Company
    form_class = CompanyForm
    template_name = "invoice_app/company_form.html"
    success_url = reverse_lazy("company-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Update Company"
        context["action"] = "Update"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Company updated successfully!")
        return super().form_valid(form)


class CompanyDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting a Company."""

    model = Company
    template_name = "invoice_app/company_confirm_delete.html"
    success_url = reverse_lazy("company-list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Company deleted successfully!")
        return super().delete(request, *args, **kwargs)
