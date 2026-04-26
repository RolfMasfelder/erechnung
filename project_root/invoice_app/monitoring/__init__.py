"""
Monitoring module for eRechnung application.

Provides Prometheus metrics for:
- Business KPIs (invoice counts, revenue, overdue invoices)
- Application health (PDF generation, XML validation)
- Performance metrics (request latency by endpoint)
"""

from invoice_app.monitoring.metrics import (  # noqa: F401
    INVOICE_CREATED_TOTAL,
    INVOICE_STATUS_GAUGE,
    INVOICES_TOTAL_AMOUNT,
    PDF_GENERATION_DURATION,
    PDF_GENERATION_ERRORS,
    PDF_GENERATION_TOTAL,
    XML_VALIDATION_DURATION,
    XML_VALIDATION_ERRORS,
    XML_VALIDATION_TOTAL,
)
