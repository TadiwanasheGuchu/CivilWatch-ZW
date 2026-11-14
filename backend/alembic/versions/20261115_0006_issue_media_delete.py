"""Let reporters remove a photo while their report is still SUBMITTED.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("GRANT DELETE ON issue_media TO civicwatch_app")
    op.execute(
        """
        CREATE POLICY issue_media_delete ON issue_media FOR DELETE
        USING (
            EXISTS (
                SELECT 1 FROM issues i
                WHERE i.id = issue_id
                  AND i.reporter_id = app_current_user_id()
                  AND i.status = 'SUBMITTED'
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS issue_media_delete ON issue_media")
    op.execute("REVOKE DELETE ON issue_media FROM civicwatch_app")
