"""Create councils, memberships and audit logs; add the application role and RLS.

The API connects as `civicwatch_app`, which owns nothing and has only the
privileges granted here, so PostgreSQL Row-Level Security applies to it.
Migrations run as the schema owner (CIVICWATCH_MIGRATION_DATABASE_URL).
Infrastructure creates the role with LOGIN and a password; this migration
creates it as NOLOGIN only if it does not exist yet, so grants never fail.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-14 07:37:20.259802
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "councils",
        sa.Column("slug", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "boundary",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
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
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name=op.f("ck_councils_slug_format")
        ),
        sa.CheckConstraint("char_length(name) > 0", name=op.f("ck_councils_name_not_empty")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_councils")),
        sa.UniqueConstraint("slug", name=op.f("uq_councils_slug")),
    )
    op.create_index(
        "ix_councils_boundary", "councils", ["boundary"], unique=False, postgresql_using="gist"
    )
    op.create_table(
        "audit_logs",
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("council_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column(
            "details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["council_id"],
            ["councils.id"],
            name=op.f("fk_audit_logs_council_id_councils"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index(
        "ix_audit_logs_council_id_occurred_at",
        "audit_logs",
        ["council_id", "occurred_at"],
        unique=False,
    )
    op.create_table(
        "council_memberships",
        sa.Column("council_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("granted_by_user_id", sa.UUID(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
            "role IN ('council_admin', 'department_manager', 'verification_officer', 'maintenance_officer')",
            name=op.f("ck_council_memberships_role_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["council_id"],
            ["councils.id"],
            name=op.f("fk_council_memberships_council_id_councils"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["users.id"],
            name=op.f("fk_council_memberships_granted_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_council_memberships_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_council_memberships")),
    )
    op.create_index(
        "ix_council_memberships_user_id", "council_memberships", ["user_id"], unique=False
    )
    op.create_index(
        "uq_council_memberships_active",
        "council_memberships",
        ["council_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    _create_app_role_and_grants()
    _create_rls()


def downgrade() -> None:
    _drop_rls()
    op.execute("REVOKE ALL ON users, user_sessions FROM civicwatch_app")
    op.drop_index(
        "uq_council_memberships_active",
        table_name="council_memberships",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.drop_index("ix_council_memberships_user_id", table_name="council_memberships")
    op.drop_table("council_memberships")
    op.drop_index("ix_audit_logs_council_id_occurred_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_councils_boundary", table_name="councils", postgresql_using="gist")
    op.drop_table("councils")


APP_ROLE = "civicwatch_app"


def _create_app_role_and_grants() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE} NOLOGIN;
            END IF;
        END
        $$
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON users, user_sessions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON councils, council_memberships TO {APP_ROLE}")
    # Append-only: no UPDATE or DELETE on the audit trail.
    op.execute(f"GRANT SELECT, INSERT ON audit_logs TO {APP_ROLE}")
    op.execute(f"GRANT SELECT ON spatial_ref_sys TO {APP_ROLE}")


def _create_rls() -> None:
    # The request's user is passed in a transaction-local setting by
    # app/core/database.py. Helpers that read council_memberships are
    # SECURITY DEFINER (run as the owner, so not subject to RLS) to avoid
    # policies on that table recursing into themselves.
    op.execute(
        """
        CREATE FUNCTION app_current_user_id() RETURNS uuid
        LANGUAGE sql STABLE
        AS $$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION app_is_platform_admin() RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT coalesce(
                (SELECT is_platform_admin AND is_active FROM users WHERE id = app_current_user_id()),
                false
            )
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION app_member_council_ids() RETURNS SETOF uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT council_id FROM council_memberships
            WHERE user_id = app_current_user_id() AND revoked_at IS NULL
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION app_admin_council_ids() RETURNS SETOF uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT council_id FROM council_memberships
            WHERE user_id = app_current_user_id()
              AND revoked_at IS NULL
              AND role = 'council_admin'
        $$
        """
    )

    op.execute("ALTER TABLE council_memberships ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY council_memberships_select ON council_memberships FOR SELECT
        USING (
            user_id = app_current_user_id()
            OR council_id IN (SELECT app_member_council_ids())
            OR app_is_platform_admin()
        )
        """
    )
    op.execute(
        """
        CREATE POLICY council_memberships_insert ON council_memberships FOR INSERT
        WITH CHECK (council_id IN (SELECT app_admin_council_ids()) OR app_is_platform_admin())
        """
    )
    op.execute(
        """
        CREATE POLICY council_memberships_update ON council_memberships FOR UPDATE
        USING (council_id IN (SELECT app_admin_council_ids()) OR app_is_platform_admin())
        WITH CHECK (council_id IN (SELECT app_admin_council_ids()) OR app_is_platform_admin())
        """
    )

    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY audit_logs_select ON audit_logs FOR SELECT
        USING (
            app_is_platform_admin()
            OR (council_id IS NOT NULL AND council_id IN (SELECT app_admin_council_ids()))
        )
        """
    )
    # Any authenticated or anonymous request may record an event, but only
    # as itself: the actor must be the current user (or none).
    op.execute(
        """
        CREATE POLICY audit_logs_insert ON audit_logs FOR INSERT
        WITH CHECK (actor_user_id IS NULL OR actor_user_id = app_current_user_id())
        """
    )


def _drop_rls() -> None:
    for policy, table in (
        ("audit_logs_insert", "audit_logs"),
        ("audit_logs_select", "audit_logs"),
        ("council_memberships_update", "council_memberships"),
        ("council_memberships_insert", "council_memberships"),
        ("council_memberships_select", "council_memberships"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    for function in (
        "app_admin_council_ids()",
        "app_member_council_ids()",
        "app_is_platform_admin()",
        "app_current_user_id()",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function}")
