"""Repair evidence photos: staff doing the work may add photos to a report.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPORTER_STATUSES = "('SUBMITTED', 'NEEDS_INFORMATION')"


def _reporter_policies(kind_clause: str) -> None:
    op.execute("DROP POLICY IF EXISTS issue_media_insert ON issue_media")
    op.execute("DROP POLICY IF EXISTS issue_media_delete ON issue_media")
    op.execute(
        f"""
        CREATE POLICY issue_media_insert ON issue_media FOR INSERT
        WITH CHECK (
            {kind_clause}
            uploaded_by_user_id = app_current_user_id()
            AND EXISTS (
                SELECT 1 FROM issues i
                WHERE i.id = issue_id AND i.reporter_id = app_current_user_id()
                  AND i.status IN {REPORTER_STATUSES}
            )
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY issue_media_delete ON issue_media FOR DELETE
        USING (
            {kind_clause}
            EXISTS (
                SELECT 1 FROM issues i
                WHERE i.id = issue_id AND i.reporter_id = app_current_user_id()
                  AND i.status IN {REPORTER_STATUSES}
            )
        )
        """
    )


def upgrade() -> None:
    op.add_column(
        "issue_media",
        sa.Column("kind", sa.String(length=16), server_default="report", nullable=False),
    )
    op.create_check_constraint("kind_valid", "issue_media", "kind IN ('report', 'repair')")
    # Reporters only ever add or remove their own report photos, never repair evidence.
    _reporter_policies("kind = 'report' AND")
    op.execute(
        """
        CREATE POLICY issue_media_insert_repair ON issue_media FOR INSERT
        WITH CHECK (
            kind = 'repair'
            AND uploaded_by_user_id = app_current_user_id()
            AND EXISTS (
                SELECT 1 FROM issues i
                WHERE i.id = issue_id
                  AND i.council_id IN (SELECT app_member_council_ids())
                  AND i.status IN ('IN_PROGRESS', 'RESOLVED')
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS issue_media_insert_repair ON issue_media")
    _reporter_policies("")
    op.drop_constraint("kind_valid", "issue_media", type_="check")
    op.drop_column("issue_media", "kind")
