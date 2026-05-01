# Runbook: PostgresDown

**Alert:** `PostgresDown`  
**Severity:** critical  
**Category:** Availability

## Summary

PostgreSQL is not responding. The database is unreachable or failing health checks.

## Impact

- All application functionality unavailable
- Django returns 500 errors
- All API endpoints fail

## Diagnosis

```bash
# Check container/pod status
# docker-compose:
docker compose ps db
docker compose logs db --tail=50

# k3s:
kubectl get pods -n erechnung -l app=postgres
kubectl logs -n erechnung -l app=postgres --tail=50

# Test connectivity directly
docker compose exec web python project_root/manage.py dbshell -c "SELECT version();"

# Check disk space (common cause of postgres crashes)
df -h /var/lib/postgresql/data
# k3s: check PVC usage
kubectl get pvc -n erechnung
```

## Common Causes and Fixes

1. **Disk full:**
   ```bash
   # Free disk space or expand PVC
   kubectl patch pvc postgres-data -n erechnung -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
   ```

2. **OOM Kill:**
   ```bash
   dmesg | grep -i "oom\|kill" | tail -20
   # Increase memory limits if needed
   ```

3. **Data corruption:** Check PostgreSQL logs for `PANIC` or `FATAL` messages

4. **Container crash:**
   ```bash
   docker compose restart db
   # or: kubectl rollout restart deployment/postgres -n erechnung
   ```

## Recovery Steps

1. Restart the database service
2. Verify data integrity: `docker compose exec db pg_dumpall --schema-only | head -50`
3. Check for pending migrations: `docker compose exec web python project_root/manage.py migrate --check`
4. Test application connectivity

## Escalation

If database does not recover within 5 minutes, activate backup restoration procedure. See `docs/OPERATIONS.md`.
