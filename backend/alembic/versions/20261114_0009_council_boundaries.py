"""Council boundaries: where each boundary came from, and when it changed.

Boundaries labelled "sample" are illustrative shapes for demonstration and
are always shown as such; "official" ones come from the council.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-14 20:11:36.000970
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("councils", sa.Column("boundary_source", sa.String(length=16), nullable=True))
    op.add_column(
        "councils", sa.Column("boundary_updated_at", sa.DateTime(timezone=True), nullable=True)
    )

    # Boundaries loaded before this migration are treated as official.
    op.execute("UPDATE councils SET boundary_source = 'official' WHERE boundary IS NOT NULL")
    op.create_check_constraint(
        "boundary_source_matches", "councils", "(boundary IS NULL) = (boundary_source IS NULL)"
    )
    op.create_check_constraint(
        "boundary_source_valid",
        "councils",
        "boundary_source IS NULL OR boundary_source IN ('sample', 'official')",
    )


def downgrade() -> None:
    op.drop_constraint("boundary_source_valid", "councils", type_="check")
    op.drop_constraint("boundary_source_matches", "councils", type_="check")
    op.drop_column("councils", "boundary_updated_at")
    op.drop_column("councils", "boundary_source")
