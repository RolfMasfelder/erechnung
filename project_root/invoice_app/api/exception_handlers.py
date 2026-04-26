"""
Globaler DRF Exception Handler — eRechnung

Fängt alle DRF-Exceptions (inkl. unserer Custom-Exceptions) ab und liefert
ein einheitliches JSON-Format zurück:

    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Benutzerfreundliche Fehlermeldung.",
            "details": { ... }        # optional — nur bei Validierungsfehlern
        }
    }

Registrierung in settings.py:
    REST_FRAMEWORK = {
        "EXCEPTION_HANDLER": "invoice_app.api.exception_handlers.global_exception_handler",
    }
"""

import logging

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler


logger = logging.getLogger(__name__)


def _build_error_response(
    code: str, message: str, details: dict | list | None = None, http_status: int = 500
) -> Response:
    """Baut eine einheitliche Fehler-Response."""
    body: dict = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return Response(body, status=http_status)


def _flatten_validation_errors(detail) -> dict | list | str:
    """
    Wandelt DRF-ValidationError-Details in ein lesbares Format um.

    DRF liefert verschiedene Strukturen:
      - dict  → {"field": ["error1", "error2"]}
      - list  → ["error1"]
      - str   → "error"
    """
    if isinstance(detail, dict):
        return {
            field: [str(e) for e in (errors if isinstance(errors, list) else [errors])]
            for field, errors in detail.items()
        }
    if isinstance(detail, list):
        return [str(e) for e in detail]
    return str(detail)


def global_exception_handler(exc, context):
    """
    Globaler Exception Handler für alle DRF-Views.

    Behandelt:
    1. Unsere Custom APIExceptions (exceptions.py) → code aus default_code
    2. DRF-Standard-Exceptions (ValidationError, NotFound, etc.)
    3. Django-Exceptions (Http404, PermissionDenied, ValidationError)
    4. Unerwartete Exceptions → 500 ohne interne Details
    """
    # Erst DRF-Default aufrufen (behandelt bekannte Exceptions,
    # setzt Content-Negotiation etc.)
    response = drf_default_handler(exc, context)

    # ── Custom APIException mit default_code ────────────────────────────
    if isinstance(exc, APIException) and hasattr(exc, "default_code") and isinstance(exc.default_code, str):
        code = exc.default_code
        # Bei ValidationError: Details mit Feldinformationen mitgeben
        if hasattr(exc, "detail"):
            details = _flatten_validation_errors(exc.detail) if code == "invalid" else None
            message = str(exc.detail) if not isinstance(exc.detail, (dict, list)) else exc.default_detail
        else:
            details = None
            message = exc.default_detail

        # Für unsere Custom-Exceptions: Code aus default_code verwenden
        if code not in (
            "invalid",
            "parse_error",
            "not_found",
            "permission_denied",
            "not_authenticated",
            "authentication_failed",
            "method_not_allowed",
            "not_acceptable",
            "unsupported_media_type",
            "throttled",
        ):
            # Custom Exception → message direkt aus detail
            message = str(exc.detail) if isinstance(exc.detail, str) else exc.default_detail
            details_val = None
            if isinstance(exc.detail, dict):
                details_val = exc.detail
            elif isinstance(exc.detail, list):
                details_val = exc.detail
            return _build_error_response(
                code=code,
                message=message,
                details=details_val,
                http_status=exc.status_code,
            )

    # ── DRF-Standard ValidationError ────────────────────────────────────
    if response is not None and response.status_code == 400:
        from rest_framework.exceptions import ValidationError

        if isinstance(exc, ValidationError):
            details = _flatten_validation_errors(exc.detail)
            # Erste Fehlermeldung als message verwenden
            if isinstance(details, dict):
                first_errors = next(iter(details.values()), ["Validierungsfehler"])
                message = first_errors[0] if first_errors else "Validierungsfehler"
            elif isinstance(details, list):
                message = details[0] if details else "Validierungsfehler"
            else:
                message = str(details)
            return _build_error_response(
                code="VALIDATION_ERROR",
                message=message,
                details=details,
                http_status=400,
            )

    # ── DRF-Standard Responses (NotFound, MethodNotAllowed, etc.) ───────
    if response is not None:
        code_map = {
            401: "NOT_AUTHENTICATED",
            403: "PERMISSION_DENIED",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            406: "NOT_ACCEPTABLE",
            415: "UNSUPPORTED_MEDIA_TYPE",
            429: "THROTTLED",
        }
        code = code_map.get(response.status_code, f"HTTP_{response.status_code}")
        message = str(exc.detail) if hasattr(exc, "detail") and isinstance(exc.detail, str) else str(exc)
        return _build_error_response(
            code=code,
            message=message,
            http_status=response.status_code,
        )

    # ── Django-Exceptions (nicht von DRF behandelt) ─────────────────────
    if isinstance(exc, Http404):
        return _build_error_response("NOT_FOUND", "Ressource nicht gefunden.", http_status=404)
    if isinstance(exc, PermissionDenied):
        return _build_error_response("PERMISSION_DENIED", "Keine Berechtigung.", http_status=403)
    if isinstance(exc, DjangoValidationError):
        return _build_error_response(
            "VALIDATION_ERROR",
            str(exc.message) if hasattr(exc, "message") else str(exc),
            http_status=400,
        )

    # ── Unerwartete Exceptions → 500 OHNE interne Details ──────────────
    view_name = ""
    if context and "view" in context:
        view_name = context["view"].__class__.__name__
    logger.error(
        "Unhandled exception in %s: %s: %s",
        view_name,
        type(exc).__name__,
        str(exc),
        exc_info=True,
    )
    return _build_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="Ein interner Serverfehler ist aufgetreten.",
        http_status=500,
    )
