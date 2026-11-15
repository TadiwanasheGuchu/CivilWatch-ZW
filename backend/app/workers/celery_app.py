"""Celery application for background jobs (notifications, image processing)."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("civicwatch", broker=str(settings.redis_url), backend=str(settings.redis_url))
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
celery_app.conf.beat_schedule = {
    "purge-stale-sessions": {"task": "identity.purge_stale_sessions", "schedule": 60 * 60},
    "deliver-notification-emails": {"task": "notifications.deliver_email", "schedule": 60},
}
# Discovers app/workers/tasks.py.
celery_app.autodiscover_tasks(["app.workers"])
