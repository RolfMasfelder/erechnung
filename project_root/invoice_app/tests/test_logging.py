"""
Tests for structured JSON logging and request correlation IDs (Task 2.2).
"""

import json
import logging
from io import StringIO
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from invoice_project.logging import ERehnungJsonFormatter, RequestIDFilter
from invoice_project.middleware import RequestIDMiddleware, request_id_var


class RequestIDFilterTest(TestCase):
    """Test that RequestIDFilter injects request_id into log records."""

    def test_filter_injects_default_request_id(self):
        """Without a request, request_id should be '-'."""
        request_id_var.set("-")
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        f = RequestIDFilter()
        f.filter(record)
        self.assertEqual(record.request_id, "-")

    def test_filter_injects_current_request_id(self):
        """When set via ContextVar, request_id should appear on the record."""
        request_id_var.set("abc123")
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        f = RequestIDFilter()
        f.filter(record)
        self.assertEqual(record.request_id, "abc123")
        # Clean up
        request_id_var.set("-")


class RequestIDMiddlewareTest(TestCase):
    """Test that the RequestID middleware sets / propagates correlation IDs."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_generates_request_id_when_missing(self):
        """When no X-Request-ID header is sent, a UUID is generated."""
        response = self.client.get("/health/")
        self.assertIn("X-Request-ID", response)
        self.assertTrue(len(response["X-Request-ID"]) > 0)

    def test_preserves_incoming_request_id(self):
        """When X-Request-ID is supplied, it is echoed back."""
        response = self.client.get("/health/", HTTP_X_REQUEST_ID="my-trace-42")
        self.assertEqual(response["X-Request-ID"], "my-trace-42")

    def test_request_id_stored_on_request_object(self):
        """The middleware stores request_id on the request object."""
        called_with_rid = {}

        def _fake_view(request):
            from django.http import HttpResponse

            called_with_rid["rid"] = request.request_id
            return HttpResponse("ok")

        mw = RequestIDMiddleware(_fake_view)
        request = self.factory.get("/")
        request.META["HTTP_X_REQUEST_ID"] = "trace-999"
        mw(request)
        self.assertEqual(called_with_rid["rid"], "trace-999")


class JsonFormatterTest(TestCase):
    """Test the JSON log formatter output."""

    def _make_logger(self):
        """Create a logger that writes JSON to a StringIO buffer."""
        buf = StringIO()
        handler = logging.StreamHandler(buf)
        formatter = ERehnungJsonFormatter()
        handler.setFormatter(formatter)
        filt = RequestIDFilter()
        handler.addFilter(filt)
        logger = logging.getLogger("test.json_formatter")
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)
        return logger, buf

    def test_output_is_valid_json(self):
        """Each log line must be valid JSON."""
        logger, buf = self._make_logger()
        logger.info("hello world")
        line = buf.getvalue().strip()
        data = json.loads(line)
        self.assertIsInstance(data, dict)

    def test_json_contains_required_fields(self):
        """Log output must contain level, logger, service, request_id."""
        request_id_var.set("req-abc")
        logger, buf = self._make_logger()
        logger.info("test message")
        data = json.loads(buf.getvalue().strip())
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["logger"], "test.json_formatter")
        self.assertEqual(data["service"], "erechnung")
        self.assertEqual(data["request_id"], "req-abc")
        self.assertIn("message", data)
        request_id_var.set("-")

    def test_extra_fields_are_passed_through(self):
        """Extra kwargs (e.g. invoice_number) must appear in JSON."""
        logger, buf = self._make_logger()
        logger.info("generated", extra={"invoice_number": "INV-001"})
        data = json.loads(buf.getvalue().strip())
        self.assertEqual(data["invoice_number"], "INV-001")

    def test_warning_level(self):
        """WARNING level must be serialised correctly."""
        logger, buf = self._make_logger()
        logger.warning("bad input")
        data = json.loads(buf.getvalue().strip())
        self.assertEqual(data["level"], "WARNING")


class EndToEndLoggingTest(TestCase):
    """Integration tests: HTTP request → JSON log with request_id."""

    def test_request_produces_json_log_with_request_id(self):
        """An HTTP request should produce structured log output."""
        with patch("invoice_project.middleware.uuid") as mock_uuid:
            mock_uuid.uuid4.return_value = type("U", (), {"hex": "deadbeef1234"})()
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Request-ID"], "deadbeef1234")
