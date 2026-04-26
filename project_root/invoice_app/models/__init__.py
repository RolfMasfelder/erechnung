"""
Invoice app models package.
This file imports and re-exports all models from the package modules.
"""

from invoice_app.models.audit import AuditLog  # noqa: I001
from invoice_app.models.business_partner import BusinessPartner
from invoice_app.models.company import Company
from invoice_app.models.config import SystemConfig
from invoice_app.models.country import Country, CountryTaxRate
from invoice_app.models.gdpr import ConsentRecord, DataSubjectRequest, PrivacyImpactAssessment, ProcessingActivity
from invoice_app.models.helpers import COUNTRY_CODE_MAP, serialize_for_audit
from invoice_app.models.invoice_models import (
    AttachmentType,
    Invoice,
    InvoiceAllowanceCharge,
    InvoiceAttachment,
    InvoiceLine,
)
from invoice_app.models.product import Product
from invoice_app.models.user import UserProfile, UserRole

# Expose inner TextChoices for drf-spectacular ENUM_NAME_OVERRIDES
InvoiceStatus = Invoice.InvoiceStatus
RequestStatus = DataSubjectRequest.RequestStatus
AssessmentStatus = PrivacyImpactAssessment.AssessmentStatus

__all__ = [
    # Core business models
    "Company",
    "Country",
    "CountryTaxRate",
    "BusinessPartner",
    "Product",
    "Invoice",
    "InvoiceLine",
    "InvoiceAttachment",
    "AttachmentType",
    "InvoiceAllowanceCharge",
    # User management
    "UserRole",
    "UserProfile",
    # System
    "SystemConfig",
    "AuditLog",
    # GDPR / DSGVO
    "DataSubjectRequest",
    "ProcessingActivity",
    "PrivacyImpactAssessment",
    "ConsentRecord",
    # Helpers
    "serialize_for_audit",
    "COUNTRY_CODE_MAP",
]
