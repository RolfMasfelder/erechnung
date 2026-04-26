"""
Helper utilities for invoice models.

Contains shared functions used across multiple model files.
"""

from datetime import date, datetime
from decimal import Decimal


def serialize_for_audit(obj):
    """
    Serialize objects for audit logging, handling special types like Decimal.
    """
    if isinstance(obj, dict):
        return {key: serialize_for_audit(value) for key, value in obj.items()}
    elif isinstance(obj, list | tuple):
        return [serialize_for_audit(item) for item in obj]
    elif isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, datetime | date):
        return obj.isoformat()
    elif hasattr(obj, "pk"):  # Django model instance
        return str(obj.pk)
    else:
        return obj


# Country code mapping for ZUGFeRD XML - ISO 3166-1 alpha-2 codes
COUNTRY_CODE_MAP = {
    "Deutschland": "DE",
    "Germany": "DE",
    "Österreich": "AT",
    "Austria": "AT",
    "Schweiz": "CH",
    "Switzerland": "CH",
    "Frankreich": "FR",
    "France": "FR",
}
