# Runbook: HighDatabaseConnections

**Alert:** `HighDatabaseConnections`  
**Severity:** warning  
**Category:** Performance

## Summary

The number of active PostgreSQL connections has exceeded 80% of `max_connections`.

## Impact

- Risk of new connections being rejected (connection exhaustion)
- Application may start receiving "too many connections" errors
- Degraded database performance due to connection pressure

## Diagnosis

```bash
# Check current connection count
docker compose exec db psql -U erechnung_user -d erechnung -c "
SELECT count(*), state, wait_event_type, wait_event
FROM pg_stat_activity
WHERE datname = 'erechnung'
GROUP BY state, wait_event_type, wait_event
ORDER BY count DESC;
"

# Check max_connections setting
docker compose exec db psql -U erechnung_user -d erechnung -c "SHOW max_connections;"

# Check for idle-in-transaction connections (connection leak indicator)
docker compose exec db psql -U erechnung_user -d erechnung -c "
SELECT pid, query_start, state, query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY query_start;
"
```

## Common Causes and Fixes

1. **Connection pool too large:** Check Django `CONN_MAX_AGE` and `DATABASE` settings
2. **Connection leak:** Idle-in-transaction connections indicate missing `connection.close()` calls
3. **Too many Celery workers:** Each worker holds connections; reduce concurrency
4. **PgBouncer not configured:** Consider adding PgBouncer for connection pooling

## Resolution

1. Kill stale connections if necessary:
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE datname = 'erechnung'
     AND state = 'idle in transaction'
     AND query_start < NOW() - INTERVAL '10 minutes';
   ```

2. Temporarily reduce Celery concurrency:
   ```bash
   docker compose exec celery celery -A project_root control pool_shrink 2
   ```

3. Increase `max_connections` in PostgreSQL config if justified (requires restart)
