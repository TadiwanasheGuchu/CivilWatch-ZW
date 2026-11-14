"""Operator commands. Run inside the API container or a configured venv:

    python -m app.cli grant-platform-admin someone@example.com
    python -m app.cli revoke-platform-admin someone@example.com

There is deliberately no HTTP endpoint for granting platform administration:
it requires shell access to the deployment, and every change is audited.
"""

import argparse
import sys

from app.core.database import get_session_factory
from app.repositories.identity import UserRepository
from app.services.audit import record_audit


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("grant-platform-admin", "revoke-platform-admin"):
        command = commands.add_parser(name)
        command.add_argument("email")
    args = parser.parse_args(argv)
    print(set_platform_admin(args.email, grant=args.command == "grant-platform-admin"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
