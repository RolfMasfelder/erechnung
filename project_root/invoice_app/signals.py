"""
Django signals configuration for automatic audit logging.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_migrate, post_save, pre_delete
from django.dispatch import receiver

from invoice_app.middleware.audit import ModelChangeTracker
from invoice_app.models import AuditLog, BusinessPartner, Company, Invoice, InvoiceAttachment, InvoiceLine, Product


User = get_user_model()


# Model change tracking
@receiver(post_save, sender=Company)
@receiver(post_save, sender=BusinessPartner)
@receiver(post_save, sender=Product)
@receiver(post_save, sender=Invoice)
@receiver(post_save, sender=InvoiceLine)
@receiver(post_save, sender=InvoiceAttachment)
def track_model_changes(sender, instance, created, **kwargs):
    """Track create and update operations for important models."""
    if created:
        ModelChangeTracker.log_model_create(sender, instance, created, **kwargs)
    else:
        ModelChangeTracker.log_model_update(sender, instance, **kwargs)


@receiver(pre_delete, sender=Company)
@receiver(pre_delete, sender=BusinessPartner)
@receiver(pre_delete, sender=Product)
@receiver(pre_delete, sender=Invoice)
@receiver(pre_delete, sender=InvoiceLine)
@receiver(pre_delete, sender=InvoiceAttachment)
def track_model_deletions(sender, instance, **kwargs):
    """Track delete operations for important models."""
    ModelChangeTracker.log_model_delete(sender, instance, **kwargs)


# Authentication events
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user logins."""
    AuditLog.log_action(
        action=AuditLog.ActionType.LOGIN,
        user=user,
        request=request,
        description=f"User {user.username} logged in successfully",
        severity=AuditLog.Severity.LOW,
        is_security_event=True,
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logouts."""
    AuditLog.log_action(
        action=AuditLog.ActionType.LOGOUT,
        user=user,
        request=request,
        description=f"User {user.username} logged out",
        severity=AuditLog.Severity.LOW,
    )


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Log failed login attempts."""
    username = credentials.get("username", "unknown")
    AuditLog.log_action(
        action=AuditLog.ActionType.LOGIN_FAILED,
        request=request,
        description=f"Failed login attempt for username: {username}",
        details={"attempted_username": username},
        severity=AuditLog.Severity.HIGH,
        is_security_event=True,
    )


# System events
@receiver(post_migrate)
def log_migration(sender, **kwargs):
    """Log database migrations."""
    if sender.name == "invoice_app":
        try:
            AuditLog.log_action(
                action=AuditLog.ActionType.CONFIG_CHANGE,
                description=f"Database migration completed for {sender.name}",
                details={"app_name": sender.name},
                severity=AuditLog.Severity.MEDIUM,
                is_compliance_relevant=True,
            )
        except Exception:
            # Might fail during initial migration when AuditLog table doesn't exist yet
            pass
