# Runbook: HighRequestLatency

**Alert:** `HighRequestLatency`  
**Severity:** warning  
**Category:** Performance

## Summary

The p95 request latency has exceeded 2 seconds over the last 5 minutes.

## Impact

- Degraded user experience
- Risk of timeout errors for slow connections
- PDF generation may be contributing to latency

## Diagnosis

```bash
# Check which endpoints are slowest
# Prometheus query: histogram_quantile(0.95, rate(django_http_requests_latency_seconds_bucket[5m])) by (view)

# Check database slow queries
docker compose exec db psql -U erechnung_user -d erechnung -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;
"

# Check DB connection pool
docker compose exec web python project_root/manage.py shell -c "
from django.db import connections
conn = connections['default']
print(conn.vendor, conn.get_autocommit())
"

# Check Celery queue depth
docker compose exec redis redis-cli LLEN celery
```

## Common Causes and Fixes

1. **Missing database index:** Run `EXPLAIN ANALYZE` on slow queries, add index if needed
2. **N+1 queries:** Check ORM queries with `django-debug-toolbar` or logging
3. **PDF generation blocking:** Ensure PDF generation is async (Celery)
4. **Redis slowdown:** See [RedisMemoryHigh runbook](./RedisMemoryHigh.md)
5. **Resource saturation:** Check CPU/memory usage of Django pods

## Resolution

1. Identify slow views from Prometheus metrics
2. Profile the view if possible
3. Add `select_related()` / `prefetch_related()` for ORM optimization
4. Consider caching for expensive read operations

## Escalation

If latency exceeds 5 seconds p95, escalate to senior engineer.
