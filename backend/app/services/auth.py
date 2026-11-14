"""Authentication: registration, sign-in, sessions and password changes.

Design: docs/06-security-and-privacy.md. Every method that writes commits
its own transaction so a request never leaves partial state behind.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import bind_rls_user
from app.core.errors import AppError, AuthenticationError, ConflictError
from app.core.rate_limit import RateLimiter
from app.core.security import (
    generate_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.models.councils import Council, CouncilMembership
from app.models.identity import User, UserSession
from app.repositories.identity import SessionRepository, UserRepository
from app.services.audit import record_audit

logger = logging.getLogger(__name__)

INVALID_LOGIN_MESSAGE = "Email or password is incorrect."
USER_AGENT_MAX_LENGTH = 255


class InvalidCurrentPasswordError(AppError):
    status_code = 400
    code = "invalid_current_password"


@dataclass(frozen=True)
class IssuedSession:
    """A newly created session. `token` exists only here and in the cookie."""

    session: UserSession
    token: str


@dataclass(frozen=True)
class ClientContext:
    ip_address: str
    user_agent: str | None


def _now() -> datetime:
    return datetime.now(UTC)


class AuthService:
    def __init__(self, db: Session, limiter: RateLimiter, settings: Settings) -> None:
        self.db = db
        self.limiter = limiter
        self.settings = settings
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)

    # --- Registration and sign-in --------------------------------------------

    def register(
        self, *, email: str, password: str, full_name: str, client: ClientContext
    ) -> IssuedSession:
        self.limiter.hit(
            "register:ip",
            client.ip_address,
            limit=self.settings.registrations_per_ip,
            window_seconds=self.settings.registration_window_seconds,
        )
        email = email.strip().lower()
        if self.users.email_exists(email):
            raise ConflictError("An account with this email address already exists.")

        user = User(email=email, password_hash=hash_password(password), full_name=full_name)
        try:
            self.users.add(user)
            issued = self._issue_session(user, client)
            self.db.commit()
        except IntegrityError as exc:
            # Lost a race with a concurrent registration for the same email.
            self.db.rollback()
            raise ConflictError("An account with this email address already exists.") from exc
        logger.info("user registered", extra={"user_id": str(user.id)})
        return issued

    def login(
        self,
        *,
        email: str,
        password: str,
        client: ClientContext,
        previous_token: str | None = None,
    ) -> IssuedSession:
        email = email.strip().lower()
        window = self.settings.login_window_seconds
        self.limiter.hit(
            "login:ip",
            client.ip_address,
            limit=self.settings.login_attempts_per_ip,
            window_seconds=window,
        )
        # Locked accounts are refused before the password is checked, so a
        # correct guess during a lockout reveals nothing.
        self.limiter.check("login:account", email, limit=self.settings.login_failures_per_account)

        user = self.users.get_by_email(email)
        password_ok = verify_password(user.password_hash if user else None, password)
        if user is None or not password_ok or not user.is_active:
            self.limiter.hit(
                "login:account",
                email,
                limit=self.settings.login_failures_per_account,
                window_seconds=window,
            )
            logger.info("login failed", extra={"reason": "invalid_credentials"})
            raise AuthenticationError(INVALID_LOGIN_MESSAGE)

        self.limiter.reset("login:account", email)
        now = _now()
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        if previous_token:
            # Signing in again replaces, rather than adds to, this browser's session.
            self.sessions.revoke_by_token_hash(hash_token(previous_token), now=now)
        user.last_login_at = now
        issued = self._issue_session(user, client)
        self.db.commit()
        logger.info("login succeeded", extra={"user_id": str(user.id)})
        return issued

    # --- Session lifecycle -----------------------------------------------------

    def resolve_session(self, token: str) -> UserSession | None:
        now = _now()
        idle_cutoff = now - timedelta(minutes=self.settings.session_idle_timeout_minutes)
        session = self.sessions.get_active_by_token_hash(
            hash_token(token), now=now, idle_cutoff=idle_cutoff
        )
        if session is None:
            return None
        if self._exceeds_staff_limits(session, now) and self._is_staff(session.user):
            session.revoked_at = now
            self.db.commit()
            logger.info("staff session expired", extra={"user_id": str(session.user_id)})
            return None
        touch_after = session.last_seen_at + timedelta(
            seconds=self.settings.session_touch_interval_seconds
        )
        if now >= touch_after:
            session.last_seen_at = now
            self.db.commit()
        return session

    def logout(self, session: UserSession) -> None:
        session.revoked_at = _now()
        self.db.commit()
        logger.info("logout", extra={"user_id": str(session.user_id)})

    # --- Account changes -------------------------------------------------------

    def update_profile(self, user: User, *, full_name: str) -> User:
        user.full_name = full_name
        self.db.commit()
        return user

    def change_password(
        self, session: UserSession, *, current_password: str, new_password: str
    ) -> None:
        user = session.user
        self.limiter.hit(
            "password_change:user",
            str(user.id),
            limit=self.settings.login_failures_per_account,
            window_seconds=self.settings.login_window_seconds,
        )
        if not verify_password(user.password_hash, current_password):
            raise InvalidCurrentPasswordError("Your current password is incorrect.")

        now = _now()
        user.password_hash = hash_password(new_password)
        user.password_changed_at = now
        # Anyone else holding a session for this account is signed out.
        self.sessions.revoke_all_for_user(user.id, now=now, except_session_id=session.id)
        record_audit(
            self.db,
            action="user.password_changed",
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
        )
        self.db.commit()
        self.limiter.reset("password_change:user", str(user.id))
        logger.info("password changed", extra={"user_id": str(user.id)})

    # --- Internals ---------------------------------------------------------------

    def _exceeds_staff_limits(self, session: UserSession, now: datetime) -> bool:
        idle = timedelta(minutes=self.settings.staff_session_idle_timeout_minutes)
        lifetime = timedelta(minutes=self.settings.staff_session_absolute_timeout_minutes)
        return session.last_seen_at <= now - idle or session.created_at <= now - lifetime

    def _is_staff(self, user: User) -> bool:
        """Platform admin, or an active member of any active council.

        Only evaluated for sessions that are past the staff limits, so the
        common request path never pays for this query.
        """
        if user.is_platform_admin:
            return True
        # council_memberships is under RLS: act as the user to read their own rows.
        bind_rls_user(self.db, user.id)
        return bool(
            self.db.scalar(
                select(
                    exists().where(
                        CouncilMembership.user_id == user.id,
                        CouncilMembership.revoked_at.is_(None),
                        CouncilMembership.council_id == Council.id,
                        Council.is_active.is_(True),
                    )
                )
            )
        )

    def _issue_session(self, user: User, client: ClientContext) -> IssuedSession:
        now = _now()
        token = generate_token()
        user_agent = (client.user_agent or "")[:USER_AGENT_MAX_LENGTH] or None
        session = self.sessions.add(
            UserSession(
                user=user,
                token_hash=hash_token(token),
                csrf_token=generate_token(),
                last_seen_at=now,
                expires_at=now + timedelta(minutes=self.settings.session_absolute_timeout_minutes),
                user_agent=user_agent,
            )
        )
        return IssuedSession(session=session, token=token)


def purge_stale_sessions(db: Session, settings: Settings) -> int:
    """Delete sessions that can no longer be used. Keeps a day of history."""
    now = _now()
    grace = timedelta(days=1)
    deleted = SessionRepository(db).delete_stale(
        expired_before=now - grace,
        idle_before=now - timedelta(minutes=settings.session_idle_timeout_minutes) - grace,
    )
    db.commit()
    return deleted
