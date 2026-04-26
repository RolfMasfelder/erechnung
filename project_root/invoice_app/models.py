"""
Invoice app models module.
This file imports all models from the models directory.
"""

# Import models from subdirectory modules
from invoice_app.models.config import SystemConfig
from invoice_app.models.invoice import (
    AuditLog,
    Company,
    Customer,
    Invoice,
    InvoiceAttachment,
    InvoiceLine,
    Product,
)
from invoice_app.models.user import UserProfile, UserRole


# Define all models that should be available directly from invoice_app.models
__all__ = [
    "Company",
    "Customer",
    "Product",
    "AuditLog",
    "Invoice",
    "InvoiceLine",
    "InvoiceAttachment",
    "UserRole",
    "UserProfile",
    "SystemConfig",
]
