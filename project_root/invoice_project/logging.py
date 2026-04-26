"""
Structured JSON logging for eRechnung.

Provides:
  • ``ERehnungJsonFormatter``  — JSON log formatter with request-ID, service
    name and optional extras (user, invoice_number, …).
  • ``RequestIDFilter``        — Log filter that injects the current
    ``request_id`` from the ContextVar into every LogRecord.
"""

import logging

from pythonjsonlogger.json import JsonFormatter

from invoice_project.middleware import request_id_var


# ---------------------------------------------------------------------------
# Log filter — injects request_id into every LogRecord
# ---------------------------------------------------------------------------


class RequestIDFilter(logging.Filter):
    """Inject ``request_id`` from the ContextVar into every log record."""

    def filter(self, record):
        record.request_id = request_id_var.get("-")
        return True


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


class ERehnungJsonFormatter(JsonFormatter):
    """
    Structured JSON formatter for eRechnung log output.

    Emitted fields (guaranteed):
        timestamp, level, logger, message, request_id, service

    Additional fields are passed through unchanged (e.g. ``user``,
    ``invoice_number``, ``duration_ms``).
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("timestamp", True)
        super().__init__(*args, **kwargs)

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        # Rename standard fields to our canonical JSON schema
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = "erechnung"
        # request_id comes from RequestIDFilter → LogRecord attribute
        log_record.setdefault("request_id", getattr(record, "request_id", "-"))
