import logging

from django.apps import AppConfig


logger = logging.getLogger("invoice_app")


class InvoiceAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "invoice_app"

    def ready(self):
        """Import signal handlers when the app is ready."""
        # Connect Prometheus monitoring signals
        import invoice_app.monitoring.signals  # noqa
        import invoice_app.signals  # noqa

        invoice_app.monitoring.signals.connect_auth_signals()

        # Deferred migration check — runs once on first request (avoids Django 5.2 DB-in-ready warning)
        from django.core.signals import request_started

        request_started.connect(_check_pending_migrations_once)


def _check_pending_migrations_once(sender, **kwargs):
    """Check for unapplied migrations on first request, then disconnect."""
    from django.core.signals import request_started

    request_started.disconnect(_check_pending_migrations_once)

    try:
        from django.db import connections
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connections["default"])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            pending = [f"{m.app_label}.{m.name}" for m, _backwards in plan]
            logger.warning(
                "Unapplied migrations detected (%d): %s — run 'python manage.py migrate' before serving traffic.",
                len(pending),
                ", ".join(pending[:5]) + ("..." if len(pending) > 5 else ""),
            )
        else:
            logger.info("Database schema is up to date (all migrations applied).")
    except Exception:
        logger.debug("Migration check skipped (database not yet available).")
