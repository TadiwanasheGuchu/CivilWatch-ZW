"""Database engine and session management.

Row-Level Security identity: once a request is authenticated, the user's ID
is stored in `session.info` and written to the transaction-local setting
`app.user_id` at the start of every transaction. PostgreSQL policies read it
through `app_current_user_id()`. Being transaction-local, it can never leak
to another request through a pooled connection.
"""

import uuid
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker

from app.core.config import get_settings

RLS_USER_KEY = "rls_user_id"
_SET_RLS_USER = text("SELECT set_config('app.user_id', :user_id, true)")


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        str(settings.database_url),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        # All timestamps are stored and handled in UTC.
        connect_args={"options": "-c timezone=UTC"},
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "after_begin")
def _apply_rls_user(session: Session, _: SessionTransaction, connection: Connection) -> None:
    user_id = session.info.get(RLS_USER_KEY)
    if user_id is not None:
        connection.execute(_SET_RLS_USER, {"user_id": str(user_id)})


def bind_rls_user(session: Session, user_id: uuid.UUID) -> None:
    """Act as `user_id` for RLS in this and every later transaction of `session`."""
    session.info[RLS_USER_KEY] = user_id
    if session.in_transaction():
        session.execute(_SET_RLS_USER, {"user_id": str(user_id)})


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session; rolls back on any error."""
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
