# ADR 023: pypdf-only Backend for PDF/A-3 Generation

## Status

Accepted (September 2025)

## Date

2025-09-15

## Context

The PDF/A-3 generation system (see ADR-003) initially used **PyPDF4** for embedding ZUGFeRD XML into existing PDF files. However, PyPDF4 has been **deprecated and unmaintained since 2020**, posing security and compatibility risks.

### Problems with PyPDF4

1. **Unmaintained**: No updates since 2020, no security patches
2. **Python 3.10+ Issues**: Compatibility problems with modern Python
3. **Deprecated Dependencies**: Uses outdated `pycryptodome` patterns
4. **Community Abandonment**: Fork of PyPDF2, itself replaced by pypdf
5. **Technical Debt**: Maintaining two PDF libraries (PyPDF4 + pypdf)

### Original Architecture

```python
# invoice_app/services/pdf/backends.py (before)
class PdfBackend:
    """Abstract base for PDF backends"""

class PypdfBackend(PdfBackend):
    """Primary: Uses pypdf for PDF operations"""

class PyPdf4Backend(PdfBackend):
    """Fallback: Uses PyPDF4 if pypdf fails"""

class InvoiceService:
    def generate_pdf_a3(self):
        try:
            backend = PypdfBackend()
            return backend.embed_xml(pdf_bytes, xml_string)
        except Exception:
            # Fallback to PyPDF4
            backend = PyPdf4Backend()
            return backend.embed_xml(pdf_bytes, xml_string)
```

**Problem:** Dual maintenance, security risk from deprecated library, unnecessary complexity.

## Decision

**We remove PyPDF4 entirely and use pypdf (v5.1.0+) as the single PDF library for all PDF operations.**

### Rationale

**1. pypdf is the Modern Successor:**

- **pypdf** (formerly PyPDF2) is the actively maintained fork
- Regular updates and security patches
- Full Python 3.11+ compatibility
- Growing community and ecosystem

**2. Feature Parity:**

- pypdf supports all PDF/A-3 operations
- Better documentation than PyPDF4
- More robust error handling

**3. Simplified Codebase:**

- Remove ~300 lines of PyPDF4 backend code
- Single code path, easier testing
- Fewer dependencies to manage

**4. Security:**

- Active CVE monitoring and patches
- Modern cryptography libraries
- Regular dependency updates

## Implementation

### Changes Made

**1. Removed PyPDF4 Backend:**

```python
# DELETED: invoice_app/services/pdf/backends.py
class PyPdf4Backend(PdfBackend):
    # ~150 lines removed
```

**2. Renamed PypdfBackend → DefaultBackend:**

```python
# invoice_app/services/pdf/backends.py (after)
class DefaultBackend(PdfBackend):
    """Uses pypdf for all PDF operations"""

    def embed_xml(self, pdf_bytes: bytes, xml_string: str) -> bytes:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        writer = pypdf.PdfWriter()

        # Copy all pages
        for page in reader.pages:
            writer.add_page(page)

        # Embed XML as attachment
        writer.add_attachment("factur-x.xml", xml_string.encode('utf-8'))

        # Write to bytes
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
```

**3. Removed Fallback Logic:**

```python
# invoice_app/services/invoice_service.py (after)
class InvoiceService:
    def generate_pdf_a3(self):
        backend = DefaultBackend()  # No fallback
        return backend.embed_xml(pdf_bytes, xml_string)
```

**4. Updated Dependencies:**

```python
# requirements.in (before)
pypdf>=5.1.0
PyPDF4>=1.27.0  # REMOVED

# requirements.in (after)
pypdf>=5.1.0
```

**5. Updated Tests:**

```python
# tests/test_pdf_generation.py
class TestPdfGeneration(TestCase):
    def test_embed_xml(self):
        backend = DefaultBackend()  # No PyPDF4 tests
        result = backend.embed_xml(pdf_bytes, xml_string)
        self.assertIsNotNone(result)
```

### Migration Strategy

**Phase 1: Verification (1 week)**

- Run all existing tests with pypdf-only
- Test PDF/A-3 generation manually
- Verify XML extraction from generated PDFs

**Phase 2: Removal (1 day)**

- Delete PyPDF4Backend class
- Remove PyPDF4 from requirements.txt
- Update docstrings and comments

**Phase 3: Cleanup (1 day)**

- Rename PypdfBackend → DefaultBackend
- Simplify error handling (no fallback)
- Update documentation

**Phase 4: Validation (1 week)**

- Run full test suite (263 tests)
- Generate test invoices
- Verify ZUGFeRD compliance

## Benefits

### 1. Simplified Architecture

**Before:**

```txt
InvoiceService
    → Try PypdfBackend
        → If error: Try PyPdf4Backend
            → If error: Raise exception
```

**After:**

```txt
InvoiceService
    → DefaultBackend
        → If error: Raise exception
```

### 2. Reduced Dependencies

```bash
# Before
pip install pypdf PyPDF4 pycryptodome

# After
pip install pypdf
```

### 3. Better Error Messages

**Before:**

```python
# Unclear which backend failed
Exception: PDF generation failed
```

**After:**

```python
# Clear pypdf error
pypdf.errors.PdfReadError: Invalid PDF header
```

### 4. Improved Performance

- No fallback logic overhead
- Single PDF library in memory
- Faster import times

## Consequences

### Positive

- ✅ **Security:** No deprecated library with security risks
- ✅ **Maintainability:** Single PDF library to maintain
- ✅ **Simplicity:** Less code, fewer edge cases
- ✅ **Modern:** Python 3.11+ compatible out of the box
- ✅ **Community:** Active development, regular updates
- ✅ **Testing:** Simpler test matrix (no dual backend tests)

### Negative

- ⚠️ **Risk:** If pypdf has a bug, no fallback available
  - **Mitigation:** pypdf is stable, used by millions
  - **Mitigation:** Comprehensive test coverage (263 tests)
  - **Mitigation:** Can revert commit if critical issue found

### Neutral

- **Learning Curve:** Team only needs to know one PDF library (simpler)
- **Documentation:** Clearer documentation without fallback complexity

## Validation Results

### Test Coverage

```bash
$ docker compose exec web python project_root/manage.py test
----------------------------------------------------------------------
Ran 263 tests in 45s

OK (skipped=3)
```

**All tests passing with pypdf-only backend** ✅

### PDF/A-3 Compliance

```python
# Test: Generate PDF/A-3 with embedded XML
invoice = Invoice.objects.create(...)
pdf_bytes = invoice_service.generate_pdf_a3(invoice)

# Verify: Can extract XML from PDF
extracted_xml = pypdf.PdfReader(io.BytesIO(pdf_bytes)).attachments["factur-x.xml"]
assert extracted_xml.decode('utf-8') == expected_xml
```

**PDF/A-3 generation working correctly** ✅

### ZUGFeRD Validation

```bash
# Validate generated PDF/A-3 against ZUGFeRD schema
$ python scripts/validate_zugferd.py generated_invoice.pdf
✓ PDF/A-3 structure valid
✓ XML attachment present
✓ ZUGFeRD 2.3 schema validation passed
```

**ZUGFeRD compliance maintained** ✅

## Alternatives Considered

### 1. Keep PyPDF4 as Optional Fallback

**Rejected:**

- Still maintains technical debt
- Security risk remains
- Complexity not justified by benefits

### 2. Migrate to Different PDF Library (e.g., reportlab)

**Rejected:**

- reportlab is for PDF generation, not manipulation
- pypdf actively maintained and sufficient
- Unnecessary migration effort

### 3. Use External PDF Tools (e.g., pdftk)

**Rejected:**

- External dependencies increase complexity
- Requires system-level installation
- Harder to test in containers

## Related Decisions

- ADR-003: Use Python-based Tools for PDF/A Generation (parent decision)
- ADR-004: Docker-based Deployment (affects dependency management)

## Rollback Plan

If critical pypdf bug discovered:

1. **Immediate:**

   ```bash
   git revert <commit-hash>  # Restore PyPDF4 backend
   pip install PyPDF4        # Restore dependency
   ```

2. **Short-term:**
   - Document pypdf issue
   - Report upstream to pypdf maintainers
   - Test PyPDF4 fallback still works

3. **Long-term:**
   - Wait for pypdf fix or find workaround
   - If no fix, keep PyPDF4 with security monitoring

**Likelihood:** Very low (pypdf is stable, used by millions)

## Timeline

- **2025-09-15:** Decision made, testing started
- **2025-09-22:** All tests passing, PyPDF4 removed
- **2025-09-25:** Documentation updated, change deployed
- **2025-12-02:** Operating successfully for 2+ months ✅

## References

- pypdf Documentation: https://pypdf.readthedocs.io/
- pypdf GitHub: https://github.com/py-pdf/pypdf
- PyPDF4 (deprecated): https://github.com/claird/PyPDF4
- PDF/A-3 Standard: ISO 19005-3:2012
