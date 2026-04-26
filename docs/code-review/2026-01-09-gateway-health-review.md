# Code Review: API Gateway & Health Endpoints

**Ready for Production**: Yes (with minor hardening recommended)
**Critical Issues**: 0

## Priority 1 (Must Fix) ⛔

- None identified. Current posture avoids sensitive information disclosure and enforces JWT on protected health endpoints.

## Findings

- Public health endpoint in [project_root/invoice_app/views/health.py](project_root/invoice_app/views/health.py) returns minimal data and uses short DB ping. Exposure is acceptable but could be abused without rate limiting.
- Detailed health endpoint (`/health/detailed/`) requires JWT and avoids internal metrics exposure. Good alignment with principle of least privilege.
- Readiness endpoint (`/health/readiness/`) is public for Kubernetes/CI-CD compatibility (updated 2026-01-22).
- API Gateway config in [api-gateway/api-gateway.conf](api-gateway/api-gateway.conf) aligns routes and security headers; duplicate `X-Frame-Options` header resolved by relying on global [api-gateway/nginx.conf](api-gateway/nginx.conf).
- Root redirect points to `/api/docs/` and matches documentation in [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md). Consistent.

## Recommended Changes

- Rate limit public health endpoint:
  - Define a dedicated zone in [api-gateway/nginx.conf](api-gateway/nginx.conf):

    ```nginx
    limit_req_zone $binary_remote_addr zone=health_limit:10m rate=10r/s;
    ```

  - Apply in [api-gateway/api-gateway.conf](api-gateway/api-gateway.conf):

    ```nginx
    location = /health {
        limit_req zone=health_limit burst=20 nodelay;
        ...
    }
    location = /health/ {
        limit_req zone=health_limit burst=20 nodelay;
        ...
    }
    ```

- Optional IP allowlist for protected health endpoints (CI/CD, SRE subnets only):

  ```nginx
  location = /health/detailed/ {
    allow 10.0.0.0/8;  # adjust to your ops network
    deny all;
    ...
  }
  location = /health/readiness/ {
    allow 10.0.0.0/8;  # adjust to your ops network
    deny all;
    ...
  }
  ```

- Remove unnecessary CSRF exemption on a GET endpoint:
  - In [project_root/invoice_app/views/health.py](project_root/invoice_app/views/health.py), `@csrf_exempt` is not required for `GET`. Removing shrinks attack surface:

    ```python
    @require_http_methods(["GET"])  # drop @csrf_exempt
    def health_check(request) -> JsonResponse:
        ...
    ```

- Enable HSTS preload in HTTPS gateway (production only):
  - In [api-gateway/api-gateway-https.conf](api-gateway/api-gateway-https.conf), uncomment and use preload:

    ```nginx
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    ```

- Prefer CSP over legacy X-XSS-Protection:
  - In [api-gateway/api-gateway.conf](api-gateway/api-gateway.conf), consider removing `X-XSS-Protection` and enabling a tighter CSP once UI needs are known:

    ```nginx
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'" always;
    ```

- Optional gateway-side JWT verification:
  - Enable Lua-based validation at the gateway for `/api/` to reduce load on Django when tokens are clearly invalid:

    ```nginx
    location /api/ {
        access_by_lua_file /etc/nginx/lua/jwt_validator.lua;
        ...
    }
    ```

## Notes

- Current configs use strict timeouts for health endpoints, which limits blast radius of probes or abuse. Pairing with rate limiting strengthens this further.
- Readiness checks verify migrations without exposing counts or sensitive details. Good balance between observability and security.
- Documentation and OpenAPI schema are aligned with gateway routing; `/api/docs/` is consistent across configs and docs.
