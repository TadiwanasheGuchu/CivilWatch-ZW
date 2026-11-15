"""Email copies of notifications, sent by the worker over SMTP."""

import socket
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from email import message_from_bytes
from email.message import EmailMessage

import pytest
from aiosmtpd.controller import Controller
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from app.core.config import Settings, get_settings
from app.core.database import get_session_factory, get_worker_session_factory
from app.services.email_delivery import SmtpSender, deliver_pending
from tests.operations_helpers import build_council, move


class _Inbox:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def handle_DATA(self, server, session, envelope):  # noqa: N802 (aiosmtpd hook name)
        self.messages.append(message_from_bytes(envelope.content))  # type: ignore[arg-type]
        return "250 OK"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def smtp() -> Iterator[tuple[_Inbox, int]]:
    inbox = _Inbox()
    port = _free_port()
    controller = Controller(inbox, hostname="127.0.0.1", port=port)
    controller.start()
    try:
        yield inbox, port
    finally:
        controller.stop()


def _settings(port: int, **overrides) -> Settings:
    return get_settings().model_copy(
        update={
            "smtp_host": "127.0.0.1",
            "smtp_port": port,
            "smtp_starttls": False,
            "email_from": "CivicWatch <noreply@civicwatch.test>",
            "public_web_url": "https://civicwatch.test",
            **overrides,
        }
    )


def _worker():
    factory = get_worker_session_factory()
    assert factory is not None, "set CIVICWATCH_WORKER_DATABASE_URL for these tests"
    return factory


@pytest.fixture
def c(make_client):
    council = build_council(make_client)
    move(council["verifier"], council["issue_url"], "UNDER_REVIEW")
    return council


def _pending(owner_engine: Engine) -> list[tuple]:
    with owner_engine.connect() as connection:
        return connection.execute(
            text("SELECT email_sent_at, email_attempts, email_last_error FROM notifications")
        ).all()


def test_notifications_are_emailed_once_with_a_link(c, smtp, owner_engine) -> None:
    inbox, port = smtp
    settings = _settings(port)
    report = deliver_pending(_worker(), settings, SmtpSender(settings))
    assert (report.sent, report.failed) == (1, 0)
    [message] = inbox.messages
    ref = c["issue"]["reference"]
    assert message["Subject"] == f"CivicWatch: Your report {ref} is being reviewed"
    assert message["To"] == c["resident"].session["user"]["email"]
    body = message.get_payload(decode=True).decode()
    assert f"https://civicwatch.test/reports/{c['issue']['id']}" in body
    assert "https://civicwatch.test/account" in body
    [(sent_at, attempts, error)] = _pending(owner_engine)
    assert sent_at is not None and attempts == 1 and error is None

    # Already sent: nothing more goes out.
    assert deliver_pending(_worker(), settings, SmtpSender(settings)).sent == 0
    assert len(inbox.messages) == 1


def test_residents_can_turn_emails_off(c, smtp) -> None:
    inbox, port = smtp
    response = c["resident"].patch("/api/v1/users/me", {"email_notifications": False})
    assert response.status_code == 200
    assert response.json()["email_notifications"] is False
    assert c["resident"].get("/api/v1/auth/session").json()["user"]["email_notifications"] is False
    settings = _settings(port)
    assert deliver_pending(_worker(), settings, SmtpSender(settings)).sent == 0
    assert inbox.messages == []
    # The in-app notification is still there.
    assert c["resident"].get("/api/v1/notifications/unread-count").json()["unread"] == 1


def test_profile_update_needs_something_to_change(c) -> None:
    assert c["resident"].patch("/api/v1/users/me", {}).status_code == 422
    renamed = c["resident"].patch("/api/v1/users/me", {"full_name": "  Chipo  M  "})
    assert renamed.status_code == 200
    assert renamed.json()["email_notifications"] is True


def test_failures_are_retried_up_to_the_limit(c, owner_engine) -> None:
    unused_port = _free_port()
    settings = _settings(unused_port, email_max_attempts=2)
    for expected_attempts in (1, 2):
        report = deliver_pending(_worker(), settings, SmtpSender(settings))
        assert (report.sent, report.failed) == (0, 1)
        [(sent_at, attempts, error)] = _pending(owner_engine)
        assert sent_at is None and attempts == expected_attempts and error
    # Given up after the limit.
    assert deliver_pending(_worker(), settings, SmtpSender(settings)).failed == 0


def test_old_notifications_are_not_emailed(c, smtp, owner_engine) -> None:
    inbox, port = smtp
    with owner_engine.begin() as connection:
        connection.execute(
            text("UPDATE notifications SET created_at = :t"),
            {"t": datetime.now(UTC) - timedelta(hours=49)},
        )
    settings = _settings(port)
    assert deliver_pending(_worker(), settings, SmtpSender(settings)).sent == 0
    assert inbox.messages == []


def test_inactive_accounts_are_not_emailed(c, smtp, owner_engine) -> None:
    inbox, port = smtp
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE users SET is_active = false"))
    settings = _settings(port)
    assert deliver_pending(_worker(), settings, SmtpSender(settings)).sent == 0


def test_without_smtp_the_task_does_nothing(c) -> None:
    from app.workers.tasks import deliver_notification_emails_task

    assert get_settings().smtp_host is None
    assert deliver_notification_emails_task() == {"sent": 0, "failed": 0}


# --- Database roles -------------------------------------------------------------------


def test_worker_role_cannot_read_reports_or_passwords(c) -> None:
    with _worker()() as db:
        for sql in ("SELECT title FROM issues", "SELECT password_hash FROM users"):
            with pytest.raises(DBAPIError, match="permission denied"):
                db.execute(text(sql))
            db.rollback()
        with pytest.raises(DBAPIError, match="permission denied"):
            db.execute(text("UPDATE notifications SET title = 'x'"))


def test_api_role_cannot_mark_emails_sent(c) -> None:
    with get_session_factory()() as db, pytest.raises(DBAPIError, match="permission denied"):
        db.execute(text("UPDATE notifications SET email_sent_at = now()"))
