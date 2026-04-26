# Dependency Version Audit

**Date:** 2026-04-08
**Branch:** `feature/dependency-version-audit`
**Purpose:** Evaluate all component versions and identify upgrade opportunities

---

## Executive Summary

The project's **Python and npm dependencies are almost entirely up to date** — a testament to good maintenance. The only major upgrade opportunity is **Django 5.2 → 6.0**, which is blocked by `django-prometheus`.

The **monitoring stack is significantly outdated** (Prometheus 2.x, Grafana 10.x, Loki 2.x) and should be upgraded independently.

### Key Decisions Required

1. **Django 6.0 upgrade** — blocked by `django-prometheus` (`Django<6.0` hard constraint)
2. **Monitoring stack** — Prometheus, Grafana, Loki/Promtail all multiple major versions behind
3. **Python version alignment** — Dockerfile uses 3.14, pyproject.toml targets 3.13

---

## 1. Python Dependencies

### 1.1 Major Upgrade Available

| Package | Current | Latest | Impact | Action |
|---------|---------|--------|--------|--------|
| Django | 5.2.12 | **6.0.4** | Major | See Django 6.0 analysis below |

### 1.2 Minor Update Available

| Package | Current | Latest | Impact | Action |
|---------|---------|--------|--------|--------|
| pytest | 9.0.2 | 9.0.3 | Patch | Low risk, update when convenient |

### 1.3 Already Current (no action needed)

| Package | Version | Category |
|---------|---------|----------|
| djangorestframework | 3.17.1 | Web Framework |
| psycopg2-binary | 2.9.11 | Database |
| celery | 5.6.3 | Task Queue |
| redis (Python) | 7.4.0 | Cache Client |
| gunicorn | 25.3.0 | WSGI Server |
| weasyprint | 68.1 | PDF Generation |
| sentry-sdk | 2.57.0 | Error Tracking |
| django-allauth | 65.15.1 | Authentication |
| django-axes | 8.3.1 | Security |
| django-filter | 25.2 | API Filtering |
| drf-spectacular | 0.29.0 | API Schema |
| django-cors-headers | 4.9.0 | CORS |
| django-csp | 4.0 | CSP Headers |
| django-debug-toolbar | 6.3.0 | Development |
| django-extensions | 4.1 | Development |
| django-prometheus | 2.4.1 | Monitoring |
| django-redis | 6.0.0 | Cache Backend |
| djangorestframework-simplejwt | 5.5.1 | JWT Auth |
| whitenoise | 6.12.0 | Static Files |
| xmlschema | 4.3.1 | XML Validation |
| factur-x | 4.2 | ZUGFeRD/Factur-X |
| saxonche | 12.9.0 | XSLT Processing |
| python-dotenv | 1.2.2 | Configuration |
| pikepdf | 10.5.1 | PDF Processing |
| pillow | 12.2.0 | Image Processing |
| lxml | 6.0.2 | XML Processing |
| python-json-logger | 4.1.0 | Logging |
| ruff | 0.15.9 | Linting |
| coverage | 7.13.5 | Test Coverage |
| bandit | 1.9.4 | Security Scan |
| pre-commit | 4.5.1 | Git Hooks |
| factory-boy | 3.3.3 | Test Fixtures |
| environs | 15.0.1 | Configuration |
| prometheus-client | 0.24.1 | Metrics |

---

## 2. Django 6.0 Upgrade Analysis

### 2.1 Constraint in `requirements.in`

```
django>=5.2,<5.3    # Must change to django>=6.0,<6.1 for upgrade
```

### 2.2 Django 6.0 Compatibility Matrix

| Package | Django 6.0 Ready? | Evidence |
|---------|-------------------|----------|
| djangorestframework 3.17.1 | ✅ Yes | Classifiers include Django 6.0 |
| django-allauth 65.15.1 | ✅ Yes | Classifiers include Django 6.0 |
| django-axes 8.3.1 | ✅ Yes | Classifiers include Django 6.0 + Python 3.14 |
| django-cors-headers 4.9.0 | ✅ Yes | Classifiers include Django 6.0 + Python 3.14 |
| django-debug-toolbar 6.3.0 | ✅ Yes | Classifiers include Django 6.0 + Python 3.14 |
| whitenoise 6.12.0 | ✅ Yes | Classifiers include Django 6.0 + Python 3.14 |
| django-redis 6.0.0 | ⚠️ Likely OK | No upper bound in requires_dist |
| djangorestframework-simplejwt 5.5.1 | ⚠️ Likely OK | No upper bound, not in classifiers |
| django-filter 25.2 | ⚠️ Unknown | Not in classifiers, needs testing |
| drf-spectacular 0.29.0 | ⚠️ Unknown | Classifiers only up to Django 5.2 |
| django-csp 4.0 | ⚠️ Unknown | Classifiers only up to Django 5.2 |
| django-extensions 4.1 | ⚠️ Unknown | Classifiers only up to Django 5.2 |
| **django-prometheus 2.4.1** | **🚫 BLOCKER** | **`Django<6.0` in requires_dist** |

### 2.3 Hard Blocker: django-prometheus

`django-prometheus` version 2.4.1 has an explicit upper bound `Django<6.0` in its package metadata. **pip will refuse to install it alongside Django 6.x.**

**Options:**
1. **Wait** for a new django-prometheus release that removes the upper bound
2. **Fork** django-prometheus and remove the constraint (maintenance burden)
3. **Replace** with a custom Prometheus integration (django middleware + prometheus_client directly)
4. **Pin with `--no-deps`** and test manually (fragile, not recommended)

### 2.4 Django 6.0 Breaking Changes to Investigate

Before migrating, review the [Django 6.0 release notes](https://docs.djangoproject.com/en/6.0/releases/6.0/) for:
- Removed deprecated features from Django 4.x/5.x
- API changes in models, forms, views, middleware
- Template engine changes
- Test framework changes

### 2.5 Recommendation

**Do NOT upgrade to Django 6.0 yet.** The `django-prometheus` blocker makes this impractical. Monitor these repositories for Django 6.0 support:
- https://github.com/korfuri/django-prometheus/issues — watch for 6.0 compatibility
- https://github.com/nigma/drf-spectacular — watch for updated classifiers

**Estimated timeline:** Wait for django-prometheus to release Django 6.0 support, then plan a coordinated upgrade sprint.

---

## 3. Frontend Dependencies (npm)

All packages use caret (`^`) semver ranges and resolve to their latest versions via `npm install`. No action needed.

### 3.1 Production Dependencies

| Package | Range | Latest | Status |
|---------|-------|--------|--------|
| vue | ^3.5.32 | 3.5.32 | ✅ Current |
| vue-router | ^5.0.4 | 5.0.4 | ✅ Current |
| pinia | ^3.0.4 | 3.0.4 | ✅ Current |
| axios | ^1.14.0 | 1.14.0 | ✅ Current |
| @vuepic/vue-datepicker | ^12.1.0 | 12.1.0 | ✅ Current |
| date-fns | ^4.1.0 | 4.1.0 | ✅ Current |

### 3.2 Development Dependencies

| Package | Range | Latest | Status |
|---------|-------|--------|--------|
| vite | ^8.0.6 | 8.0.7 | ✅ Auto-covered by ^ |
| vitest | ^4.0.18 | 4.1.3 | ✅ Auto-covered by ^ |
| tailwindcss | ^4.1.18 | 4.2.2 | ✅ Auto-covered by ^ |
| @tailwindcss/postcss | ^4.2.2 | 4.2.2 | ✅ Current |
| @vitejs/plugin-vue | ^6.0.5 | 6.0.5 | ✅ Current |
| @vitest/coverage-v8 | ^4.1.3 | 4.1.3 | ✅ Current |
| @vitest/ui | ^4.0.8 | 4.1.3 | ✅ Auto-covered by ^ |
| @vue/test-utils | ^2.4.6 | 2.4.6 | ✅ Current |
| @playwright/test | ^1.59.1 | 1.59.1 | ✅ Current |
| postcss | ^8.5.8 | 8.5.9 | ✅ Auto-covered by ^ |
| autoprefixer | ^10.4.27 | 10.4.27 | ✅ Current |
| happy-dom | ^20.8.9 | 20.8.9 | ✅ Current |

---

## 4. Docker / Infrastructure Images

### 4.1 Application Images

| Image | Current | Latest Stable | Status | Action |
|-------|---------|---------------|--------|--------|
| python | 3.13-slim-bookworm | 3.13 | ✅ Current | Aligned with pyproject.toml + host OS |
| PostgreSQL | 17 (custom build) | 17 | ✅ Current | Latest stable major |
| Redis | 7-alpine | 8.x available | ⚠️ Optional | 7.x still maintained until ~2028 |

### 4.2 Monitoring Stack (docker-compose.monitoring.yml)

| Image | Current | Latest | Delta | Priority |
|-------|---------|--------|-------|----------|
| prom/prometheus | v3.11.1 | v3.11.1 | — | ✅ Done |
| grafana/grafana | 12.4.2 | 12.4.2 | — | ✅ Done |
| grafana/loki | 3.7.1 | 3.7.1 | — | ✅ Done |
| grafana/promtail | 3.7.1 | 3.7.1 | — | ✅ Done |
| oliver006/redis_exporter | v1.82.0 | v1.82.0 | — | ✅ Done |
| prometheuscommunity/postgres-exporter | v0.19.1 | v0.19.1 | — | ✅ Done |

### 4.3 Monitoring Upgrade Notes

**Prometheus v2 → v3:**
- Major config format changes (scrape configuration, rule files)
- Native histograms enabled by default
- New UI
- Review: https://prometheus.io/docs/prometheus/latest/migration/

**Grafana 10 → 12:**
- Two major version jumps (10 → 11 → 12)
- Dashboard schema changes
- Plugin API updates
- Review: https://grafana.com/docs/grafana/latest/upgrade-guide/

**Loki/Promtail 2 → 3:**
- Major storage format changes (TSDB index)
- Config format changes
- Promtail replaced by Alloy in Loki 3.x ecosystem
- Review: https://grafana.com/docs/loki/latest/setup/upgrade/

**Recommendation:** All monitoring images have been upgraded. Verify dashboards and alert rules after starting the updated stack.

---

## 5. Python Version Alignment

| File | Python Version |
|------|---------------|
| Dockerfile | `python:3.13-slim-bookworm` |
| pyproject.toml | `target-version = "py313"` |

**Status:** ✅ Aligned — Dockerfile downgraded to Python 3.13 to match pyproject.toml and host OS.

---

## 6. Prioritized Action Plan

### Immediate (Low Risk)
- [x] Update `pytest` from 9.0.2 → 9.0.3 in requirements
- [x] Align Python version — Dockerfile downgraded to `python:3.13-slim-bookworm`

### Short-Term (Monitoring Stack)
- [x] Upgrade Grafana 10.4.1 → 12.4.2
- [x] Upgrade Prometheus v2.51.0 → v3.11.1 (removed deprecated console flags)
- [x] Upgrade Loki/Promtail 2.9.6 → 3.7.1 (migrated retention to limits_config)
- [x] Upgrade redis_exporter v1.58.0 → v1.82.0
- [x] Upgrade postgres_exporter v0.15.0 → v0.19.1

### Medium-Term (Django 6.0 — blocked by django-prometheus)
- [ ] Monitor django-prometheus for Django 6.0 support
- [ ] Monitor drf-spectacular, django-csp, django-extensions for Django 6.0 classifiers
- [ ] Once unblocked: update `requirements.in` constraint, run test suite, fix breakages

### Optional
- [ ] Consider Redis 7 → 8 upgrade (not urgent, 7.x supported until ~2028)
