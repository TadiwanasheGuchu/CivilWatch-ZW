"""Create issue_media for sanitised report photos, with RLS.

Photos are visible exactly when their report is. Only the report's
reporter may add photos, and only while the report is still SUBMITTED.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-14 10:59:31.621286
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issue_media",
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.UUID(), nullable=True),
        sa.Column("display_key", sa.String(length=255), nullable=False),
        sa.Column("thumbnail_key", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "content_type = 'image/jpeg'", name=op.f("ck_issue_media_content_type_valid")
        ),
        sa.CheckConstraint(
            "width > 0 AND height > 0 AND byte_size > 0",
            name=op.f("ck_issue_media_dimensions_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            name=op.f("fk_issue_media_issue_id_issues"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_issue_media_uploaded_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_issue_media")),
        sa.UniqueConstraint("display_key", name=op.f("uq_issue_media_display_key")),
        sa.UniqueConstraint("thumbnail_key", name=op.f("uq_issue_media_thumbnail_key")),
    )
    op.create_index(
        "ix_issue_media_issue_id_created_at",
        "issue_media",
        ["issue_id", "created_at"],
        unique=False,
    )

    op.execute("GRANT SELECT, INSERT ON issue_media TO civicwatch_app")
    op.execute("ALTER TABLE issue_media ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY issue_media_select ON issue_media FOR SELECT
        USING (EXISTS (SELECT 1 FROM issues i WHERE i.id = issue_id))
        """
    )
    op.execute(
        """
        CREATE POLICY issue_media_insert ON issue_media FOR INSERT
        WITH CHECK (
            uploaded_by_user_id = app_current_user_id()
            AND EXISTS (
                SELECT 1 FROM issues i
                WHERE i.id = issue_id
                  AND i.reporter_id = app_current_user_id()
                  AND i.status = 'SUBMITTED'
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS issue_media_insert ON issue_media")
    op.execute("DROP POLICY IF EXISTS issue_media_select ON issue_media")
    op.drop_index("ix_issue_media_issue_id_created_at", table_name="issue_media")
    op.drop_table("issue_media")
