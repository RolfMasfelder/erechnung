"""
This file initializes the Django project and ensures the Celery app is imported
when Django starts so that the @shared_task decorator will use it.
"""

# Import Celery app to ensure shared_task works properly
from .celery import app as celery_app


__all__ = ["celery_app"]
