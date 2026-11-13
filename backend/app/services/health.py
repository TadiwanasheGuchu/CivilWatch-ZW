"""Dependency checks used by readiness probes."""

import logging

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.schemas.health import ComponentStatus, ReadinessResponse

logger = logging.getLogger(__name__)


def check_database(db: Session) -> tuple[ComponentStatus, ComponentStatus]:
    """Return (database, postgis) status."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Readiness: database unreachable", exc_info=True)
        return "unavailable", "unavailable"
    try:
        db.execute(text("SELECT postgis_version()"))
    except SQLAlchemyError:
        logger.warning("Readiness: PostGIS extension unavailable", exc_info=True)
        db.rollback()
        return "ok", "unavailable"
    return "ok", "ok"


def check_cache(redis_client: Redis) -> ComponentStatus:
    try:
        redis_client.ping()
    except RedisError:
        logger.warning("Readiness: Redis unreachable", exc_info=True)
        return "unavailable"
    return "ok"


def readiness(db: Session, redis_client: Redis) -> ReadinessResponse:
    database, postgis = check_database(db)
    cache = check_cache(redis_client)
    healthy = database == "ok" and postgis == "ok" and cache == "ok"
    return ReadinessResponse(
        status="ok" if healthy else "degraded", database=database, postgis=postgis, cache=cache
    )
