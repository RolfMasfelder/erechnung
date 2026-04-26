# Views package for invoice_app
# Organizes views by domain

from invoice_app.views.base import HomeView  # noqa: I001
from invoice_app.views.business_partner import (
    BusinessPartnerCreateView,
    BusinessPartnerDeleteView,
    BusinessPartnerDetailView,
    BusinessPartnerListView,
    BusinessPartnerUpdateView,
)
from invoice_app.views.company import (
    CompanyCreateView,
    CompanyDeleteView,
    CompanyDetailView,
    CompanyListView,
    CompanyUpdateView,
)
from invoice_app.views.health import HealthCheckError, health_check, health_detailed, readiness_check
from invoice_app.views.invoice import (
    AdminGeneratePdfView,
    InvoiceAttachmentCreateView,
    InvoiceAttachmentDeleteView,
    InvoiceCreateView,
    InvoiceDeleteView,
    InvoiceDetailView,
    InvoiceLineCreateView,
    InvoiceLineDeleteView,
    InvoiceLineUpdateView,
    InvoiceListView,
    InvoicePreviewView,
    InvoiceUpdateView,
)

__all__ = [
    # Base views
    "HomeView",
    # Company views
    "CompanyListView",
    "CompanyDetailView",
    "CompanyCreateView",
    "CompanyUpdateView",
    "CompanyDeleteView",
    # BusinessPartner views
    "BusinessPartnerListView",
    "BusinessPartnerDetailView",
    "BusinessPartnerCreateView",
    "BusinessPartnerUpdateView",
    "BusinessPartnerDeleteView",
    # Invoice views
    "InvoiceListView",
    "InvoiceDetailView",
    "InvoicePreviewView",
    "InvoiceCreateView",
    "InvoiceUpdateView",
    "InvoiceDeleteView",
    "InvoiceLineCreateView",
    "InvoiceLineUpdateView",
    "InvoiceLineDeleteView",
    "InvoiceAttachmentCreateView",
    "InvoiceAttachmentDeleteView",
    "AdminGeneratePdfView",
    # Health check views
    "health_check",
    "health_detailed",
    "readiness_check",
    "HealthCheckError",
]
