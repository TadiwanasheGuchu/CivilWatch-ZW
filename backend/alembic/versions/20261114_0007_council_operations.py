"""Council operations: departments, assignments, staff notes, workflow updates.

- departments per council; a membership may belong to one department
  (same-council integrity enforced by composite foreign keys);
- issue_assignments (history kept; one current assignment per report);
- issue_updates: staff-only working notes, append-only;
- issue_status_history.note: a message to the reporter;
- the API role may now UPDATE a report's status, but only as staff of its
  council, or as its reporter answering a request for information;
- reporters may add or remove photos while information is requested.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-14 19:02:44.462923
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Composite foreign keys below reference issues(id, council_id).
    op.add_column("issues", sa.Column("duplicate_of_issue_id", sa.UUID(), nullable=True))
    op.create_unique_constraint("uq_issues_id_council_id", "issues", ["id", "council_id"])
    op.create_foreign_key(
        op.f("fk_issues_duplicate_of_issue_id_issues"),
        "issues",
        "issues",
        ["duplicate_of_issue_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "departments",
        sa.Column("council_id", sa.UUID(), nullable=False),
        sa.Column("name", postgresql.CITEXT(), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
            "char_length(name) BETWEEN 2 AND 80", name=op.f("ck_departments_name_length")
        ),
        sa.ForeignKeyConstraint(
            ["council_id"],
            ["councils.id"],
            name=op.f("fk_departments_council_id_councils"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("council_id", "name", name="uq_departments_council_id_name"),
        sa.UniqueConstraint("id", "council_id", name="uq_departments_id_council_id"),
    )
    op.create_table(
        "issue_assignments",
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("council_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("assignee_user_id", sa.UUID(), nullable=True),
        sa.Column("assigned_by_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"],
            ["users.id"],
            name=op.f("fk_issue_assignments_assigned_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assignee_user_id"],
            ["users.id"],
            name=op.f("fk_issue_assignments_assignee_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["department_id", "council_id"],
            ["departments.id", "departments.council_id"],
            name="fk_issue_assignments_department_council",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id", "council_id"],
            ["issues.id", "issues.council_id"],
            name="fk_issue_assignments_issue_council",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_issue_assignments")),
    )
    op.create_index(
        "ix_issue_assignments_assignee_user_id",
        "issue_assignments",
        ["assignee_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_issue_assignments_department_id", "issue_assignments", ["department_id"], unique=False
    )
    op.create_index(
        "uq_issue_assignments_current",
        "issue_assignments",
        ["issue_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    op.create_table(
        "issue_updates",
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("council_id", sa.UUID(), nullable=False),
        sa.Column("author_user_id", sa.UUID(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "char_length(body) BETWEEN 1 AND 2000", name=op.f("ck_issue_updates_body_length")
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            name=op.f("fk_issue_updates_author_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id", "council_id"],
            ["issues.id", "issues.council_id"],
            name="fk_issue_updates_issue_council",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_issue_updates")),
    )
    op.create_index(
        "ix_issue_updates_issue_id_created_at",
        "issue_updates",
        ["issue_id", "created_at"],
        unique=False,
    )
    op.add_column("council_memberships", sa.Column("department_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_council_memberships_department_council",
        "council_memberships",
        "departments",
        ["department_id", "council_id"],
        ["id", "council_id"],
        ondelete="RESTRICT",
    )
    op.add_column("issue_status_history", sa.Column("note", sa.Text(), nullable=True))

    _grants_and_rls()


def downgrade() -> None:
    _drop_rls()
    op.drop_column("issue_status_history", "note")
    op.drop_constraint(
        "fk_council_memberships_department_council", "council_memberships", type_="foreignkey"
    )
    op.drop_column("council_memberships", "department_id")
    op.drop_index("ix_issue_updates_issue_id_created_at", table_name="issue_updates")
    op.drop_table("issue_updates")
    op.drop_index(
        "uq_issue_assignments_current",
        table_name="issue_assignments",
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    op.drop_index("ix_issue_assignments_department_id", table_name="issue_assignments")
    op.drop_index("ix_issue_assignments_assignee_user_id", table_name="issue_assignments")
    op.drop_table("issue_assignments")
    op.drop_table("departments")
    op.drop_constraint(op.f("fk_issues_duplicate_of_issue_id_issues"), "issues", type_="foreignkey")
    op.drop_constraint("uq_issues_id_council_id", "issues", type_="unique")
    op.drop_column("issues", "duplicate_of_issue_id")


APP_ROLE = "civicwatch_app"
MEMBER = "council_id IN (SELECT app_member_council_ids())"
ADMIN = "council_id IN (SELECT app_admin_council_ids())"
OPEN_FOR_REPORTER = "('SUBMITTED', 'NEEDS_INFORMATION')"


def _media_policies(statuses: str) -> None:
    op.execute("DROP POLICY IF EXISTS issue_media_insert ON issue_media")
    op.execute("DROP POLICY IF EXISTS issue_media_delete ON issue_media")
    op.execute(
        f"""
        CREATE POLICY issue_media_insert ON issue_media FOR INSERT
        WITH CHECK (
            uploaded_by_user_id = app_current_user_id()
            AND EXISTS (
                SELECT 1 FROM issues i
                WHERE i.id = issue_id AND i.reporter_id = app_current_user_id()
                  AND i.status IN {statuses}
            )
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY issue_media_delete ON issue_media FOR DELETE
        USING (
            EXISTS (
                SELECT 1 FROM issues i
                WHERE i.id = issue_id AND i.reporter_id = app_current_user_id()
                  AND i.status IN {statuses}
            )
        )
        """
    )


def _grants_and_rls() -> None:
    op.execute(f"GRANT SELECT, INSERT ON departments TO {APP_ROLE}")
    op.execute(
        f"GRANT UPDATE (name, description, is_active, updated_at) ON departments TO {APP_ROLE}"
    )
    op.execute(f"GRANT SELECT, INSERT ON issue_assignments TO {APP_ROLE}")
    op.execute(f"GRANT UPDATE (ended_at) ON issue_assignments TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON issue_updates TO {APP_ROLE}")
    op.execute(f"GRANT UPDATE (status, duplicate_of_issue_id, updated_at) ON issues TO {APP_ROLE}")

    op.execute("ALTER TABLE departments ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY departments_select ON departments FOR SELECT USING ({MEMBER})")
    op.execute(f"CREATE POLICY departments_insert ON departments FOR INSERT WITH CHECK ({ADMIN})")
    op.execute(
        f"CREATE POLICY departments_update ON departments FOR UPDATE USING ({ADMIN}) WITH CHECK ({ADMIN})"
    )

    op.execute("ALTER TABLE issue_assignments ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY issue_assignments_select ON issue_assignments FOR SELECT USING ({MEMBER})"
    )
    op.execute(
        f"""
        CREATE POLICY issue_assignments_insert ON issue_assignments FOR INSERT
        WITH CHECK ({MEMBER} AND assigned_by_user_id = app_current_user_id())
        """
    )
    op.execute(
        f"CREATE POLICY issue_assignments_update ON issue_assignments FOR UPDATE USING ({MEMBER}) WITH CHECK ({MEMBER})"
    )

    op.execute("ALTER TABLE issue_updates ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY issue_updates_select ON issue_updates FOR SELECT USING ({MEMBER})")
    op.execute(
        f"""
        CREATE POLICY issue_updates_insert ON issue_updates FOR INSERT
        WITH CHECK ({MEMBER} AND author_user_id = app_current_user_id())
        """
    )

    # Two ways a report's status may change: staff of its council, or the
    # reporter answering a request for information (and only to UNDER_REVIEW).
    op.execute(
        f"CREATE POLICY issues_update_staff ON issues FOR UPDATE USING ({MEMBER}) WITH CHECK ({MEMBER})"
    )
    op.execute(
        """
        CREATE POLICY issues_update_reporter ON issues FOR UPDATE
        USING (reporter_id = app_current_user_id() AND status = 'NEEDS_INFORMATION')
        WITH CHECK (reporter_id = app_current_user_id() AND status = 'UNDER_REVIEW')
        """
    )
    _media_policies(OPEN_FOR_REPORTER)


def _drop_rls() -> None:
    _media_policies("('SUBMITTED')")
    for policy, table in (
        ("issues_update_reporter", "issues"),
        ("issues_update_staff", "issues"),
        ("issue_updates_insert", "issue_updates"),
        ("issue_updates_select", "issue_updates"),
        ("issue_assignments_update", "issue_assignments"),
        ("issue_assignments_insert", "issue_assignments"),
        ("issue_assignments_select", "issue_assignments"),
        ("departments_update", "departments"),
        ("departments_insert", "departments"),
        ("departments_select", "departments"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute(f"REVOKE UPDATE ON issues FROM {APP_ROLE}")
