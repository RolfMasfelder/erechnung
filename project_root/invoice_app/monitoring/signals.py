"""
Django signal handlers that update Prometheus counters in real time.

Connected in InvoiceAppConfig.ready() so they fire automatically
whenever model instances are saved / tokens issued.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver


logger = logging.getLogger(__name__)


@receiver(post_save, sender="invoice_app.Invoice")
def on_invoice_created(sender, instance, created, **kwargs):
    """Increment the invoice-created counter when a new Invoice is saved."""
    if created:
        from .metrics import INVOICE_CREATED_TOTAL

        invoice_type = getattr(instance, "invoice_type_code", "380")
        INVOICE_CREATED_TOTAL.labels(invoice_type=str(invoice_type)).inc()


def connect_auth_signals():
    """
    Connect JWT authentication signals for login tracking.
    Call this from AppConfig.ready().
    """
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken  # noqa: F401

        # Track successful token issues
        @receiver(post_save, sender=OutstandingToken)
        def on_token_issued(sender, instance, created, **kwargs):
            if created:
                from .metrics import AUTH_LOGIN_TOTAL

                AUTH_LOGIN_TOTAL.labels(result="success").inc()

    except (ImportError, LookupError):
        # token_blacklist app might not be installed
        pass
