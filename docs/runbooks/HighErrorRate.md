# Runbook: HighErrorRate

**Alert:** `HighErrorRate`  
**Severity:** critical  
**Category:** Reliability

## Summary

The HTTP 5xx error rate has exceeded 5% over the last 5 minutes.

## Impact

- Users receiving server errors
- Invoice creation and retrieval may be failing
- Data integrity risk if errors occur during write operations

## Diagnosis

```bash
# Check recent error logs
kubectl logs -n erechnung -l app=django --tail=100 | grep -E "ERROR|CRITICAL|500|502|503"

# Check which endpoints are failing
# Prometheus query: rate(django_http_responses_total_by_status_total{status=~"5.."}[5m])

# Check Celery task failures
docker compose exec web python project_root/manage.py shell -c "
from django_celery_results.models import TaskResult
print(TaskResult.objects.filter(status='FAILURE').order_by('-date_done')[:10].values('task_name', 'result', 'date_done'))
"

# Check DB connectivity
docker compose exec web python project_root/manage.py dbshell -c "SELECT 1;"
```

## Common Causes and Fixes

1. **Database connection errors:** See [PostgresDown runbook](./PostgresDown.md)
2. **Redis connection errors:** See [RedisDown runbook](./RedisDown.md)
3. **Unhandled exception in view:** Check application logs for traceback
4. **Memory pressure:** Check pod resource usage, consider scaling

## Resolution

1. Identify the failing endpoint from logs
2. Check for recent deployments (`kubectl rollout history deployment/django -n erechnung`)
3. Rollback if a deployment caused the error:
   ```bash
   kubectl rollout undo deployment/django -n erechnung
   ```

## Escalation

If error rate persists above 5% for more than 10 minutes, escalate to senior engineer.
