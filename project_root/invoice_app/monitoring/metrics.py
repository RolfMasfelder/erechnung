"""
Custom Prometheus metrics for eRechnung business KPIs.

These metrics supplement the automatic django-prometheus metrics
(request latency, DB queries, cache hits) with domain-specific counters
and gauges that provide operational insight into invoice processing.
"""

from prometheus_client import Counter, Gauge, Histogram


# ---------------------------------------------------------------------------
# Invoice lifecycle
# ---------------------------------------------------------------------------
INVOICE_CREATED_TOTAL = Counter(
    "erechnung_invoices_created_total",
    "Total number of invoices created",
    ["invoice_type"],  # 380=invoice, 381=credit_note
)

INVOICE_STATUS_GAUGE = Gauge(
    "erechnung_invoices_by_status",
    "Current number of invoices by status",
    ["status"],  # DRAFT, SENT, PAID, CANCELLED, OVERDUE
)

INVOICES_TOTAL_AMOUNT = Gauge(
    "erechnung_invoices_total_amount_eur",
    "Sum of invoice amounts in EUR by status",
    ["status"],
)

INVOICE_OVERDUE_COUNT = Gauge(
    "erechnung_invoices_overdue_count",
    "Number of invoices past due date that are not paid or cancelled",
)

# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------
PDF_GENERATION_TOTAL = Counter(
    "erechnung_pdf_generation_total",
    "Total PDF generation attempts",
    ["result"],  # success, error
)

PDF_GENERATION_DURATION = Histogram(
    "erechnung_pdf_generation_duration_seconds",
    "Time spent generating a PDF/A-3 document",
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0],
)

PDF_GENERATION_ERRORS = Counter(
    "erechnung_pdf_generation_errors_total",
    "Total PDF generation errors by type",
    ["error_type"],  # ghostscript, template, xml_embed, io
)

# ---------------------------------------------------------------------------
# XML / ZUGFeRD validation
# ---------------------------------------------------------------------------
XML_VALIDATION_TOTAL = Counter(
    "erechnung_xml_validation_total",
    "Total XML validation attempts",
    ["result"],  # valid, invalid, error
)

XML_VALIDATION_DURATION = Histogram(
    "erechnung_xml_validation_duration_seconds",
    "Time spent validating a ZUGFeRD/Factur-X XML document",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
)

XML_VALIDATION_ERRORS = Counter(
    "erechnung_xml_validation_errors_total",
    "Total XML validation errors by category",
    ["error_category"],  # schema, business_rule, parse_error
)

# ---------------------------------------------------------------------------
# Business partners
# ---------------------------------------------------------------------------
BUSINESS_PARTNERS_TOTAL = Gauge(
    "erechnung_business_partners_total",
    "Total number of business partners (customers)",
)

# ---------------------------------------------------------------------------
# User / Auth
# ---------------------------------------------------------------------------
AUTH_LOGIN_TOTAL = Counter(
    "erechnung_auth_login_total",
    "Total authentication attempts",
    ["result"],  # success, failure
)

ACTIVE_USERS_GAUGE = Gauge(
    "erechnung_active_users",
    "Number of users who logged in within the last 30 days",
)

# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------
CELERY_TASK_TOTAL = Counter(
    "erechnung_celery_task_total",
    "Total Celery tasks executed",
    ["task_name", "result"],  # success, failure
)

CELERY_TASK_DURATION = Histogram(
    "erechnung_celery_task_duration_seconds",
    "Time to complete Celery tasks",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)
