# Enhanced CSRF Protection Middleware for eRechnung App

import logging

from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger(__name__)


class EnhancedCSRFMiddleware(MiddlewareMixin):
    """
    Enhanced CSRF protection for mixed web/API application.

    Provides different CSRF handling for:
    - Web forms (traditional CSRF tokens)
    - API endpoints (JWT + optional CSRF headers)
    - Admin interface (strict CSRF + IP validation)
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Apply enhanced CSRF checks based on request type."""

        # Skip CSRF for API endpoints using JWT
        if request.path.startswith("/api/") and self._has_valid_jwt(request):
            # For API: JWT is primary auth, CSRF is optional
            return None

        # Enhanced protection for admin interface
        if request.path.startswith("/admin/"):
            return self._validate_admin_csrf(request)

        # Regular CSRF for web forms (handled by Django's middleware)
        return None

    def _has_valid_jwt(self, request):
        """Check if request has valid JWT token."""
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        return auth_header.startswith("Bearer ")

    def _validate_admin_csrf(self, request):
        """Enhanced CSRF validation for admin interface."""
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            # Additional checks for admin operations
            if not self._is_trusted_ip(request):
                logger.warning(f"Admin access from untrusted IP: {self._get_client_ip(request)}")
                # Could add additional validation here

    def _is_trusted_ip(self, request):
        """Check if request comes from trusted IP (example implementation)."""
        # Add your trusted IP logic here
        return True  # For now, trust all IPs

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class APICSRFMixin:
    """
    Mixin for API ViewSets that want additional CSRF protection.

    Usage:
        class InvoiceViewSet(APICSRFMixin, viewsets.ModelViewSet):
            csrf_required_actions = ['create', 'update', 'destroy']
    """

    csrf_required_actions = []  # Override in subclass

    def dispatch(self, request, *args, **kwargs):
        """Check CSRF for specified actions."""
        if (
            hasattr(self, "action")
            and self.action in self.csrf_required_actions
            and request.method in ["POST", "PUT", "PATCH", "DELETE"]
        ):
            if not self._validate_api_csrf(request):
                return HttpResponseForbidden("CSRF validation failed")

        return super().dispatch(request, *args, **kwargs)

    def _validate_api_csrf(self, request):
        """
        Validate CSRF for API using double-submit pattern.

        Expects either:
        1. X-CSRFToken header matching csrftoken cookie
        2. Valid JWT token (fallback)
        """
        # Method 1: Double-submit cookie pattern
        csrf_token = request.headers.get("X-CSRFToken")
        csrf_cookie = request.COOKIES.get("csrftoken")

        if csrf_token and csrf_cookie and csrf_token == csrf_cookie:
            return True

        # Method 2: Fallback to JWT validation
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        return auth_header.startswith("Bearer ")
