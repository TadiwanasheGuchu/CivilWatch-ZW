"""Email notifications: delivery columns, a per-user opt-out, and the worker role.

The background worker connects as `civicwatch_worker`, which can only read
notifications and the recipient's name, email and preferences, and record
delivery results. It cannot read reports or anything else. Infrastructure
creates it with LOGIN and a password; this migration creates it NOLOGIN if
missing so the grants always apply.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-15 01:20:37.973361
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications", sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "notifications",
        sa.Column("email_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "notifications", sa.Column("email_last_error", sa.String(length=300), nullable=True)
    )
    op.create_index(
        "ix_notifications_email_pending",
        "notifications",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("email_sent_at IS NULL"),
    )
    op.add_column(
        "users",
        sa.Column("email_notifications", sa.Boolean(), server_default="true", nullable=False),
    )

    _worker_role()


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS notifications_worker_update ON notifications")
    op.execute("DROP POLICY IF EXISTS notifications_worker_select ON notifications")
    op.execute(f"REVOKE ALL ON notifications, users FROM {WORKER_ROLE}")
    op.drop_column("users", "email_notifications")
    op.drop_index(
        "ix_notifications_email_pending",
        table_name="notifications",
        postgresql_where=sa.text("email_sent_at IS NULL"),
    )
    op.drop_column("notifications", "email_last_error")
    op.drop_column("notifications", "email_attempts")
    op.drop_column("notifications", "email_sent_at")


WORKER_ROLE = "civicwatch_worker"


def _worker_role() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{WORKER_ROLE}') THEN
                CREATE ROLE {WORKER_ROLE} NOLOGIN;
            END IF;
        END
        $$
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {WORKER_ROLE}")
    op.execute(
        f"GRANT SELECT (id, email, full_name, is_active, email_notifications) ON users TO {WORKER_ROLE}"
    )
    op.execute(
        f"GRANT SELECT (id, user_id, kind, title, body, link, created_at, email_sent_at, "
        f"email_attempts) ON notifications TO {WORKER_ROLE}"
    )
    op.execute(
        f"GRANT UPDATE (email_sent_at, email_attempts, email_last_error) ON notifications TO {WORKER_ROLE}"
    )
    # The worker sees every user's notifications; nobody else gains anything.
    op.execute(
        f"CREATE POLICY notifications_worker_select ON notifications FOR SELECT TO {WORKER_ROLE} USING (true)"
    )
    op.execute(
        f"CREATE POLICY notifications_worker_update ON notifications FOR UPDATE TO {WORKER_ROLE} "
        "USING (true) WITH CHECK (true)"
    )
