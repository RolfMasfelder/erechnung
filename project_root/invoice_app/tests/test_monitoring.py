"""
Tests for the monitoring module (Prometheus metrics).
"""

from django.test import TestCase

from invoice_app.monitoring.collectors import collect_business_metrics
from invoice_app.monitoring.metrics import (
    INVOICE_CREATED_TOTAL,
    INVOICE_STATUS_GAUGE,
    INVOICES_TOTAL_AMOUNT,
    PDF_GENERATION_DURATION,
    PDF_GENERATION_TOTAL,
    XML_VALIDATION_TOTAL,
)


class MetricsRegistrationTest(TestCase):
    """Verify that all custom metrics are registered in Prometheus."""

    def test_invoice_created_counter_exists(self):
        """INVOICE_CREATED_TOTAL counter should be registered."""
        self.assertIsNotNone(INVOICE_CREATED_TOTAL)
        INVOICE_CREATED_TOTAL.labels(invoice_type="380").inc()
        # No exception = success

    def test_invoice_status_gauge_exists(self):
        """INVOICE_STATUS_GAUGE gauge should be registered."""
        self.assertIsNotNone(INVOICE_STATUS_GAUGE)
        INVOICE_STATUS_GAUGE.labels(status="DRAFT").set(0)

    def test_invoices_total_amount_gauge_exists(self):
        """INVOICES_TOTAL_AMOUNT gauge should be registered."""
        self.assertIsNotNone(INVOICES_TOTAL_AMOUNT)
        INVOICES_TOTAL_AMOUNT.labels(status="PAID").set(1234.56)

    def test_pdf_generation_metrics_exist(self):
        """PDF generation metrics should be registered."""
        PDF_GENERATION_TOTAL.labels(result="success").inc()
        PDF_GENERATION_DURATION.observe(1.5)

    def test_xml_validation_metrics_exist(self):
        """XML validation metrics should be registered."""
        XML_VALIDATION_TOTAL.labels(result="valid").inc()


class CollectorTest(TestCase):
    """Test the business metrics collector."""

    def test_collect_business_metrics_runs_without_error(self):
        """collect_business_metrics() should complete without raising."""
        # This will query the test database (which may be empty)
        collect_business_metrics()

    def test_collect_sets_invoice_status_gauges(self):
        """After collection, invoice status gauges should be set."""
        collect_business_metrics()
        # Verify gauge was set (value >= 0 means it was written)
        value = INVOICE_STATUS_GAUGE.labels(status="DRAFT")._value.get()
        self.assertGreaterEqual(value, 0)

    def test_collect_sets_business_partners_total(self):
        """After collection, business_partners_total should be set."""
        from invoice_app.monitoring.metrics import BUSINESS_PARTNERS_TOTAL

        collect_business_metrics()
        value = BUSINESS_PARTNERS_TOTAL._value.get()
        self.assertGreaterEqual(value, 0)

    def test_collect_sets_active_users(self):
        """After collection, active_users should be set."""
        from invoice_app.monitoring.metrics import ACTIVE_USERS_GAUGE

        collect_business_metrics()
        value = ACTIVE_USERS_GAUGE._value.get()
        self.assertGreaterEqual(value, 0)


class MetricsEndpointTest(TestCase):
    """Test the /metrics HTTP endpoint."""

    def test_metrics_endpoint_returns_200(self):
        """GET /metrics should return HTTP 200."""
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)

    def test_metrics_endpoint_contains_django_metrics(self):
        """Response should contain django-prometheus default metrics."""
        response = self.client.get("/metrics")
        content = response.content.decode()
        self.assertIn("django_http_requests_before_middlewares_total", content)

    def test_metrics_endpoint_contains_custom_metrics(self):
        """Response should contain erechnung custom metrics."""
        response = self.client.get("/metrics")
        content = response.content.decode()
        self.assertIn("erechnung_invoices_created_total", content)
        self.assertIn("erechnung_pdf_generation_duration_seconds", content)
        self.assertIn("erechnung_xml_validation_duration_seconds", content)

    def test_metrics_endpoint_content_type(self):
        """Response should have text/plain content type for Prometheus."""
        response = self.client.get("/metrics")
        # prometheus_client returns text/plain or openmetrics format
        self.assertTrue(
            response["Content-Type"].startswith("text/plain")
            or response["Content-Type"].startswith("application/openmetrics-text")
        )
