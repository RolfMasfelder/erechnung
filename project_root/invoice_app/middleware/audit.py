"""
Audit logging middleware for automatic tracking of requests and model changes.
"""

import logging
import time

from django.db import DatabaseError
from django.utils.deprecation import MiddlewareMixin
from invoice_app.models import AuditLog


logger = logging.getLogger(__name__)


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to automatically log HTTP requests and responses.
    """

    def process_request(self, request):
        """Store request start time for performance tracking."""
        request._audit_start_time = time.time()

    def process_response(self, request, response):
        """Log the request/response cycle."""
        # Skip logging for static files and admin media
        if (
            request.path.startswith("/static/")
            or request.path.startswith("/media/")
            or request.path.startswith("/admin/jsi18n/")
        ):
            return response

        # Calculate request duration
        duration = None
        if hasattr(request, "_audit_start_time"):
            duration = time.time() - request._audit_start_time

        # Determine action type based on request method
        action_map = {
            "GET": AuditLog.ActionType.READ,
            "POST": AuditLog.ActionType.CREATE,
            "PUT": AuditLog.ActionType.UPDATE,
            "PATCH": AuditLog.ActionType.UPDATE,
            "DELETE": AuditLog.ActionType.DELETE,
        }
        action = action_map.get(request.method, AuditLog.ActionType.READ)

        # Determine severity based on response status
        severity = AuditLog.Severity.LOW
        if response.status_code >= 500:
            severity = AuditLog.Severity.CRITICAL
        elif response.status_code >= 400:
            severity = AuditLog.Severity.MEDIUM

        # Create description
        description = f"{request.method} {request.path}"
        if response.status_code >= 400:
            description += f" - Error {response.status_code}"

        # Prepare details
        details = {
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "content_type": response.get("Content-Type", ""),
        }

        if duration:
            details["duration_ms"] = round(duration * 1000, 2)

        # Log the request
        try:
            AuditLog.log_action(
                action=action,
                user=request.user if hasattr(request, "user") and request.user.is_authenticated else None,
                request=request,
                description=description,
                details=details,
                severity=severity,
                response_status=response.status_code,
            )
        except DatabaseError as e:
            # Never let audit logging break the application, but log the failure
            logger.warning(
                "Audit logging failed for %s %s: %s",
                request.method,
                request.path,
                str(e),
                exc_info=True,
            )

        return response


class ModelChangeTracker:
    """
    Utility class to track model changes for audit logging.
    """

    @staticmethod
    def get_model_fields(instance):
        """Get all field values from a model instance."""
        fields = {}
        for field in instance._meta.fields:
            try:
                value = getattr(instance, field.name)
                # Convert complex types to JSON-serializable format
                if hasattr(value, "isoformat"):  # DateTime objects
                    value = value.isoformat()
                elif hasattr(value, "__dict__"):  # Model instances
                    value = str(value)
                fields[field.name] = value
            except (AttributeError, TypeError, ValueError) as e:
                fields[field.name] = "<error getting value>"
                logger.debug(
                    "Error getting field value for %s.%s: %s",
                    instance.__class__.__name__,
                    field.name,
                    str(e),
                )
        return fields

    @staticmethod
    def log_model_create(sender, instance, created, **kwargs):
        """Signal handler for post_save when created=True."""
        if created:
            try:
                new_values = ModelChangeTracker.get_model_fields(instance)
                AuditLog.log_model_change(action=AuditLog.ActionType.CREATE, instance=instance, new_values=new_values)
            except DatabaseError as e:
                logger.warning(
                    "Audit log_model_create failed for %s (pk=%s): %s",
                    sender.__name__,
                    getattr(instance, "pk", "unknown"),
                    str(e),
                    exc_info=True,
                )

    @staticmethod
    def log_model_update(sender, instance, **kwargs):
        """Signal handler for post_save when created=False."""
        try:
            # Get the old instance from database
            old_instance = sender.objects.get(pk=instance.pk)
            old_values = ModelChangeTracker.get_model_fields(old_instance)
            new_values = ModelChangeTracker.get_model_fields(instance)

            # Only log if there are actual changes
            if old_values != new_values:
                AuditLog.log_model_change(
                    action=AuditLog.ActionType.UPDATE, instance=instance, old_values=old_values, new_values=new_values
                )
        except sender.DoesNotExist:
            # This is actually a create operation
            ModelChangeTracker.log_model_create(sender, instance, True, **kwargs)
        except DatabaseError as e:
            logger.warning(
                "Audit log_model_update failed for %s (pk=%s): %s",
                sender.__name__,
                getattr(instance, "pk", "unknown"),
                str(e),
                exc_info=True,
            )

    @staticmethod
    def log_model_delete(sender, instance, **kwargs):
        """Signal handler for pre_delete."""
        try:
            old_values = ModelChangeTracker.get_model_fields(instance)
            AuditLog.log_model_change(action=AuditLog.ActionType.DELETE, instance=instance, old_values=old_values)
        except DatabaseError as e:
            logger.warning(
                "Audit log_model_delete failed for %s (pk=%s): %s",
                sender.__name__,
                getattr(instance, "pk", "unknown"),
                str(e),
                exc_info=True,
            )
