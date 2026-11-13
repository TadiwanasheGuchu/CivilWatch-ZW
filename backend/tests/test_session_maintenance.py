from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.identity import UserSession
from app.services.auth import purge_stale_sessions
from tests.conftest import register


def test_purge_removes_only_stale_sessions(client: TestClient, db: Session) -> None:
    register(client, email="a@example.com")
    register(client, email="b@example.com")
    register(client, email="c@example.com")
    sessions = db.scalars(select(UserSession).order_by(UserSession.created_at)).all()
    long_ago = datetime.now(UTC) - timedelta(days=60)
    db.execute(
        update(UserSession).where(UserSession.id == sessions[0].id).values(expires_at=long_ago)
    )
    db.execute(
        update(UserSession).where(UserSession.id == sessions[1].id).values(revoked_at=long_ago)
    )
    db.commit()

    assert purge_stale_sessions(db, get_settings()) == 2
    assert db.scalar(select(func.count()).select_from(UserSession)) == 1
