"""
Celery tasks for periodic Prometheus metric collection.

Registered via Celery beat schedule in settings.py.
"""

import logging

from celery import shared_task


logger = logging.getLogger(__name__)


@shared_task(name="monitoring.collect_business_metrics")
def collect_business_metrics_task():
    """
    Celery task that refreshes all gauge metrics from the database.
    Scheduled to run every 60 seconds via Celery beat.
    """
    from invoice_app.monitoring.collectors import collect_business_metrics

    collect_business_metrics()
    logger.debug("Business metrics collected successfully")
