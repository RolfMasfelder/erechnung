# Runbook: RedisMemoryHigh

**Alert:** `RedisMemoryHigh`  
**Severity:** warning  
**Category:** Performance

## Summary

Redis memory usage has exceeded 80% of `maxmemory`. Risk of eviction or OOM.

## Impact

- Cache eviction begins (LRU policy), reducing cache hit rate
- Performance degradation as more requests hit the database
- If memory is fully exhausted, Celery task enqueue may fail

## Diagnosis

```bash
# Check Redis memory usage
docker compose exec redis redis-cli INFO memory | grep -E "used_memory_human|maxmemory_human|mem_fragmentation_ratio|evicted_keys"

# Check key count and largest keys
docker compose exec redis redis-cli DBSIZE
docker compose exec redis redis-cli --bigkeys

# Check which key patterns use the most memory
docker compose exec redis redis-cli MEMORY DOCTOR
```

## Common Causes and Fixes

1. **Large Celery result backend:** Tasks storing large results in Redis
   ```bash
   # Check result backend key count
   docker compose exec redis redis-cli KEYS "celery-task-meta-*" | wc -l
   # Reduce CELERY_RESULT_EXPIRES setting
   ```

2. **Cache not expiring:** Check cache key TTLs
   ```bash
   docker compose exec redis redis-cli TTL <key>
   ```

3. **Memory fragmentation:** High `mem_fragmentation_ratio` (>1.5) suggests fragmentation
   ```bash
   docker compose exec redis redis-cli MEMORY PURGE
   ```

## Resolution

1. Delete expired Celery results:
   ```bash
   docker compose exec web python project_root/manage.py shell -c "
   from django_celery_results.models import TaskResult
   from django.utils import timezone
   from datetime import timedelta
   old = TaskResult.objects.filter(date_done__lt=timezone.now() - timedelta(days=7))
   print(f'Deleting {old.count()} old results')
   old.delete()
   "
   ```

2. If immediate relief needed: `docker compose exec redis redis-cli FLUSHDB` (loses all cache — acceptable)

3. Increase `maxmemory` in Redis config if growth is expected

## Notes

Data loss in Redis is acceptable — it holds only cache and ephemeral task data, not the primary data store.
