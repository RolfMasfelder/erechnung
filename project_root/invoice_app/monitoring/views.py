"""
Custom Prometheus /metrics view that refreshes business KPI gauges
from the database before exporting metrics.

The default django-prometheus view only exports in-process counters.
DB-backed gauges (invoice counts by status, partner count, etc.) need
to be collected each scrape because the web worker process does not
share memory with Celery workers.
"""

import logging

from django_prometheus.exports import ExportToDjangoView

from invoice_app.monitoring.collectors import collect_business_metrics


logger = logging.getLogger(__name__)


def metrics_with_business_kpis(request):
    """Refresh business KPI gauges, then delegate to django-prometheus."""
    try:
        collect_business_metrics()
    except Exception:
        logger.exception("Failed to collect business metrics before scrape")
    return ExportToDjangoView(request)
