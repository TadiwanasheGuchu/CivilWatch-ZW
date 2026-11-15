"""The demonstration seeder creates labelled sample data through the real workflow."""

from collections import Counter

import pytest
from sqlalchemy import Engine, text

from app.cli import main
from app.demo import REPORTS, DemoSeeder


def test_seed_demo_needs_confirmation(capsys) -> None:
    assert main(["seed-demo"]) == 2
    assert "--confirm" in capsys.readouterr().out


def test_seed_demo_creates_labelled_sample_data(owner_engine: Engine, client) -> None:
    accounts = DemoSeeder().run()
    assert all(a.email.endswith("@example.com") for a in accounts)
    assert len({a.password for a in accounts}) == len(accounts)

    with owner_engine.connect() as connection:
        titles = connection.execute(text("SELECT title FROM issues")).scalars().all()
        statuses = Counter(connection.execute(text("SELECT status FROM issues")).scalars())
        sources = set(
            connection.execute(
                text("SELECT boundary_source FROM councils WHERE boundary IS NOT NULL")
            ).scalars()
        )
        history = connection.execute(text("SELECT count(*) FROM issue_status_history")).scalar()
        notified = connection.execute(text("SELECT count(*) FROM notifications")).scalar()
    assert len(titles) == sum(len(r) for r in REPORTS.values())
    assert all(t.startswith("Sample: ") for t in titles)
    expected = Counter(status for reports in REPORTS.values() for *_, status, _n, _e in reports)
    assert statuses == {s.value: n for s, n in expected.items()}
    assert sources == {"sample"}
    assert history > len(titles) and notified > 0

    # Public figures count only the verified public sample reports.
    public = client.get("/api/v1/analytics/public").json()
    published = sum(
        1
        for reports in REPORTS.values()
        for _t, _c, _d, visibility, status, _n, _e in reports
        if visibility == "PUBLIC"
        and status.value in {"VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"}
    )
    assert public["published"] == published

    with pytest.raises(SystemExit, match="already present"):
        DemoSeeder().run()


def test_seed_demo_with_a_shared_password(monkeypatch, capsys, client) -> None:
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", "short")
    assert main(["seed-demo", "--confirm", "--password-from-env"]) == 2

    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", "shared demo passphrase")
    assert main(["seed-demo", "--confirm", "--if-empty", "--password-from-env"]) == 0
    output = capsys.readouterr().out
    assert "shared demo passphrase" not in output
    assert "demo.platform@example.com" not in output.split("Sample accounts")[1]

    staff = client.post(
        "/api/v1/auth/login",
        json={"email": "demo.harare.admin@example.com", "password": "shared demo passphrase"},
    )
    assert staff.status_code == 200
    # The platform administrator never gets the shared password.
    platform = client.post(
        "/api/v1/auth/login",
        json={"email": "demo.platform@example.com", "password": "shared demo passphrase"},
    )
    assert platform.status_code == 401

    # Running again on start-up is a no-op.
    assert main(["seed-demo", "--confirm", "--if-empty", "--password-from-env"]) == 0
    assert "already present" in capsys.readouterr().out


def test_hosted_database_urls_use_the_psycopg_driver() -> None:
    from app.core.config import Settings

    settings = Settings(
        database_url="postgresql://app:pw@ep-x.neon.tech/neondb?sslmode=require",
        migration_database_url="postgres://owner:pw@ep-x.neon.tech/neondb",
    )
    assert str(settings.database_url).startswith("postgresql+psycopg://app:pw@ep-x.neon.tech")
    assert str(settings.migration_database_url).startswith("postgresql+psycopg://owner")
