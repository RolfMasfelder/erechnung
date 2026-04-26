"""
URL configuration for custom admin actions in invoice_app.
"""

from django.urls import path

from invoice_app import views


urlpatterns = [
    # Admin action to generate PDF/A-3
    path("", views.AdminGeneratePdfView.as_view(), name="admin-generate-pdf"),
]
