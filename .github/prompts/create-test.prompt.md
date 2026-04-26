---
description: "Generate tests for a Django/DRF component following project conventions"
mode: "agent"
---

# Create Tests

Generate tests for the specified component.

## Target

${input:component:Component to test (e.g. InvoiceViewSet, ZugferdXmlGenerator, business_partner model)}

## Project Test Conventions

- **Location**: `project_root/invoice_app/tests/`
- **Framework**: Django `TestCase` for models/services, DRF `APITestCase` for API views
- **Auth**: JWT authentication — create test user and obtain token in `setUp()`
- **Execution**: `docker compose exec web python project_root/manage.py test invoice_app --pattern="test_*.py" --verbosity=2`
- **Naming**: `test_<component>.py`, class `<Component>Tests`

## Required Test Coverage

### For ViewSets (API):
- List (GET collection) — authenticated and unauthenticated
- Create (POST) — valid data and validation errors
- Retrieve (GET single) — existing and 404
- Update (PUT/PATCH) — valid and invalid
- Delete (DELETE) — existing and 404
- Permission checks (unauthenticated → 401)

### For Models:
- Field validation and constraints
- `__str__` representation
- Default values
- Unique constraints

### For Services:
- Happy path with expected output
- Edge cases and error conditions
- Integration with dependent models

## Constraints
- Do NOT mock the database — use Django's test DB
- Use `factory` or `setUp()` to create test data
- Each test method tests exactly ONE behavior
