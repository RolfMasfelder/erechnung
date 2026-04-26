"""Custom middleware for eRechnung application."""

import contextvars
import uuid


# ContextVar for request correlation ID — accessible from any thread / async context.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIDMiddleware:
    """
    Assign a unique correlation ID to every HTTP request.

    Priority:
      1. Incoming ``X-Request-ID`` header (forwarded by API gateway / load-balancer)
      2. Freshly generated UUID-4

    The ID is stored in:
      • ``request.request_id``  — for use inside views / services
      • ``request_id_var``      — ContextVar for the JSON log filter
      • Response header ``X-Request-ID`` — returned to the caller
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.META.get("HTTP_X_REQUEST_ID") or uuid.uuid4().hex
        request.request_id = rid
        request_id_var.set(rid)

        response = self.get_response(request)
        response["X-Request-ID"] = rid
        return response


class HealthCheckSSLExemptMiddleware:
    """
    Middleware to exempt /health/ endpoint from HTTPS redirect.

    This allows Kubernetes health checks to work over HTTP
    while still enforcing HTTPS for all other endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exempt health check endpoint from SSL redirect
        if request.path == "/health/":
            request._dont_enforce_csrf_checks = True
            # Mark request as already using HTTPS to skip redirect
            request.META["HTTP_X_FORWARDED_PROTO"] = "https"

        response = self.get_response(request)
        return response
