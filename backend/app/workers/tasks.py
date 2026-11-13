"""Periodic maintenance tasks."""

import logging

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.services.auth import purge_stale_sessions
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="identity.purge_stale_sessions")
def purge_stale_sessions_task() -> int:
    with get_session_factory()() as db:
        deleted = purge_stale_sessions(db, get_settings())
    logger.info("purged stale sessions", extra={"deleted": deleted})
    return deleted
