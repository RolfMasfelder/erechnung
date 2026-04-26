"""
URL configuration for invoice_app.
"""

from django.urls import path  # noqa: I001
from invoice_app import views

urlpatterns = [
    # Invoice PDF Preview (Browser-Vorschau des PDF-Templates)
    path("invoices/<int:pk>/preview/", views.InvoicePreviewView.as_view(), name="invoice-preview"),
    # Home view
    path("", views.HomeView.as_view(), name="home"),
    # Company URLs
    path("companies/", views.CompanyListView.as_view(), name="company-list"),
    path("companies/new/", views.CompanyCreateView.as_view(), name="company-create"),
    path("companies/<int:pk>/", views.CompanyDetailView.as_view(), name="company-detail"),
    path("companies/<int:pk>/edit/", views.CompanyUpdateView.as_view(), name="company-update"),
    path("companies/<int:pk>/delete/", views.CompanyDeleteView.as_view(), name="company-delete"),
    # Business Partner URLs
    path("business-partners/", views.BusinessPartnerListView.as_view(), name="business-partner-list"),
    path("business-partners/new/", views.BusinessPartnerCreateView.as_view(), name="business-partner-create"),
    path("business-partners/<int:pk>/", views.BusinessPartnerDetailView.as_view(), name="business-partner-detail"),
    path(
        "business-partners/<int:pk>/edit/", views.BusinessPartnerUpdateView.as_view(), name="business-partner-update"
    ),
    path(
        "business-partners/<int:pk>/delete/", views.BusinessPartnerDeleteView.as_view(), name="business-partner-delete"
    ),
    # Invoice URLs
    path("invoices/", views.InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/new/", views.InvoiceCreateView.as_view(), name="invoice-create"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/<int:pk>/edit/", views.InvoiceUpdateView.as_view(), name="invoice-update"),
    path("invoices/<int:pk>/delete/", views.InvoiceDeleteView.as_view(), name="invoice-delete"),
    # Invoice Line URLs (nested under invoices)
    path("invoices/<int:invoice_pk>/lines/add/", views.InvoiceLineCreateView.as_view(), name="invoice-line-create"),
    path("invoices/lines/<int:pk>/edit/", views.InvoiceLineUpdateView.as_view(), name="invoice-line-update"),
    path("invoices/lines/<int:pk>/delete/", views.InvoiceLineDeleteView.as_view(), name="invoice-line-delete"),
    # Invoice Attachment URLs (nested under invoices)
    path(
        "invoices/<int:invoice_pk>/attachments/add/",
        views.InvoiceAttachmentCreateView.as_view(),
        name="invoice-attachment-create",
    ),
    path(
        "invoices/attachments/<int:pk>/delete/",
        views.InvoiceAttachmentDeleteView.as_view(),
        name="invoice-attachment-delete",
    ),
]
