"""Notifications and resolution feedback, with RLS.

- notifications: each person reads and marks only their own; a notification
  can only be created about a report the creating user can see.
- resolution_feedback: the reporter answers once, after resolution; readable
  by the reporter and that council's staff only.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-15 00:42:13.947978
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('status_changed', 'information_requested', 'information_provided', 'work_assigned', 'feedback_not_fixed')",
            name=op.f("ck_notifications_kind_valid"),
        ),
        sa.CheckConstraint(
            "link LIKE '/%%' AND link NOT LIKE '//%%'", name=op.f("ck_notifications_link_relative")
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            name=op.f("fk_notifications_issue_id_issues"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notifications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(
        "ix_notifications_unread",
        "notifications",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.create_index(
        "ix_notifications_user_id_created_at",
        "notifications",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "resolution_feedback",
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("council_id", sa.UUID(), nullable=False),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("fixed", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "comment IS NULL OR char_length(comment) <= 1000",
            name=op.f("ck_resolution_feedback_comment_length"),
        ),
        sa.ForeignKeyConstraint(
            ["council_id"],
            ["councils.id"],
            name=op.f("fk_resolution_feedback_council_id_councils"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            name=op.f("fk_resolution_feedback_issue_id_issues"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
            name=op.f("fk_resolution_feedback_reporter_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resolution_feedback")),
        sa.UniqueConstraint("issue_id", name=op.f("uq_resolution_feedback_issue_id")),
    )
    op.create_index(
        "ix_resolution_feedback_council_id", "resolution_feedback", ["council_id"], unique=False
    )

    _grants_and_rls()


def downgrade() -> None:
    for policy, table in (
        ("resolution_feedback_insert", "resolution_feedback"),
        ("resolution_feedback_select", "resolution_feedback"),
        ("notifications_insert", "notifications"),
        ("notifications_update", "notifications"),
        ("notifications_select", "notifications"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.drop_index("ix_resolution_feedback_council_id", table_name="resolution_feedback")
    op.drop_table("resolution_feedback")
    op.drop_index("ix_notifications_user_id_created_at", table_name="notifications")
    op.drop_index(
        "ix_notifications_unread",
        table_name="notifications",
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.drop_table("notifications")


APP_ROLE = "civicwatch_app"


def _grants_and_rls() -> None:
    op.execute(f"GRANT SELECT, INSERT ON notifications TO {APP_ROLE}")
    op.execute(f"GRANT UPDATE (read_at) ON notifications TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON resolution_feedback TO {APP_ROLE}")

    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY notifications_select ON notifications FOR SELECT "
        "USING (user_id = app_current_user_id())"
    )
    op.execute(
        "CREATE POLICY notifications_update ON notifications FOR UPDATE "
        "USING (user_id = app_current_user_id()) WITH CHECK (user_id = app_current_user_id())"
    )
    # The subquery runs under the creator's own report policies.
    op.execute(
        """
        CREATE POLICY notifications_insert ON notifications FOR INSERT
        WITH CHECK (
            app_current_user_id() IS NOT NULL
            AND issue_id IS NOT NULL
            AND EXISTS (SELECT 1 FROM issues i WHERE i.id = issue_id)
        )
        """
    )

    op.execute("ALTER TABLE resolution_feedback ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY resolution_feedback_select ON resolution_feedback FOR SELECT
        USING (
            reporter_id = app_current_user_id()
            OR council_id IN (SELECT app_member_council_ids())
        )
        """
    )
    op.execute(
        """
        CREATE POLICY resolution_feedback_insert ON resolution_feedback FOR INSERT
        WITH CHECK (
            reporter_id = app_current_user_id()
            AND EXISTS (
                SELECT 1 FROM issues i
                WHERE i.id = issue_id
                  AND i.reporter_id = app_current_user_id()
                  AND i.council_id = resolution_feedback.council_id
                  AND i.status IN ('RESOLVED', 'CLOSED')
            )
        )
        """
    )
