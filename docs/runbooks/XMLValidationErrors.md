# Runbook: XMLValidationErrors

**Alert:** `XMLValidationErrors`  
**Severity:** warning  
**Category:** Compliance

## Summary

XML validation errors (ZUGFeRD/Factur-X EN 16931) have been detected. More than 5 validation errors occurred in the last 15 minutes.

## Impact

- Generated invoices may not be EN 16931 compliant
- Recipients may reject invoices as invalid
- ZUGFeRD conformance at risk

## Diagnosis

```bash
# Check XML validation errors in application logs
docker compose logs web 2>&1 | grep -i "xml.*valid\|zugferd\|facturx\|schematron" | tail -20

# Check recent invoice XML generation errors
docker compose exec web python project_root/manage.py shell -c "
from invoice_app.models import Invoice
# Check invoices with XML validation failures
import logging
logging.basicConfig(level=logging.DEBUG)
"

# Validate a specific invoice XML manually
docker compose exec web python project_root/manage.py shell -c "
from invoice_app.services.xml_service import generate_invoice_xml, validate_xml
from invoice_app.models import Invoice
inv = Invoice.objects.latest('created_at')
xml = generate_invoice_xml(inv)
errors = validate_xml(xml)
print(f'Validation errors: {errors}')
"
```

## Common Causes and Fixes

1. **Required field missing:** Check if mandatory EN 16931 fields (BuyerReference, etc.) are populated
2. **Invalid date format:** Dates must be in YYYYMMDD format for ZUGFeRD
3. **Tax rate mismatch:** Verify tax rates match ZUGFeRD code list
4. **Recent code change:** Check git log for recent changes to XML generation service

## Resolution

1. Identify which invoice(s) are failing
2. Check the specific validation error message
3. Fix the data issue or code bug
4. Re-generate XML for affected invoices

## References

- EN 16931 Schematron: `invoice_app/services/validation/`
- ZUGFeRD conformance guide: `docs/ZUGFERD_CONFORMANCE.md`
