"""Health probes.

These endpoints are intentionally unauthenticated: orchestrators and load
balancers call them. They reveal only coarse component status, never versions,
hostnames or error messages.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from redis import Redis
from sqlalchemy.orm import Session

from app.core.cache import get_redis
from app.core.database import get_db
from app.core.storage import ObjectStorage, get_storage
from app.schemas.health import LivenessResponse, ReadinessResponse
from app.services import health as health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LivenessResponse, summary="Process liveness")
def live() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Dependency readiness",
    responses={503: {"model": ReadinessResponse}},
)
def ready(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[Redis, Depends(get_redis)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
) -> ReadinessResponse:
    result = health_service.readiness(db, redis_client, storage)
    if result.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
