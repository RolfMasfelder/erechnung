# Runbook: PDFGenerationSlow

**Alert:** `PDFGenerationSlow`  
**Severity:** warning  
**Category:** Performance

## Summary

The p95 PDF generation time has exceeded 10 seconds in the last 15 minutes.

## Impact

- Users experience long waits for PDF downloads
- Celery task queue may grow
- Risk of timeouts for synchronous PDF requests

## Diagnosis

```bash
# Check PDF generation timing from Prometheus
# Query: histogram_quantile(0.95, rate(erechnung_pdf_generation_duration_seconds_bucket[15m]))

# Check invoice complexity (large invoices with many lines are slower)
docker compose exec web python project_root/manage.py shell -c "
from invoice_app.models import Invoice, InvoiceLine
large = Invoice.objects.annotate(
    line_count=models.Count('lines')
).filter(line_count__gt=50).count()
print(f'Invoices with >50 lines: {large}')
"

# Check system resources
docker stats --no-stream
```

## Common Causes and Fixes

1. **Large invoices:** Invoices with many line items take longer to render
2. **External font loading:** Ensure all fonts are local, not fetched from network
3. **Resource contention:** Multiple concurrent PDF generations — check Celery concurrency
4. **WeasyPrint version:** Check for known performance regressions

## Resolution

1. If isolated to large invoices: acceptable, no action needed
2. If all invoices slow:
   - Check CPU utilization of Celery workers
   - Consider scaling Celery worker replicas
   - Check for blocking I/O in PDF generation pipeline
3. Ensure PDF generation runs asynchronously via Celery (not synchronously in request cycle)
