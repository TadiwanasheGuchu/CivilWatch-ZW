"""Data access for users and sessions."""

import uuid
from datetime import datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.models.identity import User, UserSession


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        # `email` is CITEXT, so this comparison is case-insensitive.
        return self.db.scalar(select(User).where(User.email == email))

    def email_exists(self, email: str) -> bool:
        return self.db.scalar(select(User.id).where(User.email == email)) is not None

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, session: UserSession) -> UserSession:
        self.db.add(session)
        self.db.flush()
        return session

    def get_active_by_token_hash(
        self, token_hash: bytes, *, now: datetime, idle_cutoff: datetime
    ) -> UserSession | None:
        return self.db.scalar(
            select(UserSession)
            .join(UserSession.user)
            .where(
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
                UserSession.last_seen_at > idle_cutoff,
                User.is_active.is_(True),
            )
        )

    def revoke_by_token_hash(self, token_hash: bytes, *, now: datetime) -> None:
        self.db.execute(
            update(UserSession)
            .where(UserSession.token_hash == token_hash, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def revoke_all_for_user(
        self, user_id: uuid.UUID, *, now: datetime, except_session_id: uuid.UUID | None = None
    ) -> None:
        stmt = update(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
        )
        if except_session_id is not None:
            stmt = stmt.where(UserSession.id != except_session_id)
        self.db.execute(stmt.values(revoked_at=now))

    def delete_stale(self, *, expired_before: datetime, idle_before: datetime) -> int:
        result = self.db.execute(
            delete(UserSession).where(
                or_(
                    UserSession.expires_at < expired_before,
                    UserSession.revoked_at < expired_before,
                    UserSession.last_seen_at < idle_before,
                )
            )
        )
        return result.rowcount or 0
