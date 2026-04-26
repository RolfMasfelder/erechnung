"""Health check views for CI/CD Pipeline and Monitoring."""

import logging
import os

from django.conf import settings
from django.core.cache import cache
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated


# Health check logger
health_logger = logging.getLogger(__name__)

# Constants
DB_PING_QUERY = "SELECT 1"


class HealthCheckError(Exception):
    """Custom exception for health check failures."""

    pass


@require_http_methods(["GET"])
def health_check(request) -> JsonResponse:
    """
    Simple health check endpoint for load balancers and monitoring.
    Returns HTTP 200 if the service is healthy.

    SECURITY: This endpoint is public but returns minimal information.
    No service name, version, or internal details are exposed.
    """
    try:
        # Quick database ping to verify basic connectivity
        with connection.cursor() as cursor:
            cursor.execute(DB_PING_QUERY)

        return JsonResponse({"status": "ok"}, status=200)
    except OperationalError:
        return JsonResponse({"status": "error"}, status=503)


@extend_schema(
    description="Detailed health check including database and cache connectivity",
    responses={200: {"type": "object", "properties": {"status": {"type": "string"}, "checks": {"type": "object"}}}},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def health_detailed(request) -> JsonResponse:
    """
    Detailed health check including database and cache connectivity.
    Used for deep health monitoring and CI/CD pipeline verification.

    SECURITY: Requires JWT authentication to prevent information disclosure.
    """
    health_data = {
        "status": "healthy",
        "timestamp": None,
        "checks": {},
    }

    overall_healthy = True

    try:
        from django.utils import timezone

        health_data["timestamp"] = timezone.now().isoformat()
    except ImportError:
        pass

    # Database connectivity check
    try:
        with connection.cursor() as cursor:
            cursor.execute(DB_PING_QUERY)
            cursor.fetchone()
        health_data["checks"]["database"] = {"status": "healthy"}
    except OperationalError as e:
        health_logger.error(f"Database health check failed: {e}")
        health_data["checks"]["database"] = {"status": "unhealthy"}
        overall_healthy = False

    # Cache connectivity check (Redis)
    try:
        cache.set("health_check", "test", timeout=60)
        cached_value = cache.get("health_check")
        if cached_value == "test":
            health_data["checks"]["cache"] = {"status": "healthy"}
        else:
            raise HealthCheckError("Cache write/read mismatch")
    except (HealthCheckError, ConnectionError, OSError) as e:
        health_logger.warning(f"Cache health check failed: {e}")
        health_data["checks"]["cache"] = {"status": "unhealthy"}
        # Cache failure is not critical for basic operation

    # File system check (media directory)
    try:
        media_root = getattr(settings, "MEDIA_ROOT", "/tmp")
        if os.path.exists(media_root) and os.access(media_root, os.W_OK):
            health_data["checks"]["filesystem"] = {"status": "healthy"}
        else:
            raise HealthCheckError("Media directory not writable")
    except (HealthCheckError, OSError) as e:
        health_logger.error(f"Filesystem health check failed: {e}")
        health_data["checks"]["filesystem"] = {"status": "unhealthy"}
        overall_healthy = False

    # Update overall status
    health_data["status"] = "healthy" if overall_healthy else "unhealthy"

    # Return appropriate HTTP status code
    status_code = 200 if overall_healthy else 503

    return JsonResponse(health_data, status=status_code)


@extend_schema(
    description="Readiness check for Kubernetes/Docker deployments",
    responses={200: {"type": "object", "properties": {"status": {"type": "string"}, "checks": {"type": "object"}}}},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_check(request) -> JsonResponse:
    """
    Readiness check for Kubernetes/Docker deployments.
    Verifies that the application is ready to serve traffic.

    SECURITY: Public endpoint for health checks. Returns minimal status information.
    """
    readiness_data = {"status": "ready", "checks": {}}

    overall_ready = True

    # Check if migrations are up to date
    try:
        from django.db import connections
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connections["default"])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        if plan:
            readiness_data["checks"]["migrations"] = {"status": "not_ready"}
            overall_ready = False
        else:
            readiness_data["checks"]["migrations"] = {"status": "ready"}
    except (OperationalError, ImportError) as e:
        health_logger.error(f"Migration check failed: {e}")
        readiness_data["checks"]["migrations"] = {"status": "not_ready"}
        overall_ready = False

    # Check if database is accessible (without exposing counts)
    try:
        with connection.cursor() as cursor:
            cursor.execute(DB_PING_QUERY)
        readiness_data["checks"]["database"] = {"status": "ready"}
    except OperationalError as e:
        health_logger.error(f"Database access check failed: {e}")
        readiness_data["checks"]["database"] = {"status": "not_ready"}
        overall_ready = False

    # Update overall status
    readiness_data["status"] = "ready" if overall_ready else "not_ready"

    # Return appropriate HTTP status code
    status_code = 200 if overall_ready else 503

    return JsonResponse(readiness_data, status=status_code)
