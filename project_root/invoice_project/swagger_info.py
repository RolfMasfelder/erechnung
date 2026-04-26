"""
OpenAPI schema config for drf-spectacular.

All settings are now in SPECTACULAR_SETTINGS (settings.py).
This module is kept only for backward compatibility with scripts
that may import api_info.

Regenerate openapi.json:
    docker compose exec web python project_root/manage.py spectacular \
        --file docs/openapi.json --format openapi-json
"""

# Backward-compat: scripts that import api_info get a no-op dict.
api_info = {
    "title": "eRechnung API",
    "version": "v1",
}
