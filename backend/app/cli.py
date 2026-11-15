"""Operator commands. Run inside the API container or a configured venv:

    python -m app.cli grant-platform-admin someone@example.com
    python -m app.cli revoke-platform-admin someone@example.com
    python -m app.cli load-sample-boundaries [--create-missing]
    python -m app.cli seed-demo --confirm [--if-empty] [--password-from-env]
    python -m app.cli prepare-database

There is deliberately no HTTP endpoint for granting platform administration:
it requires shell access to the deployment, and every change is audited.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from psycopg import sql
from sqlalchemy import create_engine, make_url, select, text

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.models.councils import BoundarySource, Council
from app.repositories.identity import UserRepository
from app.services.audit import record_audit
from app.services.geo import BoundaryService


def set_platform_admin(email: str, *, grant: bool) -> str:
    with get_session_factory()() as db:
        user = UserRepository(db).get_by_email(email.strip().lower())
        if user is None:
            raise SystemExit(f"No user with email {email!r}. They must register first.")
        if user.is_platform_admin == grant:
            return "No change: the user already has that status."
        user.is_platform_admin = grant
        record_audit(
            db,
            action="platform_admin.granted" if grant else "platform_admin.revoked",
            actor_user_id=None,
            target_type="user",
            target_id=user.id,
            details={"via": "cli"},
        )
        db.commit()
        return f"Platform administrator {'granted to' if grant else 'revoked from'} {user.email}."


SAMPLE_BOUNDARIES = Path(__file__).parent / "data" / "sample_boundaries.geojson"


def load_sample_boundaries(*, create_missing: bool = False) -> list[str]:
    """Give councils with matching slugs the bundled SAMPLE boundaries.

    Sample boundaries are illustrative octagons, always labelled as samples in
    the API and UI. Councils that already have an official boundary are skipped.
    """
    collection = json.loads(SAMPLE_BOUNDARIES.read_text())
    report = []
    with get_session_factory()() as db:
        service = BoundaryService(db, get_settings())
        for feature in collection["features"]:
            slug, name = feature["properties"]["slug"], feature["properties"]["name"]
            council = db.scalar(select(Council).where(Council.slug == slug))
            if council is None and create_missing:
                council = Council(slug=slug, name=name)
                db.add(council)
                db.flush()
                record_audit(
                    db,
                    action="council.created",
                    actor_user_id=None,
                    council_id=council.id,
                    target_type="council",
                    target_id=council.id,
                    details={"slug": slug, "name": name, "via": "cli-sample"},
                )
                db.commit()
            if council is None:
                report.append(f"{slug}: no such council (use --create-missing)")
                continue
            if council.boundary_source == BoundarySource.OFFICIAL:
                report.append(f"{slug}: kept its official boundary")
                continue
            result = service.set_boundary(
                None, council.id, feature, BoundarySource.SAMPLE, via="cli"
            )
            report.append(f"{slug}: sample boundary loaded ({result.area_km2} km²)")
    return report


def seed_demo(*, confirm: bool, if_empty: bool = False, password_from_env: bool = False) -> int:
    if not confirm:
        print("This adds sample accounts and reports. Run again with --confirm.")
        return 2
    from app.demo import DemoSeeder  # imports app.cli; avoid a cycle at load time

    shared = None
    if password_from_env:
        shared = os.environ.get("DEMO_ACCOUNT_PASSWORD", "")
        if len(shared) < 10:
            print("Set DEMO_ACCOUNT_PASSWORD (at least 10 characters).")
            return 2
    seeder = DemoSeeder(shared_password=shared)
    if if_empty and seeder.already_seeded():
        print("Demo data already present.")
        return 0
    accounts = seeder.run()
    if shared:
        # Never print the shared password: it may end up in hosted logs.
        print("\nSample accounts (password: the value of DEMO_ACCOUNT_PASSWORD):")
        for account in accounts[1:]:
            print(f"  {account.email:<45} {account.full_name}")
        return 0
    print("\nSample accounts (passwords are shown only now; store them safely):")
    for account in accounts:
        print(f"  {account.email:<45} {account.password}   {account.full_name}")
    return 0


def _ensure_login_role(connection, role: str, url: str | None) -> str:  # type: ignore[no-untyped-def]
    """Create `role` with the password from its connection URL, if it does not exist yet."""
    if url is None:
        return f"{role}: no connection URL configured, skipped"
    parsed = make_url(url)
    if parsed.username != role or not parsed.password:
        raise SystemExit(f"The {role} connection URL must log in as {role} with a password.")
    exists = connection.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}
    ).first()
    if exists:
        return f"{role}: already exists"
    connection.exec_driver_sql(
        sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}")
        .format(sql.Identifier(role), sql.Literal(parsed.password))
        .as_string()
    )
    return f"{role}: created"


def prepare_database() -> list[str]:
    """For hosts without a release step: roles first (migrations grant to them), then migrations.

    Runs as the schema owner (CIVICWATCH_MIGRATION_DATABASE_URL), which must
    be allowed to create roles, as on Neon or a self-managed PostgreSQL.
    """
    settings = get_settings()
    if settings.migration_database_url is None:
        raise SystemExit("Set CIVICWATCH_MIGRATION_DATABASE_URL (the schema owner).")
    engine = create_engine(settings.effective_migration_database_url)
    with engine.begin() as connection:
        report = [
            _ensure_login_role(connection, "civicwatch_app", str(settings.database_url)),
            _ensure_login_role(
                connection,
                "civicwatch_worker",
                str(settings.worker_database_url) if settings.worker_database_url else None,
            ),
        ]
    engine.dispose()
    backend_root = Path(__file__).resolve().parent.parent
    alembic_config = AlembicConfig(str(backend_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(backend_root / "alembic"))
    alembic_command.upgrade(alembic_config, "head")
    report.append("migrations: up to date")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("grant-platform-admin", "revoke-platform-admin"):
        command = commands.add_parser(name)
        command.add_argument("email")
    samples = commands.add_parser(
        "load-sample-boundaries", help="Apply SAMPLE (non-official) boundaries for demonstrations"
    )
    samples.add_argument("--create-missing", action="store_true", help="Create sample councils too")
    demo = commands.add_parser(
        "seed-demo", help="Add labelled SAMPLE councils, staff, residents and reports"
    )
    demo.add_argument(
        "--confirm", action="store_true", help="Required: this adds sample data to the database"
    )
    demo.add_argument(
        "--if-empty", action="store_true", help="Do nothing (and succeed) if already seeded"
    )
    demo.add_argument(
        "--password-from-env",
        action="store_true",
        help="Give sample staff and residents the password in DEMO_ACCOUNT_PASSWORD",
    )
    commands.add_parser(
        "prepare-database",
        help="Create or update the API and worker roles, then apply migrations",
    )
    args = parser.parse_args(argv)
    if args.command == "seed-demo":
        return seed_demo(
            confirm=args.confirm, if_empty=args.if_empty, password_from_env=args.password_from_env
        )
    if args.command == "prepare-database":
        for line in prepare_database():
            print(line)
        return 0
    if args.command == "load-sample-boundaries":
        for line in load_sample_boundaries(create_missing=args.create_missing):
            print(line)
        return 0
    print(set_platform_admin(args.email, grant=args.command == "grant-platform-admin"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
