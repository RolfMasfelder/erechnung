# Runbook: DjangoDown

**Alert:** `DjangoDown`  
**Severity:** critical  
**Category:** Availability

## Summary

The Django application is not responding to HTTP requests. The `/api/health/` endpoint is returning errors or is unreachable.

## Impact

- All API endpoints unavailable
- Frontend shows 502/503 errors
- PDF generation and invoice processing halted

## Diagnosis

```bash
# Check pod status (k3s)
kubectl get pods -n erechnung -l app=django

# Check logs (k3s)
kubectl logs -n erechnung -l app=django --tail=50

# Check container status (docker-compose)
docker compose ps web
docker compose logs web --tail=50

# Check health endpoint directly
curl -v http://localhost:8000/api/health/
```

## Resolution

1. **Restart the service:**
   ```bash
   # k3s
   kubectl rollout restart deployment/django -n erechnung

   # docker-compose
   docker compose restart web
   ```

2. **If OOMKilled:** Check memory limits and recent memory usage. Increase limits if necessary.

3. **If CrashLoopBackOff:** Check logs for startup errors (DB connection, missing env vars).

4. **If DB unavailable:** See [PostgresDown runbook](./PostgresDown.md).

## Escalation

Contact on-call engineer if not resolved within 15 minutes.
