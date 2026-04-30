# Runbook: RedisDown

**Alert:** `RedisDown`  
**Severity:** critical  
**Category:** Availability

## Summary

Redis is not responding. The cache and Celery broker are unavailable.

## Impact

- Celery task queue unavailable — no async processing
- Session cache unavailable (if session backend is Redis)
- Rate limiting may be broken
- PDF generation queue is halted

## Diagnosis

```bash
# Check container/pod status
docker compose ps redis
docker compose logs redis --tail=30

# k3s:
kubectl get pods -n erechnung -l app=redis
kubectl logs -n erechnung -l app=redis --tail=30

# Test connectivity
docker compose exec redis redis-cli PING
docker compose exec web python project_root/manage.py shell -c "
from django.core.cache import cache
cache.set('test', 'ok', 10)
print(cache.get('test'))
"
```

## Common Causes and Fixes

1. **Container crashed:**
   ```bash
   docker compose restart redis
   # k3s: kubectl rollout restart deployment/redis -n erechnung
   ```

2. **Memory limit reached:** Redis evicts keys when maxmemory is reached. See [RedisMemoryHigh](./RedisMemoryHigh.md)

3. **Persistence file corruption:**
   ```bash
   docker compose logs redis | grep -i "error\|warn\|corrupt"
   ```

## Recovery Steps

1. Restart Redis service
2. Verify Celery workers reconnect:
   ```bash
   docker compose restart celery
   docker compose exec celery celery -A project_root inspect ping
   ```
3. Check for queued tasks that may have been lost

## Notes

Redis data loss on restart is acceptable — the application uses Redis for ephemeral caching and task queuing, not as the primary data store.
