"""Operator commands. Run inside the API container or a configured venv:

    python -m app.cli grant-platform-admin someone@example.com
    python -m app.cli revoke-platform-admin someone@example.com
    python -m app.cli load-sample-boundaries [--create-missing]
    python -m app.cli seed-demo --confirm

There is deliberately no HTTP endpoint for granting platform administration:
it requires shell access to the deployment, and every change is audited.
"""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import select

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


def seed_demo(*, confirm: bool) -> int:
    if not confirm:
        print("This adds sample accounts and reports. Run again with --confirm.")
        return 2
    from app.demo import DemoSeeder  # imports app.cli; avoid a cycle at load time

    accounts = DemoSeeder().run()
    print("\nSample accounts (passwords are shown only now; store them safely):")
    for account in accounts:
        print(f"  {account.email:<45} {account.password}   {account.full_name}")
    return 0


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
    args = parser.parse_args(argv)
    if args.command == "seed-demo":
        return seed_demo(confirm=args.confirm)
    if args.command == "load-sample-boundaries":
        for line in load_sample_boundaries(create_missing=args.create_missing):
            print(line)
        return 0
    print(set_platform_admin(args.email, grant=args.command == "grant-platform-admin"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
