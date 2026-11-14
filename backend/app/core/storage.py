"""Private S3-compatible object storage for uploaded media.

Objects are never public. The API hands browsers short-lived pre-signed GET
URLs, generated with a client pointed at the *public* endpoint so the
signature matches the host the browser will call.
"""

import logging
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings
from app.core.errors import ServiceUnavailableError

logger = logging.getLogger(__name__)


def _client(settings: Settings, endpoint_url: str | None) -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=settings.storage_region,
        aws_access_key_id=(
            settings.storage_access_key_id.get_secret_value()
            if settings.storage_access_key_id
            else None
        ),
        aws_secret_access_key=(
            settings.storage_secret_access_key.get_secret_value()
            if settings.storage_secret_access_key
            else None
        ),
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=3,
            read_timeout=10,
            retries={"max_attempts": 2},
        ),
    )


class ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.storage_bucket
        self._client = _client(settings, settings.storage_endpoint_url)
        self._signer = _client(
            settings, settings.storage_public_endpoint_url or settings.storage_endpoint_url
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl="private, max-age=300",
            )
        except (BotoCoreError, ClientError) as exc:
            logger.error("Object storage write failed", extra={"key": key})
            raise ServiceUnavailableError(
                "Photos cannot be saved right now. Please try again shortly."
            ) from exc

    def delete(self, key: str) -> None:
        """Best effort: a leftover private object is harmless, so failures are logged."""
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError):
            logger.warning("Object storage delete failed", extra={"key": key})

    def signed_url(self, key: str, ttl_seconds: int) -> str:
        # Signing is local computation; no network call per URL.
        return self._signer.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=ttl_seconds,
        )

    def is_available(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except (BotoCoreError, ClientError):
            logger.warning("Readiness: object storage unavailable", exc_info=True)
            return False
        return True

    def ensure_bucket(self) -> None:
        """Create the (private) bucket if missing. For local development and tests."""
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self.bucket)


@lru_cache
def get_storage() -> ObjectStorage:
    return ObjectStorage(get_settings())
