"""Email copies of notifications (the outbox pattern).

Runs in the background worker as the `civicwatch_worker` database role.
Each notification is claimed with FOR UPDATE SKIP LOCKED, so several
workers never send the same email, and each send is committed on its own.
"""

import logging
import smtplib
import ssl
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.engagement import Notification
from app.models.identity import User

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class SmtpSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: EmailMessage) -> None:
        s = self.settings
        context = ssl.create_default_context()
        smtp: smtplib.SMTP
        if s.smtp_use_ssl:
            smtp = smtplib.SMTP_SSL(s.smtp_host or "", s.smtp_port, timeout=15, context=context)
        else:
            smtp = smtplib.SMTP(s.smtp_host or "", s.smtp_port, timeout=15)
        with smtp:
            if s.smtp_starttls and not s.smtp_use_ssl:
                smtp.starttls(context=context)
            if s.smtp_username and s.smtp_password:
                smtp.login(s.smtp_username, s.smtp_password.get_secret_value())
            smtp.send_message(message)


@dataclass(frozen=True)
class DeliveryReport:
    sent: int
    failed: int


def build_message(
    settings: Settings, *, to: str, name: str, title: str, body: str | None, link: str
) -> EmailMessage:
    base = settings.public_web_url.rstrip("/")
    message = EmailMessage()
    message["Subject"] = f"CivicWatch: {title}"
    message["From"] = settings.email_from or ""
    message["To"] = to
    lines = [f"Hello {name},", "", title]
    if body:
        lines += ["", body]
    lines += [
        "",
        f"Open it in CivicWatch: {base}{link}",
        "",
        "--",
        "You receive these emails because you use CivicWatch ZW.",
        f"You can turn them off in your account: {base}/account",
    ]
    message.set_content("\n".join(lines))
    return message


def deliver_pending(
    session_factory: Callable[[], Session], settings: Settings, sender: EmailSender
) -> DeliveryReport:
    """Send up to one batch of pending notification emails."""
    sent = failed = 0
    tried: list[uuid.UUID] = []  # at most one attempt per notification per run
    cutoff = datetime.now(UTC) - timedelta(hours=settings.email_max_age_hours)
    for _ in range(settings.email_batch_size):
        with session_factory() as db:
            row = db.execute(
                select(
                    Notification.id,
                    Notification.title,
                    Notification.body,
                    Notification.link,
                    Notification.email_attempts,
                    User.email,
                    User.full_name,
                )
                .join(User, User.id == Notification.user_id)
                .where(
                    Notification.email_sent_at.is_(None),
                    Notification.email_attempts < settings.email_max_attempts,
                    Notification.created_at >= cutoff,
                    User.is_active.is_(True),
                    User.email_notifications.is_(True),
                    Notification.id.not_in(tried),
                )
                .order_by(Notification.created_at)
                .limit(1)
                .with_for_update(of=Notification, skip_locked=True)
            ).first()
            if row is None:
                break
            tried.append(row.id)
            message = build_message(
                settings,
                to=row.email,
                name=row.full_name,
                title=row.title,
                body=row.body,
                link=row.link,
            )
            try:
                sender.send(message)
            except (smtplib.SMTPException, OSError) as exc:
                failed += 1
                logger.warning("notification email failed", extra={"notification_id": str(row.id)})
                values = {
                    "email_attempts": row.email_attempts + 1,
                    "email_last_error": str(exc)[:300],
                }
            else:
                sent += 1
                values = {
                    "email_attempts": row.email_attempts + 1,
                    "email_sent_at": datetime.now(UTC),
                }
            db.execute(update(Notification).where(Notification.id == row.id).values(**values))
            db.commit()
    if sent or failed:
        logger.info("notification emails processed", extra={"sent": sent, "failed": failed})
    return DeliveryReport(sent=sent, failed=failed)
