"""ORM models. Import every model module here so Alembic sees full metadata."""

from app.models.base import Base

__all__ = ["Base"]
