"""
Periodic gauge collector for database-backed business metrics.

Call ``collect_business_metrics()`` on a schedule (e.g. every 60 s via
Celery beat or a Prometheus custom collector) to refresh gauges that
represent current DB state such as invoice counts by status.
"""

import logging
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone


logger = logging.getLogger(__name__)


def collect_business_metrics() -> None:
    """Refresh all Gauge metrics from the database."""
    try:
        _collect_invoice_metrics()
        _collect_partner_metrics()
        _collect_user_metrics()
    except Exception:
        logger.exception("Error collecting business metrics")


def _collect_invoice_metrics() -> None:
    from invoice_app.models import Invoice

    from .metrics import INVOICE_OVERDUE_COUNT, INVOICE_STATUS_GAUGE, INVOICES_TOTAL_AMOUNT

    # Count by status
    for status_value, _label in Invoice.InvoiceStatus.choices:
        count = Invoice.objects.filter(status=status_value).count()
        INVOICE_STATUS_GAUGE.labels(status=status_value).set(count)

        # Sum amounts by status
        total = Invoice.objects.filter(status=status_value).aggregate(total=Sum("total_amount"))["total"] or 0
        INVOICES_TOTAL_AMOUNT.labels(status=status_value).set(float(total))

    # Overdue invoices (due_date passed, not PAID/CANCELLED)
    overdue_count = (
        Invoice.objects.filter(
            due_date__lt=timezone.now().date(),
        )
        .exclude(
            status__in=[
                Invoice.InvoiceStatus.PAID,
                Invoice.InvoiceStatus.CANCELLED,
            ],
        )
        .count()
    )
    INVOICE_OVERDUE_COUNT.set(overdue_count)


def _collect_partner_metrics() -> None:
    from invoice_app.models import BusinessPartner

    from .metrics import BUSINESS_PARTNERS_TOTAL

    BUSINESS_PARTNERS_TOTAL.set(BusinessPartner.objects.count())


def _collect_user_metrics() -> None:
    from django.contrib.auth import get_user_model

    from .metrics import ACTIVE_USERS_GAUGE

    User = get_user_model()
    thirty_days_ago = timezone.now() - timedelta(days=30)
    active = User.objects.filter(last_login__gte=thirty_days_ago).count()
    ACTIVE_USERS_GAUGE.set(active)
