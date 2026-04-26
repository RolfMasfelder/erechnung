# Import/Export Feature Implementation Plan

**Feature**: JSON/CSV Import/Export für Rechnungen, Kunden, Produkte
**Branch**: `feature/import-export`
**Estimated Total Time**: 2-3 Wochen
**Priority**: Medium-High (Functionality Focus)

## Technology Stack Evaluation

### Recommended Approach: Hybrid Solution

**For Export:**
- Django REST Framework Serializers (bereits vorhanden) → JSON Export
- Python `csv` module (Standard Library) → CSV Export
- Custom Views/Actions für Admin + API

**For Import:**
- Django REST Framework Serializers → JSON Import & Validation
- Python `csv` + Custom Parser → CSV Import
- Transaction-based processing (atomic imports)

**Alternative Package Considered:**
- `django-import-export` (https://github.com/django-import-export/django-import-export)
  - ✅ Pro: Battle-tested, Admin-Integration, Multiple formats
  - ❌ Con: Excel-fokussiert, zusätzliche Dependency, Learning curve
  - **Decision**: NOT using - we build custom solution with existing tools

### Why Custom Solution?

1. **Leverage existing serializers** - DRF serializers already in place
2. **Full control** - Custom validation, business logic integration
3. **Minimal dependencies** - Only standard library + existing DRF
4. **Learning value** - Better understanding of data flow
5. **Flexibility** - Easy to extend for specific requirements

## Implementation Phases

---

## Phase 1: Export Foundation (Week 1, Days 1-3)

### 1.1 Core Export Service

**Files to create:**
- `project_root/invoice_app/services/export_service.py`

**Functionality:**
```python
class ExportService:
    """Service for exporting data to JSON/CSV."""

    def export_to_json(self, queryset, serializer_class, filename)
    def export_to_csv(self, queryset, fields, filename)
    def create_export_response(self, data, format, filename)
```

**Features:**
- Queryset-based export (flexible filtering)
- Automatic serialization with DRF serializers
- CSV field selection and ordering
- Memory-efficient for large datasets (streaming)
- Proper HTTP response with download headers

**CRITICAL DESIGN DECISION - GoBD Compliance:**
- ⚠️ **Import Mode**: ALWAYS `create_only` (hardcoded)
- ⚠️ **NO update/overwrite functionality** - GoBD compliance requirement
- ⚠️ **Existing records = Import Error** - prevents data manipulation
- Audit trail logs all import attempts (success and failures)

**Dependencies:**
```python
# requirements.in - NO NEW DEPENDENCIES NEEDED
# Using: csv (stdlib), DRF (existing), Django (existing)
```

**Configuration (.env):**
```bash
# Add to .env file
IMPORT_MAX_FILE_SIZE_MB=50
IMPORT_MAX_ROWS=100000
EXPORT_MAX_ROWS=100000
EXPORT_BATCH_SIZE=1000
IMPORT_TIMEOUT_SECONDS=300
```

**Settings (settings.py):**
```python
# Import/Export Configuration (NO MAGIC NUMBERS!)
IMPORT_MAX_FILE_SIZE = int(os.getenv('IMPORT_MAX_FILE_SIZE_MB', 50)) * 1024 * 1024
IMPORT_MAX_ROWS = int(os.getenv('IMPORT_MAX_ROWS', 100000))
EXPORT_MAX_ROWS = int(os.getenv('EXPORT_MAX_ROWS', 100000))
EXPORT_BATCH_SIZE = int(os.getenv('EXPORT_BATCH_SIZE', 1000))
IMPORT_TIMEOUT_SECONDS = int(os.getenv('IMPORT_TIMEOUT_SECONDS', 300))
```

### 1.2 Export Views/Actions

**Files to create/modify:**
- `project_root/invoice_app/api/export_views.py` (new)
- `project_root/invoice_app/admin.py` (modify - add actions)

**API Endpoints:**
```
GET /api/invoices/export/?format=json&filter=...
GET /api/business-partners/export/?format=csv&fields=name,email,tax_id
GET /api/products/export/?format=json
```

**Admin Actions:**
- "Export selected to JSON"
- "Export selected to CSV"
- Available for: Invoice, BusinessPartner, Product, InvoiceLine

**Query Parameters:**
- `format`: json|csv (required)
- `fields`: comma-separated list (CSV only, optional)
- Standard filters (date range, status, etc.)

### 1.3 Tests for Phase 1

**Test file**: `project_root/invoice_app/tests/test_export.py`

**Test Coverage:**
- ✅ Export empty queryset (edge case)
- ✅ Export single object (JSON/CSV)
- ✅ Export multiple objects (100+ items, performance)
- ✅ CSV field selection
- ✅ CSV field ordering
- ✅ JSON nested relationships (company_details, lines)
- ✅ Permission checks (authentication required)
- ✅ Invalid format handling
- ✅ Special characters in CSV (escaping, quotes)
- ✅ Date/Decimal formatting
- ✅ File download headers (Content-Type, Content-Disposition)
- ✅ **File size limit enforcement** (EXPORT_MAX_ROWS from settings)
- ✅ **Configuration loading** (settings from .env)

**Minimum 15 tests**, target coverage: >90%

### 1.4 Documentation for Phase 1

**Files to create/update:**
- `docs/IMPORT_EXPORT_USAGE.md` (user documentation)
- `docs/API_SPECIFICATION.md` (update with export endpoints)

**Content:**
- Export endpoint documentation
- Query parameter reference
- CSV field mapping tables
- Example curl commands
- Admin interface screenshots/description

**Deliverables Phase 1:**
- ✅ Export service implementation
- ✅ API endpoints functional
- ✅ Admin actions working
- ✅ 15+ tests passing
- ✅ Documentation complete

---

## Phase 2: Import Foundation (Week 1, Day 4 - Week 2, Day 2)

### 2.1 Core Import Service

**Files to create:**
- `project_root/invoice_app/services/import_service.py`

**Functionality:**
```python
class ImportService:
    """Service for importing data from JSON/CSV."""

    def import_from_json(self, file, model_class, serializer_class)
    def import_from_csv(self, file, model_class, field_mapping)
    def validate_import_data(self, data, serializer_class)
    def create_import_report(self, results)
```

**Features:**
- **STRICT atomic imports** (all-or-nothing - NO partial imports!)
- Validation BEFORE any database writes
- Detailed error reporting (line number, field, error message)
- **STRICT create_only mode** (NO update/overwrite functionality)
- Duplicate detection:
  - ✅ **ONLY: Fail entire import on ANY duplicate** (GoBD compliance)
  - ❌ Skip duplicates (removed - could hide errors, data loss risk)
  - ❌ Update existing (removed - GoBD violation)
  - ❌ Partial imports (removed - data integrity risk)
- Dry-run mode (validation only, no DB changes)
- Complete audit trail of all import operations

**CRITICAL: Transaction Rollback**
- Single error → Entire import fails
- Database rollback ensures data integrity
- User gets complete error report to fix issues
- Re-import after fixing all errors

**Import Report Structure:**
```json
{
  "status": "success|failed",  // NO "partial" - atomic only!
  "total_rows": 100,
  "imported": 100,  // Either ALL or 0
  "failed": 0,      // Either 0 or total_rows
  "errors": [
    {
      "row": 42,
      "field": "tax_id",
      "error": "This field is required.",
      "data": {"name": "ACME Corp", "tax_id": ""}
    }
  ],
  "transaction_rolled_back": false  // true if ANY error occurred
}
```

**Example: Invoice with Lines Import Failed**
```json
{
  "status": "failed",
  "total_rows": 1,
  "imported": 0,
  "failed": 1,
  "errors": [
    {
      "row": 1,
      "invoice": "INV-2025-001",
      "error": "Invoice line 3: Invalid product_code 'PROD999' (not found)",
      "data": {"invoice_number": "INV-2025-001", "lines": 5}
    }
  ],
  "transaction_rolled_back": true,
  "message": "Import failed: Invoice header AND all lines rolled back due to error in line 3"
}
```

### 2.2 Import Views/Endpoints

**Files to create:**
- `project_root/invoice_app/api/import_views.py` (new)
- `project_root/invoice_app/forms.py` (add import forms for admin)

**API Endpoints:**
```
POST /api/invoices/import/
POST /api/business-partners/import/
POST /api/products/import/
POST /api/invoice-lines/import/  # For adding lines to existing invoice (Phase 2.5)
```

**Scope for Phase 2:**
- ✅ Import Business Partners (standalone, atomic)
- ✅ Import Products (standalone, atomic)
- ✅ Import Invoices **WITH ALL LINES** (complete, atomic)
  - Full nested import: Invoice header + all invoice lines
  - Single transaction: ALL data or NOTHING
  - Any error (header OR any line) → complete rollback
  - Invoice only "imported" when header + ALL lines persisted successfully

**Future Phase 2.5: Add Lines to Existing Invoice**
- Import lines for already-existing invoice (created manually or previously imported)
- Use case: User creates invoice header, later imports lines from work/material list
- Still atomic: ALL new lines imported or NONE
- Requires invoice exists and status = DRAFT

**Request:**
```
POST /api/business-partners/import/
Content-Type: multipart/form-data

file: business_partners.csv
format: csv
dry_run: true|false (default: false)

# NOTE: No 'mode' parameter - ALWAYS create_only for GoBD compliance
# Duplicate records will ALWAYS cause import to fail
```

**Response:**
```json
{
  "import_report": { /* as above */ },
  "processing_time": "2.5s",
  "dry_run": false
}
```

**Admin Interface:**
- Import page for each model
- File upload form
- Format selection (JSON/CSV)
- Dry-run checkbox (validation only)
- **NO import mode selection** (always create_only for GoBD)
- Import report display (success/error table)
- **Clear warning**: "Duplicate records will cause import to fail"

### 2.3 Field Mapping & Validation

**CSV Field Mapping:**

**Business Partners CSV:**
```csv
partner_number,name,email,tax_id,vat_id,address_line1,postal_code,city,country,phone
CUST001,ACME Corp,info@acme.com,DE123456789,DE999888777,Main St 1,10115,Berlin,Germany,+49301234567
```

### 2.3 Field Mapping & Validation

**CSV Field Mapping:**

**Business Partners CSV:**
```csv
partner_number,name,email,tax_id,vat_id,address_line1,postal_code,city,country,phone
CUST001,ACME Corp,info@acme.com,DE123456789,DE999888777,Main St 1,10115,Berlin,Germany,+49301234567
```

**Products CSV:**
```csv
product_code,name,description,product_type,base_price,currency,unit_of_measure,tax_rate,is_active
PROD001,Consulting Hour,Professional consulting,SERVICE,150.00,EUR,HOUR,19.00,true
```

**Invoices with Lines CSV** (complete invoice data):
```csv
# Header fields:
invoice_number,partner_number,issue_date,due_date,currency,payment_terms,status,notes
# Line fields (repeated per line):
line_number,description,product_code,quantity,unit_price,tax_rate

# Example (pseudo-structure, actual implementation may use JSON or nested CSV):
INV-2025-001,CUST001,2025-01-15,2025-02-14,EUR,30,DRAFT,"Consulting project"
# Lines for INV-2025-001:
1,Consulting Hour,PROD001,10,150.00,19.00
2,Travel Expenses,PROD002,1,50.00,19.00
```

**Implementation Options for Invoice+Lines:**

**Option A: JSON Format (Recommended)**
```json
{
  "invoice_number": "INV-2025-001",
  "partner_number": "CUST001",
  "issue_date": "2025-01-15",
  "due_date": "2025-02-14",
  "currency": "EUR",
  "payment_terms": 30,
  "status": "DRAFT",
  "lines": [
    {
      "line_number": 1,
      "description": "Consulting Hour",
      "product_code": "PROD001",
      "quantity": 10,
      "unit_price": 150.00,
      "tax_rate": 19.00
    },
    {
      "line_number": 2,
      "description": "Travel Expenses",
      "product_code": "PROD002",
      "quantity": 1,
      "unit_price": 50.00,
      "tax_rate": 19.00
    }
  ]
}
```

**Option B: CSV with Denormalized Structure**
```csv
invoice_number,partner_number,issue_date,due_date,currency,status,line_number,description,product_code,quantity,unit_price,tax_rate
INV-2025-001,CUST001,2025-01-15,2025-02-14,EUR,DRAFT,1,Consulting Hour,PROD001,10,150.00,19.00
INV-2025-001,CUST001,2025-01-15,2025-02-14,EUR,DRAFT,2,Travel Expenses,PROD002,1,50.00,19.00
```
- Parser groups by invoice_number
- Creates invoice once, adds all lines
- Single transaction for complete invoice

**Products CSV:**
```csv
product_code,name,description,product_type,base_price,currency,unit_of_measure,tax_rate,is_active
PROD001,Consulting Hour,Professional consulting,SERVICE,150.00,EUR,HOUR,19.00,true
```

**Validation Rules:**
- Required fields check
- Foreign key resolution (partner_number → BusinessPartner.id, product_code → Product.id)
- **STRICT unique constraint validation** (fail entire import on ANY duplicate)
- Date format validation (ISO 8601)
- Decimal precision check
- Choice field validation (status, product_type, etc.)
- Email format validation
- Business rule validation (due_date > issue_date)
- **Nested data validation** (invoice lines count, totals match)
- **GoBD Compliance Check**: Prevent any data overwrites
- **Atomic validation**: Validate ENTIRE invoice (header + ALL lines) before ANY write

### 2.4 Tests for Phase 2

**Test file**: `project_root/invoice_app/tests/test_import.py`

**Test Coverage:**
- ✅ Import valid JSON (single object)
- ✅ Import valid JSON (multiple objects)
- ✅ Import valid CSV (with all fields)
- ✅ **Import invoice with lines (complete, nested data)**
- ✅ **Import invoice with invalid line (entire import fails)**
- ✅ **Import multiple invoices with lines (atomic per invoice)**
- ✅ Import CSV with missing optional fields
- ✅ Import CSV with missing required fields (validation error)
- ✅ Import with duplicate detection (fail entire import)
- ✅ Import with invalid data types
- ✅ Import with invalid foreign keys
- ✅ Import with invalid choice values
- ✅ Import with business rule violations
- ✅ **Import transaction rollback on ANY error (header or line)**
- ✅ Dry-run mode (no DB changes, even for valid data)
- ✅ Import report generation
- ✅ Large file import (1000+ rows, performance)
- ✅ Concurrent import handling (race conditions)
- ✅ Permission checks
- ✅ File size limit validation
- ✅ Malformed CSV handling
- ✅ JSON schema validation
- ✅ Special characters and encoding (UTF-8)
- ✅ **File size limit enforcement** (IMPORT_MAX_FILE_SIZE from settings)
- ✅ **Row limit enforcement** (IMPORT_MAX_ROWS from settings)
- ✅ **Timeout handling** (IMPORT_TIMEOUT_SECONDS from settings)
- ✅ **Configuration validation** (invalid .env values)

**Minimum 25 tests** (increased from 20 due to nested invoice complexity), target coverage: >90%

### 2.5 Documentation for Phase 2

**Files to update:**
- `docs/IMPORT_EXPORT_USAGE.md` (add import section)
- `docs/API_SPECIFICATION.md` (add import endpoints)

**Content:**
- Import endpoint documentation
- CSV format specification per model
- Field mapping tables
- Validation rules documentation
- Error handling guide
- Import mode comparison table
- Example files (CSV/JSON templates)
- Troubleshooting guide

**Deliverables Phase 2:**
- ✅ Import service implementation
- ✅ API endpoints functional
- ✅ Admin interface working
- ✅ 20+ tests passing
- ✅ Documentation complete
- ✅ CSV/JSON example files

---

## Phase 3: Advanced Features & UI (Week 2, Day 3-5)

### Optional Phase 2.5: Invoice Lines Import (Can be done anytime after Phase 2)

**Scope**: Add invoice lines to existing invoices (created manually or previously imported)

**Use Case:**
- Invoice already exists (created manually or via previous import)
- User has work list, material list, or time tracking data
- Import lines from CSV to populate/extend existing invoice

**CSV Format:**
```csv
invoice_number,line_number,description,product_code,quantity,unit_price,tax_rate
INV-2025-001,1,Consulting Hour,CONS-HR,10,150.00,19.00
INV-2025-001,2,Travel Expenses,TRAVEL,1,50.00,19.00
INV-2025-002,1,Software License,SW-LIC,1,999.00,19.00
```

**Implementation:**
- POST `/api/invoice-lines/import/`
- Requires existing invoice (lookup by invoice_number)
- Validates invoice exists and is editable (status=DRAFT)
- **Atomic**: ALL lines for an invoice imported or NONE
  - If importing lines for multiple invoices: atomic per invoice
  - Error in any line for invoice X → rollback ALL lines for invoice X
  - Lines for invoice Y (if no errors) → still imported
- Creates/adds lines and updates invoice totals
- **GoBD compliant**: Cannot add lines to already-sent/paid invoices

**Tests:** 12+ tests for line import scenarios

**Timeline:** 2-3 days (independent mini-phase)

**Difference from Phase 2:**
- Phase 2: Import complete new invoices (header + lines)
- Phase 2.5: Add lines to existing invoice (lines only)

---

## Phase 3: Advanced Features & UI (Week 2, Day 3-5)

### 3.1 Bulk Export Features

**Enhancements:**
- Export with filters (date range, status, business partner)
- Export with related data (invoices + lines in one file)
- ZIP export (multiple files)
- Scheduled exports (via Celery - future enhancement)

**API Examples:**
```
GET /api/invoices/export/?format=json&issue_date_after=2025-01-01&issue_date_before=2025-12-31
GET /api/invoices/export/?format=csv&status=PAID&include_lines=true
GET /api/business-partners/export/?format=json&is_active=true&created_after=2025-01-01
```

### 3.2 Template Downloads

**Feature:** Download CSV/JSON templates

**Endpoints:**
```
GET /api/business-partners/import/template/?format=csv
GET /api/invoices/import/template/?format=json
```

**Response:** Empty CSV/JSON with correct headers/structure

**CSV Template Example:**
```csv
partner_number,name,email,tax_id,vat_id,address_line1,postal_code,city,country,phone
# Example row (remove before import):
# CUST001,ACME Corp,info@acme.com,DE123456789,DE999888777,Main St 1,10115,Berlin,Germany,+49301234567
```

### 3.3 Admin UI Enhancements

**Features:**
- Import history table (who imported what when)
- Import preview (before commit)
- Progress bar for large imports (via WebSocket/polling)
- Download import report as JSON
- Re-import failed rows (from error report)

**Model to track imports:**
```python
class ImportLog(models.Model):
    """Track all import operations."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    file_name = models.CharField(max_length=255)
    format = models.CharField(max_length=10, choices=[('json', 'JSON'), ('csv', 'CSV')])
    mode = models.CharField(max_length=20)
    status = models.CharField(max_length=20)  # success, partial, failed
    total_rows = models.IntegerField()
    imported_count = models.IntegerField()
    error_count = models.IntegerField()
    report = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    processing_time = models.FloatField()  # seconds
```

### 3.4 Tests for Phase 3

**Test files:**
- `project_root/invoice_app/tests/test_export_advanced.py`
- `project_root/invoice_app/tests/test_import_advanced.py`
- `project_root/invoice_app/tests/test_import_log.py`

**Test Coverage:**
- ✅ Filtered exports
- ✅ Nested data export (invoices + lines)
- ✅ Template download
- ✅ Import log creation
- ✅ Import history retrieval
- ✅ Large file handling (streaming)
- ✅ Concurrent imports (locking)

**Minimum 10 tests**, target coverage: >85%

### 3.5 Documentation for Phase 3

**Files to update:**
- `docs/IMPORT_EXPORT_USAGE.md` (add advanced features)
- Admin user guide (screenshots, workflows)

**Deliverables Phase 3:**
- ✅ Advanced export features
- ✅ Template downloads
- ✅ Import logging
- ✅ Admin UI enhancements
- ✅ 10+ tests passing
- ✅ Documentation updated

---

## Phase 4: Integration & Polish (Week 3)

### 4.1 RBAC Integration

**Permissions:**
```python
# In UserRole model (add new permission flags)
can_export_data = models.BooleanField(default=False)
can_import_data = models.BooleanField(default=False)
```

**Permission Checks:**
- Export: Requires `can_export_data` or Admin role
- Import: Requires `can_import_data` or Admin role
- Audit log all export/import operations

### 4.2 Performance Optimization

**Export:**
- Streaming large datasets (avoid loading all in memory)
- Pagination for API exports (chunked downloads)
- Async export for very large datasets (Celery task)

**Import:**
- Batch processing (commit every N rows)
- Progress tracking for large imports
- Memory-efficient CSV parsing (streaming)

**Benchmarks:**
- Export 10,000 invoices: < 10 seconds
- Import 10,000 business partners: < 30 seconds
- Memory usage: < 500 MB for 10k records

### 4.3 Error Handling & Edge Cases

**Scenarios to handle:**
- Empty file upload
- Corrupted CSV (malformed quotes, wrong delimiter)
- Invalid JSON structure
- **File size limits** (configurable via IMPORT_MAX_FILE_SIZE_MB in .env)
- Encoding issues (UTF-8, Latin-1)
- Circular dependencies in import order
- **Timeout for very large imports** (configurable via IMPORT_TIMEOUT_SECONDS)
- **Row limits** (configurable via IMPORT_MAX_ROWS)

### 4.4 Final Testing

**Integration Tests:**
- Full import/export workflow (export → modify → import)
- Multi-user concurrent operations
- Cross-model imports (business partners → invoices → lines)
- Permission-based access control

**Performance Tests:**
- Load testing with large datasets
- Memory profiling
- Response time benchmarks

**Security Tests:**
- CSV injection attack prevention
- Path traversal in filenames
- SQL injection via CSV data
- XSS in import data

### 4.5 Documentation Finalization

**Complete documentation package:**
- User guide with screenshots
- API reference (swagger annotations)
- Admin guide
- Developer guide (extending import/export)
- Troubleshooting FAQ
- Security considerations

**Deliverables Phase 4:**
- ✅ RBAC integration complete
- ✅ Performance optimized
- ✅ All edge cases handled
- ✅ Security hardened
- ✅ Complete documentation
- ✅ Ready for production

---

## Testing Strategy Summary

### Test Coverage Goals

**Per Phase:**
- Phase 1: 15+ tests, >90% coverage (export_service.py, export_views.py)
- Phase 2: 25+ tests, >90% coverage (import_service.py, import_views.py, nested invoice import)
- Phase 3: 10+ tests, >85% coverage (advanced features)
- Phase 4: 10+ integration tests

**Total: ~60+ tests** (increased from 55 due to invoice complexity)

### Test Categories

1. **Unit Tests** (services, utilities)
   - Export formatting
   - Import parsing
   - Validation logic
   - Error handling

2. **Integration Tests** (views, API)
   - End-to-end workflows
   - Database transactions
   - File handling
   - Permission checks

3. **Performance Tests**
   - Large dataset handling
   - Memory usage
   - Response times

4. **Security Tests**
   - Input validation
   - Injection attacks
   - Permission enforcement

### Test Execution

```bash
# Run all import/export tests
./run_tests_docker.sh invoice_app.tests.test_export
./run_tests_docker.sh invoice_app.tests.test_import
./run_tests_docker.sh invoice_app.tests.test_import_log

# Run with coverage
./run_tests_docker.sh --coverage invoice_app.tests.test_export*
```

---

## File Structure

```
project_root/invoice_app/
├── services/
│   ├── export_service.py          # NEW - Phase 1
│   ├── import_service.py          # NEW - Phase 2
│   └── __init__.py
├── api/
│   ├── export_views.py            # NEW - Phase 1
│   ├── import_views.py            # NEW - Phase 2
│   ├── urls.py                    # MODIFY - add routes
│   └── serializers.py             # MODIFY - enhance if needed
├── admin.py                       # MODIFY - add export/import actions
├── models/
│   └── import_log.py              # NEW - Phase 3 (or add to config.py)
├── tests/
│   ├── test_export.py             # NEW - Phase 1
│   ├── test_import.py             # NEW - Phase 2
│   ├── test_export_advanced.py   # NEW - Phase 3
│   ├── test_import_advanced.py   # NEW - Phase 3
│   └── test_import_log.py         # NEW - Phase 3
└── templates/
    └── admin/
        ├── import_form.html       # NEW - Phase 2
        └── import_report.html     # NEW - Phase 2

docs/
├── IMPORT_EXPORT_USAGE.md         # NEW - Phase 1+2+3
└── API_SPECIFICATION.md           # MODIFY - add endpoints

examples/
├── business_partners_template.csv         # NEW - Phase 3
├── invoices_template.csv          # NEW - Phase 3
├── products_template.csv          # NEW - Phase 3
├── business_partners_example.json         # NEW - Phase 3
└── invoices_example.json          # NEW - Phase 3
```

---

## Dependencies

**No new dependencies required!**

Using existing tools:
- ✅ Django REST Framework (already installed)
- ✅ Python `csv` module (standard library)
- ✅ Python `json` module (standard library)
- ✅ Django transactions (django.db.transaction)
- ✅ Django file upload handling

**Optional (for future enhancements):**
- `pandas` - for advanced CSV operations (only if needed)
- `celery` - for async exports (already installed)

---

## Success Criteria

### Phase 1 (Export) - Ready when:
- ✅ Can export invoices/business-partners/products to JSON
- ✅ Can export invoices/business-partners/products to CSV
- ✅ API endpoints working with authentication
- ✅ Admin actions functional
- ✅ 15+ tests passing with >90% coverage
- ✅ Documentation complete

### Phase 2 (Import) - Ready when:
- ✅ Can import business partners from CSV/JSON (atomic)
- ✅ Can import products from CSV/JSON (atomic)
- ✅ Can import invoices WITH ALL LINES from CSV/JSON (atomic, nested)
- ✅ Validation working with detailed error reports
- ✅ **Atomic transaction rollback**: ANY error → COMPLETE rollback (no partial data)
- ✅ Dry-run mode working
- ✅ 25+ tests passing with >90% coverage (increased due to invoice complexity)
- ✅ Documentation complete with examples (JSON + CSV formats)
- ✅ Invoice totals auto-calculated from imported lines

### Phase 3 (Advanced) - Ready when:
- ✅ Advanced filtering in exports
- ✅ Template downloads working
- ✅ Import logging functional
- ✅ Admin UI polished
- ✅ 10+ tests passing
- ✅ Documentation updated

### Phase 4 (Production-Ready) - Ready when:
- ✅ RBAC integrated
- ✅ Performance benchmarks met
- ✅ All edge cases handled
- ✅ Security audit passed
- ✅ Complete documentation
- ✅ Code review completed
- ✅ Merged to main branch

---

## Risk Assessment

### Low Risk
- Export functionality (read-only)
- Template downloads
- Import validation

### Medium Risk
- Import with database writes
- Transaction handling
- Large file processing
- Concurrent operations

### High Risk
- Data integrity (imports overwriting data)
- Performance with very large files
- Security (CSV injection, malicious data)

### Mitigation Strategies
- Comprehensive testing (55+ tests)
- Dry-run mode default for imports
- Transaction-based imports (atomic)
- File size limits
- Input sanitization
- Rate limiting on import endpoints
- Audit logging all operations

---

## Timeline Estimate

**Week 1:**
- Days 1-3: Phase 1 (Export) ✅
- Days 4-5: Phase 2 Start (Import core)

**Week 2:**
- Days 1-2: Phase 2 Completion (Import)
- Days 3-5: Phase 3 (Advanced features)

**Week 3:**
- Days 1-3: Phase 4 (Integration & Polish)
- Days 4-5: Code review, documentation finalization

**Total: 15 working days (3 weeks)**

**Contingency: +3-5 days for unexpected issues**

---

## Next Steps

**✅ ALL CRITICAL DECISIONS MADE - Ready to start implementation!**

1. **Create feature branch**: `git checkout -b feature/import-export`
2. **Add .env configuration** (already in .env.ci)
3. **Update settings.py** with configuration loading
4. **Start with Phase 1**: Export implementation
5. **Commit after each sub-phase** with descriptive messages
6. **Run tests continuously**: Aim for green CI pipeline
7. **Update PROGRESS_PROTOCOL.md** after each phase
8. **Create PR after Phase 2** for initial review
9. **Final PR after Phase 4** for merge to main

---

## Questions / Decisions Needed - RESOLVED ✅

- [x] **Import mode**: ✅ DECIDED - ALWAYS `create_only` (GoBD compliance, no overwrites allowed)
- [x] **File size limit**: ✅ DECIDED - 50 MB (configurable via .env, ~100k records)
- [x] **Invoice lines import**: ✅ DECIDED - Full invoices WITH lines in Phase 2 (atomic)
  - **Phase 2**: Complete invoices (header + ALL lines) imported atomically
  - **Phase 2.5 (optional)**: Add lines to existing invoice (separate use case)
- [x] **Duplicate handling**: ✅ DECIDED - Atomic all-or-nothing (single error → complete rollback)
  - **NO partial imports** - data integrity priority
  - **NO skipping errors** - could hide data loss
  - User must fix ALL errors and re-import
- [ ] **Async exports**: Should Phase 4 include Celery integration or defer to later?
- [ ] **Audit log detail level**: Log every imported row or just summary?

### Configuration Strategy

**All limits/thresholds configurable via environment variables (.env):**

```bash
# .env file
# Import/Export Configuration
IMPORT_MAX_FILE_SIZE_MB=50          # Default: 50 MB
IMPORT_MAX_ROWS=100000              # Default: 100k rows
EXPORT_MAX_ROWS=100000              # Default: 100k rows
EXPORT_BATCH_SIZE=1000              # Default: 1k rows per batch
IMPORT_TIMEOUT_SECONDS=300          # Default: 5 minutes
```

**NO magic numbers in code!** All values loaded from settings:

```python
# settings.py
IMPORT_MAX_FILE_SIZE = int(os.getenv('IMPORT_MAX_FILE_SIZE_MB', 50)) * 1024 * 1024  # Convert to bytes
IMPORT_MAX_ROWS = int(os.getenv('IMPORT_MAX_ROWS', 100000))
EXPORT_MAX_ROWS = int(os.getenv('EXPORT_MAX_ROWS', 100000))
EXPORT_BATCH_SIZE = int(os.getenv('EXPORT_BATCH_SIZE', 1000))
IMPORT_TIMEOUT_SECONDS = int(os.getenv('IMPORT_TIMEOUT_SECONDS', 300))
```

**Future enhancement (Phase 4+):**
- Move to SystemConfig model in database for runtime changes
- Keep .env as fallback for initial deployment

---

**Ready to start? Let me know and I'll create the feature branch and begin Phase 1!**
