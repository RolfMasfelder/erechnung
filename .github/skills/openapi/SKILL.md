---
name: openapi
display_name: OpenAPI Schema Management
version: 1.0.0
author: Rolf Masfelder
description: Rules for regenerating, validating, and modifying docs/openapi.json (OpenAPI 3.0+)
---

# OpenAPI Schema Management

## Single Source of Truth

`docs/openapi.json` is the **single source of truth** for API field names, data types, and endpoint structure.

- On conflicts between code, docs, or serializers — `openapi.json` always wins.
- Field name or type changes **must start in `openapi.json`** — then propagate to code.

## Regeneration

**Always use the existing script** — never run `manage.py spectacular` manually:

```bash
cd scripts && ./regenerate_openapi.sh
```

### Why the script exists

- `--file` inside the container writes to a container path (`/tmp/`), then `docker cp` copies it to the host.
- Direct `--file /app/docs/openapi.json` may produce YAML instead of JSON due to drf-spectacular behavior.
- The script validates the output is valid JSON and reports the number of paths.

### When to regenerate

- After adding/removing API endpoints (views, routers)
- After modifying serializer fields (new fields, renamed fields, type changes)
- After changing `@extend_schema` decorators
- After modifying `SPECTACULAR_SETTINGS` in Django settings

## Validation

After regeneration, verify:

1. **Valid JSON**: The script does this automatically.
2. **New fields present**: Spot-check that your changes appear in the output.
3. **Pre-commit hook**: `check-json` will catch invalid JSON on commit.

## Workflow: Adding or Changing API Fields

1. **Design** the field in `docs/openapi.json` (or regenerate to see current state)
2. **Implement** in serializers (`invoice_app/api/serializers.py`)
3. **Regenerate**: `cd scripts && ./regenerate_openapi.sh`
4. **Verify**: Confirm the field appears correctly in the regenerated schema
5. **Update ACL**: Add field mapping in `frontend/src/api/fieldMappings.js`

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Running `manage.py spectacular --file` directly on host path | Use `scripts/regenerate_openapi.sh` |
| Output is YAML instead of JSON | The script handles this via `--format openapi-json` + `/tmp/` + `docker cp` |
| Forgetting to regenerate after serializer changes | Always regenerate when API surface changes |
| Editing `openapi.json` by hand without regenerating | Hand-edits get overwritten — change serializers first, then regenerate |
