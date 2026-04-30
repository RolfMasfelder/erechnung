# Runbook: OverdueInvoicesHigh

**Alert:** `OverdueInvoicesHigh`  
**Severity:** warning  
**Category:** Business

## Summary

The number of overdue invoices (unpaid, past due date) has exceeded 10.

## Impact

- Potential cash flow issue
- Manual follow-up required with customers
- No system downtime — this is a business metric alert

## Diagnosis

```bash
# List overdue invoices
docker compose exec web python project_root/manage.py shell -c "
from invoice_app.models import Invoice
from django.utils import timezone
overdue = Invoice.objects.filter(
    status='SENT',
    due_date__lt=timezone.now().date()
).order_by('due_date')
print(f'Total overdue: {overdue.count()}')
for inv in overdue[:10]:
    print(f'  {inv.invoice_number} - {inv.business_partner} - due {inv.due_date} - {inv.total_amount}')
"
```

## Resolution

1. Export overdue invoice list from the admin interface
2. Send payment reminders via the standard business process
3. If the number is unusually high, check for:
   - System issue preventing status updates
   - Bulk import that set wrong due dates

## Notes

This alert does not indicate a system problem. Acknowledge and handle via normal business process.
