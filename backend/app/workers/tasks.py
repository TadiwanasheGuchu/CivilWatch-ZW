"""Periodic maintenance tasks."""

import logging

from app.core.config import get_settings
from app.core.database import get_session_factory, get_worker_session_factory
from app.services.auth import purge_stale_sessions
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="identity.purge_stale_sessions")
def purge_stale_sessions_task() -> int:
    with get_session_factory()() as db:
        deleted = purge_stale_sessions(db, get_settings())
    logger.info("purged stale sessions", extra={"deleted": deleted})
    return deleted


@celery_app.task(name="notifications.deliver_email")
def deliver_notification_emails_task() -> dict[str, int]:
    from app.services.email_delivery import SmtpSender, deliver_pending

    settings = get_settings()
    factory = get_worker_session_factory()
    if not settings.smtp_host or factory is None:
        # Email is optional: in-app notifications work without it.
        return {"sent": 0, "failed": 0}
    report = deliver_pending(factory, settings, SmtpSender(settings))
    return {"sent": report.sent, "failed": report.failed}
