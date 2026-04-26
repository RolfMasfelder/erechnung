from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from invoice_app.models import AuditLog, Product


User = get_user_model()


class Command(BaseCommand):
    help = "Test audit logging functionality"

    def handle(self, *args, **options):
        self.stdout.write("Testing audit logging functionality...")

        # Test manual audit log creation
        AuditLog.log_action(
            action=AuditLog.ActionType.SECURITY_EVENT,
            description="Test security event for audit logging demonstration",
            details={"test": True, "component": "audit_system"},
            severity=AuditLog.Severity.MEDIUM,
        )
        self.stdout.write(self.style.SUCCESS("✓ Created test security event"))

        # Test model change logging (if we have a product)
        products = Product.objects.filter(is_active=True)[:1]
        if products:
            product = products[0]
            old_price = product.base_price
            product.base_price = old_price + Decimal("10.00")
            product.save()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Updated product price: {product.name} (${old_price} -> ${product.base_price})")
            )

        # Show recent audit logs
        recent_logs = AuditLog.objects.all()[:5]
        self.stdout.write(f"\nRecent audit log entries ({recent_logs.count()}):")
        for log in recent_logs:
            self.stdout.write(f"  {log.timestamp} - {log.get_action_display()} - {log.description}")

        # Show statistics
        total_logs = AuditLog.objects.count()
        security_logs = AuditLog.objects.filter(is_security_event=True).count()
        compliance_logs = AuditLog.objects.filter(is_compliance_relevant=True).count()

        self.stdout.write("\nAudit Log Statistics:")
        self.stdout.write(f"  Total entries: {total_logs}")
        self.stdout.write(f"  Security events: {security_logs}")
        self.stdout.write(f"  Compliance events: {compliance_logs}")

        self.stdout.write(self.style.SUCCESS("\n✓ Audit logging test completed successfully!"))
