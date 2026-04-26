---
description: "Create a new DRF API endpoint following project conventions (Serializer + ViewSet + URL + Test)"
mode: "agent"
---

# Create DRF API Endpoint

Create a complete Django REST Framework endpoint for the entity described below.

## Entity

${input:entityName:Name of the entity (e.g. Product, Invoice)}

## Requirements

Follow the existing project patterns exactly:

### 1. Serializer (`project_root/invoice_app/api/serializers.py`)
- Add a `ModelSerializer` for the entity
- Reference the model from `invoice_app/models/`
- Include all fields from `docs/openapi.json` for this entity

### 2. ViewSet (`project_root/invoice_app/api/rest_views.py`)
- Add a `ModelViewSet` using the new serializer
- Use `IsAuthenticated` permission class
- Register in the existing `DefaultRouter` in `project_root/invoice_app/api/urls.py`

### 3. URL Registration (`project_root/invoice_app/api/urls.py`)
- Register with `router.register(r"<plural-name>", <Entity>ViewSet)`

### 4. Tests (`project_root/invoice_app/tests/`)
- Create CRUD tests (list, create, retrieve, update, delete)
- Use `APITestCase` with JWT authentication
- Follow pattern from `test_api_views.py`

### 5. OpenAPI (`docs/openapi.json`)
- Update `docs/openapi.json` FIRST — it is the single source of truth for field names and types
- Serializer field names MUST match `openapi.json`

### 6. ACL Field Mapping (`frontend/src/api/fieldMappings.js`)
- Add mapping entry for the new entity
- ALL fields must be declared, even 1:1 mappings
- Follow pattern in `docs/ACL_FIELD_MAPPING.md`

## Constraints
- Docker-first: test via `docker compose exec web python project_root/manage.py test`
- Push to BOTH remotes (`origin` and `github`)
