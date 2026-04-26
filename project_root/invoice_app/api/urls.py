"""
URL patterns for the invoice_app API.
"""

from django.urls import include, path  # noqa: I001
from rest_framework.routers import DefaultRouter

from .rest_views import (
    AuditLogViewSet,
    BusinessPartnerImportView,
    BusinessPartnerViewSet,
    CompanyViewSet,
    ComplianceReportView,
    ConsentRecordViewSet,
    CountryViewSet,
    DashboardStatsView,
    DataSubjectRequestViewSet,
    InvoiceAllowanceChargeViewSet,
    InvoiceAttachmentViewSet,
    InvoiceLineViewSet,
    InvoiceViewSet,
    PrivacyImpactAssessmentViewSet,
    ProcessingActivityViewSet,
    ProductImportView,
    ProductViewSet,
    RetentionSummaryView,
)
from .views.version_view import VersionView

router = DefaultRouter()
router.register(r"companies", CompanyViewSet, basename="api-company")
router.register(r"countries", CountryViewSet, basename="api-country")
router.register(r"business-partners", BusinessPartnerViewSet, basename="api-business-partner")
router.register(r"products", ProductViewSet, basename="api-product")
router.register(r"audit-logs", AuditLogViewSet, basename="api-audit-log")
router.register(r"invoices", InvoiceViewSet, basename="api-invoice")
router.register(r"invoice-lines", InvoiceLineViewSet, basename="api-invoice-line")
router.register(r"invoice-attachments", InvoiceAttachmentViewSet, basename="api-invoice-attachment")
router.register(r"invoice-allowance-charges", InvoiceAllowanceChargeViewSet, basename="api-invoice-allowance-charge")
# GDPR / DSGVO
router.register(r"gdpr/requests", DataSubjectRequestViewSet, basename="api-dsr")
router.register(r"gdpr/processing-activities", ProcessingActivityViewSet, basename="api-processing-activity")
router.register(r"gdpr/impact-assessments", PrivacyImpactAssessmentViewSet, basename="api-pia")
router.register(r"gdpr/consent-records", ConsentRecordViewSet, basename="api-consent-record")

urlpatterns = [
    # Version endpoint (public, no auth)
    path("version/", VersionView.as_view(), name="api-version"),
    # Import endpoints first (before router to avoid matching as IDs)
    path("business-partners/import/", BusinessPartnerImportView.as_view(), name="api-business-partner-import"),
    path("products/import/", ProductImportView.as_view(), name="api-product-import"),
    # Stats endpoint
    path("stats/", DashboardStatsView.as_view(), name="api-stats"),
    # GoBD Compliance endpoints
    path(
        "compliance/integrity-report/",
        ComplianceReportView.as_view(),
        name="api-compliance-integrity-report",
    ),
    path(
        "compliance/retention-summary/",
        RetentionSummaryView.as_view(),
        name="api-compliance-retention-summary",
    ),
    # Router endpoints last
    path("", include(router.urls)),
]
