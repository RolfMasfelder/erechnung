# Runbook: HighCeleryTaskFailureRate

**Alert:** `HighCeleryTaskFailureRate`  
**Severity:** warning  
**Category:** Reliability

## Summary

More than 10% of Celery tasks have failed in the last 15 minutes.

## Impact

- Background job processing degraded
- PDF generation may be failing (if async)
- Email notifications may not be sent
- ZUGFeRD/Factur-X XML generation may be delayed

## Diagnosis

```bash
# Check Celery worker status
docker compose exec celery celery -A project_root inspect ping
docker compose exec celery celery -A project_root inspect active

# Check failed tasks (last 20)
docker compose exec web python project_root/manage.py shell -c "
from django_celery_results.models import TaskResult
failures = TaskResult.objects.filter(status='FAILURE').order_by('-date_done')[:20]
for t in failures:
    print(f'{t.task_name}: {t.result[:150]}')
"

# Check Celery worker logs
docker compose logs celery --tail=50

# Check Redis broker connectivity
docker compose exec celery redis-cli -h redis PING
```

## Common Causes and Fixes

1. **Worker crashed:** Restart Celery workers
   ```bash
   docker compose restart celery
   ```

2. **Redis unavailable:** See [RedisDown runbook](./RedisDown.md)

3. **Specific task bug:** Check which task_name is failing and investigate the code

4. **Database unavailable:** See [PostgresDown runbook](./PostgresDown.md)

5. **Memory limit:** Workers running out of memory; check with `docker stats`

## Resolution

1. Restart Celery workers
2. Check if tasks need to be retried:
   ```bash
   docker compose exec web python project_root/manage.py shell -c "
   from django_celery_results.models import TaskResult
   # Retry failed PDF tasks
   from invoice_app.tasks import generate_pdf_task
   failed = TaskResult.objects.filter(status='FAILURE', task_name__icontains='pdf')
   for t in failed:
       # Extract invoice_id from args/kwargs if needed
       pass
   "
   ```

3. Review Celery concurrency settings if failure rate is due to resource exhaustion

## Escalation

If more than 50% of tasks fail for more than 30 minutes, escalate to senior engineer.
