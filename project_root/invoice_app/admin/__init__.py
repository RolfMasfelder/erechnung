# Admin package for invoice_app
# Registers all admin classes with Django admin

from invoice_app.admin.business_partner import BusinessPartnerAdmin
from invoice_app.admin.company import CompanyAdmin
from invoice_app.admin.country import CountryAdmin, CountryTaxRateAdmin
from invoice_app.admin.gdpr import (
    ConsentRecordAdmin,
    DataSubjectRequestAdmin,
    PrivacyImpactAssessmentAdmin,
    ProcessingActivityAdmin,
)
from invoice_app.admin.inlines import InvoiceAttachmentInline, InvoiceLineInline
from invoice_app.admin.invoice import InvoiceAdmin, InvoiceAttachmentAdmin, InvoiceLineAdmin
from invoice_app.admin.mixins import RBACPermissionMixin
from invoice_app.admin.product import ProductAdmin
from invoice_app.admin.system import AuditLogAdmin, SystemConfigAdmin
from invoice_app.admin.user import UserProfileAdmin, UserRoleAdmin


__all__ = [
    # Mixins
    "RBACPermissionMixin",
    # Inlines
    "InvoiceLineInline",
    "InvoiceAttachmentInline",
    # Admin classes
    "CompanyAdmin",
    "CountryAdmin",
    "CountryTaxRateAdmin",
    "ProductAdmin",
    "BusinessPartnerAdmin",
    "InvoiceAdmin",
    "InvoiceLineAdmin",
    "InvoiceAttachmentAdmin",
    "UserRoleAdmin",
    "UserProfileAdmin",
    "AuditLogAdmin",
    "SystemConfigAdmin",
    # GDPR / DSGVO
    "DataSubjectRequestAdmin",
    "ProcessingActivityAdmin",
    "PrivacyImpactAssessmentAdmin",
    "ConsentRecordAdmin",
]
