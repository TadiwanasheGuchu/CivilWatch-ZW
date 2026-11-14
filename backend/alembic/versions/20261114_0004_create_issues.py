"""Create issue categories, issues and status history, with RLS.

Visibility rules enforced by the database for the API role:
- a reporter sees their own reports;
- active staff of a council see that council's reports;
- everyone (including anonymous visitors) sees PUBLIC reports once a
  council has verified them (status VERIFIED or later, never REJECTED or
  DUPLICATE);
- status history is visible exactly when its report is.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-14 10:50:28.354229
"""

import uuid
from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issue_categories",
        sa.Column("code", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_issue_categories")),
        sa.UniqueConstraint("code", name=op.f("uq_issue_categories_code")),
    )
    op.create_table(
        "issues",
        sa.Column("reference_number", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("council_id", sa.UUID(), nullable=False),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("location_description", sa.String(length=200), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('SUBMITTED', 'UNDER_REVIEW', 'NEEDS_INFORMATION', 'VERIFIED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED', 'DUPLICATE', 'CLOSED')",
            name=op.f("ck_issues_status_valid"),
        ),
        sa.CheckConstraint(
            "visibility IN ('PUBLIC', 'PRIVATE')", name=op.f("ck_issues_visibility_valid")
        ),
        sa.CheckConstraint(
            "char_length(description) BETWEEN 10 AND 2000",
            name=op.f("ck_issues_description_length"),
        ),
        sa.CheckConstraint(
            "char_length(title) BETWEEN 5 AND 120", name=op.f("ck_issues_title_length")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["issue_categories.id"],
            name=op.f("fk_issues_category_id_issue_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["council_id"],
            ["councils.id"],
            name=op.f("fk_issues_council_id_councils"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
            name=op.f("fk_issues_reporter_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_issues")),
        sa.UniqueConstraint("reference_number", name=op.f("uq_issues_reference_number")),
    )
    op.create_index("ix_issues_council_id_status", "issues", ["council_id", "status"], unique=False)
    op.create_index(
        "ix_issues_location", "issues", ["location"], unique=False, postgresql_using="gist"
    )
    op.create_index(
        "ix_issues_published_created_at",
        "issues",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text(
            "visibility = 'PUBLIC' AND status IN ('ASSIGNED', 'CLOSED', 'IN_PROGRESS', 'RESOLVED', 'VERIFIED')"
        ),
    )
    op.create_index(
        "ix_issues_reporter_id_created_at", "issues", ["reporter_id", "created_at"], unique=False
    )
    op.create_table(
        "issue_status_history",
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("changed_by_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "to_status IN ('SUBMITTED', 'UNDER_REVIEW', 'NEEDS_INFORMATION', 'VERIFIED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED', 'DUPLICATE', 'CLOSED')",
            name=op.f("ck_issue_status_history_to_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
            name=op.f("fk_issue_status_history_changed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            name=op.f("fk_issue_status_history_issue_id_issues"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_issue_status_history")),
    )
    op.create_index(
        "ix_issue_status_history_issue_id_created_at",
        "issue_status_history",
        ["issue_id", "created_at"],
        unique=False,
    )

    _seed_categories()
    _grants_and_rls()


def downgrade() -> None:
    _drop_rls()
    op.drop_index("ix_issue_status_history_issue_id_created_at", table_name="issue_status_history")
    op.drop_table("issue_status_history")
    op.drop_index("ix_issues_reporter_id_created_at", table_name="issues")
    op.drop_index(
        "ix_issues_published_created_at",
        table_name="issues",
        postgresql_where=sa.text(
            "visibility = 'PUBLIC' AND status IN ('ASSIGNED', 'CLOSED', 'IN_PROGRESS', 'RESOLVED', 'VERIFIED')"
        ),
    )
    op.drop_index("ix_issues_location", table_name="issues", postgresql_using="gist")
    op.drop_index("ix_issues_council_id_status", table_name="issues")
    op.drop_table("issues")
    op.drop_table("issue_categories")


APP_ROLE = "civicwatch_app"
PUBLISHED = "('VERIFIED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')"

# Platform-wide categories from the product requirements (CLAUDE.md section 8).
CATEGORIES = [
    ("roads", "Roads and potholes", "Potholes, damaged road surfaces and road markings.", 10),
    ("streetlights", "Streetlights", "Broken, flickering or missing streetlights.", 20),
    ("drainage", "Drainage and flooding", "Blocked drains, culverts and flooding.", 30),
    ("water", "Water infrastructure", "Burst pipes, leaks and damaged water points.", 40),
    ("waste", "Waste management", "Uncollected refuse and illegal dumping.", 50),
    ("public-buildings", "Public buildings", "Damage to council buildings and facilities.", 60),
    ("bridges-pavements", "Bridges and pavements", "Damaged bridges, footpaths and pavements.", 70),
    ("other", "Other infrastructure", "Any other public infrastructure problem.", 80),
]


def _seed_categories() -> None:
    table = sa.table(
        "issue_categories",
        sa.column("id", sa.UUID()),
        sa.column("code", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": uuid.uuid4(),
                "code": code,
                "name": name,
                "description": desc,
                "sort_order": order,
            }
            for code, name, desc, order in CATEGORIES
        ],
    )


def _grants_and_rls() -> None:
    op.execute(f"GRANT SELECT ON issue_categories TO {APP_ROLE}")
    # Residents create reports; council staff update them from Milestone 3,
    # which will add UPDATE together with the workflow rules.
    op.execute(f"GRANT SELECT, INSERT ON issues TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON issue_status_history TO {APP_ROLE}")

    op.execute("ALTER TABLE issues ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY issues_select ON issues FOR SELECT
        USING (
            reporter_id = app_current_user_id()
            OR council_id IN (SELECT app_member_council_ids())
            OR (visibility = 'PUBLIC' AND status IN {PUBLISHED})
        )
        """
    )
    op.execute(
        """
        CREATE POLICY issues_insert ON issues FOR INSERT
        WITH CHECK (reporter_id = app_current_user_id() AND status = 'SUBMITTED')
        """
    )

    op.execute("ALTER TABLE issue_status_history ENABLE ROW LEVEL SECURITY")
    # The subquery runs under the issues policies, so history follows the
    # visibility of its report.
    op.execute(
        """
        CREATE POLICY issue_status_history_select ON issue_status_history FOR SELECT
        USING (EXISTS (SELECT 1 FROM issues i WHERE i.id = issue_id))
        """
    )
    op.execute(
        """
        CREATE POLICY issue_status_history_insert ON issue_status_history FOR INSERT
        WITH CHECK (
            changed_by_user_id = app_current_user_id()
            AND EXISTS (SELECT 1 FROM issues i WHERE i.id = issue_id)
        )
        """
    )


def _drop_rls() -> None:
    for policy, table in (
        ("issue_status_history_insert", "issue_status_history"),
        ("issue_status_history_select", "issue_status_history"),
        ("issues_insert", "issues"),
        ("issues_select", "issues"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
