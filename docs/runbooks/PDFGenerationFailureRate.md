# Runbook: PDFGenerationFailureRate

**Alert:** `PDFGenerationFailureRate`  
**Severity:** warning  
**Category:** Reliability

## Summary

More than 10% of PDF generation attempts have failed in the last 15 minutes.

## Impact

- Users cannot download invoice PDFs
- ZUGFeRD/Factur-X invoice delivery may be blocked
- Celery task queue may be backing up

## Diagnosis

```bash
# Check WeasyPrint errors in application logs
docker compose logs web 2>&1 | grep -i "weasyprint\|pdf\|generation" | tail -20

# Check Celery task failures
docker compose exec web python project_root/manage.py shell -c "
from django_celery_results.models import TaskResult
failures = TaskResult.objects.filter(
    task_name__icontains='pdf',
    status='FAILURE'
).order_by('-date_done')[:5]
for t in failures:
    print(t.task_name, t.result[:200])
"

# Check if WeasyPrint fonts are available
docker compose exec web python -c "
import weasyprint
html = weasyprint.HTML(string='<p>Test</p>')
doc = html.render()
print('WeasyPrint OK, pages:', len(doc.pages))
"

# Check disk space (PDF temp files)
df -h /tmp
```

## Common Causes and Fixes

1. **Missing font:** WeasyPrint requires fonts to be installed in the container
2. **Template error:** Check invoice_pdf.html for syntax errors
3. **Memory pressure:** PDF generation is memory-intensive — check pod limits
4. **Missing CSS/images:** Ensure static files are accessible during PDF rendering
5. **Celery worker down:** See [HighCeleryTaskFailureRate runbook](./HighCeleryTaskFailureRate.md)

## Resolution

1. Check logs for specific error message
2. Test PDF generation manually:
   ```bash
   docker compose exec web python project_root/manage.py shell -c "
   from invoice_app.services.pdf_service import generate_invoice_pdf
   from invoice_app.models import Invoice
   inv = Invoice.objects.first()
   pdf = generate_invoice_pdf(inv)
   print(f'PDF size: {len(pdf)} bytes')
   "
   ```
3. Restart Celery workers if needed:
   ```bash
   docker compose restart celery
   ```
