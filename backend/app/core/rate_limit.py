"""Fixed-window rate limiting backed by Redis.

Auth limits fail *closed*: if Redis is unreachable the request is refused
with 503 rather than allowed without protection.
"""

import hashlib
import logging

from redis import Redis
from redis.exceptions import RedisError

from app.core.errors import RateLimitedError, ServiceUnavailableError

logger = logging.getLogger(__name__)


def _key(scope: str, identifier: str) -> str:
    # Hash identifiers so emails and IPs are not stored in Redis in clear text.
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:32]
    return f"ratelimit:{scope}:{digest}"


class RateLimiter:
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def hit(self, scope: str, identifier: str, *, limit: int, window_seconds: int) -> None:
        """Count one event; raise RateLimitedError once the limit is exceeded."""
        key = _key(scope, identifier)
        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            pipe.ttl(key)
            count, _, ttl = pipe.execute()
        except RedisError as exc:
            logger.error("Rate limiter unavailable", extra={"scope": scope})
            raise ServiceUnavailableError(
                "This service is temporarily unavailable. Please try again shortly."
            ) from exc
        if count > limit:
            raise RateLimitedError(
                "Too many attempts. Please wait before trying again.",
                retry_after_seconds=max(int(ttl), 1),
            )

    def check(self, scope: str, identifier: str, *, limit: int) -> None:
        """Raise if the counter is already at its limit, without counting an event."""
        key = _key(scope, identifier)
        try:
            pipe = self._redis.pipeline()
            pipe.get(key)
            pipe.ttl(key)
            raw, ttl = pipe.execute()
        except RedisError as exc:
            logger.error("Rate limiter unavailable", extra={"scope": scope})
            raise ServiceUnavailableError(
                "This service is temporarily unavailable. Please try again shortly."
            ) from exc
        if raw is not None and int(raw) >= limit:
            raise RateLimitedError(
                "Too many attempts. Please wait before trying again.",
                retry_after_seconds=max(int(ttl), 1),
            )

    def reset(self, scope: str, identifier: str) -> None:
        try:
            self._redis.delete(_key(scope, identifier))
        except RedisError:
            # Not fatal: the counter expires on its own.
            logger.warning("Could not reset rate-limit counter", extra={"scope": scope})
