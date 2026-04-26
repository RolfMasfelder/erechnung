---
description: "Add a new field across all layers: openapi.json → Model → Serializer → ACL fieldMappings → Vue component"
mode: "agent"
---

# Add ACL Field (Full Stack)

Add a new field to the entity across all layers of the Anti-Corruption Layer.

## Field Details

- **Entity**: ${input:entity:Entity name (e.g. Invoice, BusinessPartner)}
- **Field name (UI)**: ${input:uiField:UI-side field name (e.g. payment_terms)}
- **Field name (API)**: ${input:apiField:API-side field name (e.g. payment_terms)}
- **Type**: ${input:fieldType:Field type (e.g. CharField, DecimalField, IntegerField, BooleanField)}

## Steps (in this exact order)

### 1. `docs/openapi.json` — Single Source of Truth
Update the OpenAPI spec FIRST. Add the field to the relevant schema with correct type and constraints.

### 2. Model (`project_root/invoice_app/models/`)
Add the Django model field matching the openapi.json definition.

### 3. Migration
Generate migration: `docker compose exec web python project_root/manage.py makemigrations`

### 4. Serializer (`project_root/invoice_app/api/serializers.py`)
Add field to the serializer `Meta.fields`. Name MUST match `openapi.json`.

### 5. ACL Mapping (`frontend/src/api/fieldMappings.js`)
Add the mapping entry in the entity's `UI_TO_API` section:
```javascript
${input:uiField}: '${input:apiField}',
```
Even if UI and API names are identical — explicit declaration is mandatory.

### 6. Vue Component
Add the field to the relevant form/table components in `frontend/src/`.

### 7. Tests
Add test coverage for the new field in the relevant test file.

## Validation
- Run `docker compose exec web python project_root/manage.py test invoice_app`
- Verify field appears in API response matching `openapi.json`
