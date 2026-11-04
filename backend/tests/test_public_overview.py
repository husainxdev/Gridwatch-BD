"""Anonymous evidence must stay useful without exposing private dashboard records."""

import importlib.util
import json
import subprocess
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import event
from test_dashboard import accounts as accounts

from app.db import SessionLocal, engine
from app.models import Notice, Report, Schedule
from app.security import now


def test_public_overview_privacy_visibility_latest_counts_and_bounds(accounts):
    client, areas, people, headers = accounts
    area = areas[0]
    instant = now()
    with SessionLocal.begin() as db:
        for name, lifecycle, demo in [
            ("public", "published", False),
            ("draft", "draft", False),
            ("demo", "published", True),
        ]:
            notice = Notice(
                title="Fictional public board " + name,
                body="Fictional source review only",
                publisher="Fictional publisher",
                source_url="https://example.com/fictional-board",
                lifecycle=lifecycle,
                is_demo=demo,
                verification_status="verified",
                verified_by=uuid.UUID(people[0]["user"]["id"]),
                verified_at=instant,
                published_at=instant,
            )
            db.add(notice)
            db.flush()
            db.add(
                Schedule(
                    notice_id=notice.id,
                    location_id=uuid.UUID(area),
                    starts_at=instant + timedelta(hours=1),
                    ends_at=instant + timedelta(hours=2),
                    lifecycle="published",
                    is_demo=demo,
                    created_by=uuid.UUID(people[0]["user"]["id"]),
                )
            )
        db.add(
            Report(
                user_id=uuid.UUID(people[3]["user"]["id"]),
                location_id=uuid.UUID(area),
                kind="power_off",
                observed_at=instant,
                idempotency_key=uuid.uuid4(),
                moderation="rejected",
                note="PRIVATE-REJECTED-NOTE",
            )
        )
    for actor, kind, offset in [
        (0, "power_off", 3),
        (0, "still_off", 1),
        (1, "power_back", 2),
    ]:
        response = client.post(
            "/api/reports",
            headers=headers[actor],
            json={
                "location_id": area,
                "kind": kind,
                "observed_at": (instant - timedelta(minutes=offset)).isoformat(),
                "idempotency_key": str(uuid.uuid4()),
                "note": "PRIVATE-OBSERVER-NOTE",
            },
        )
        assert response.status_code == 201
    statements = []

    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        result = client.get("/api/area-overview", params={"location_id": area})
        assert result.status_code == 200
        assert len(statements) <= 8
    finally:
        event.remove(engine, "before_cursor_execute", count)
    data = result.json()
    assert "personal" not in data and data["restoration_estimate"] is None
    assert data["community"]["unique_reporters"] == 2
    assert data["community"]["evidence_label"] == "mixed"
    assert data["community"]["area_status"] == "unknown"
    assert data["schedules"]["total"] == 1
    assert len(data["recent_reports"]) == 3
    for report in data["recent_reports"]:
        assert not {
            "user_id",
            "note",
            "episode_id",
            "idempotency_key",
            "candidate_event_id",
        }.intersection(report)
    assert "created_by" not in data["schedules"]["items"][0]
    body = json.dumps(data)
    assert "PRIVATE-" not in body
    for person in people:
        assert person["user"]["email"] not in body
    assert "no-store" in result.headers["cache-control"]
    assert client.get("/api/dashboard", params={"location_id": area}).status_code == 401
    assert (
        client.get(
            "/api/area-overview", params={"location_id": area, "page": 0}
        ).status_code
        == 422
    )
    assert (
        client.get("/api/area-overview", params={"location_id": "invalid"}).status_code
        == 422
    )
    assert (
        client.get(
            "/api/area-overview", params={"location_id": str(uuid.uuid4())}
        ).status_code
        == 404
    )


def test_local_demo_mailpit_uses_loopback_and_discards_inherited_credentials(
    monkeypatch,
):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "demo_launcher_test", root / "scripts/start-local-demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("SMTP_PASSWORD", "not-a-real-inherited-password")

    def command(args, **kwargs):
        port = "1125" if args[-1] == "1025" else "8125"
        return subprocess.CompletedProcess(
            args, 0, stdout=f"127.0.0.1:{port}\n".encode()
        )

    monkeypatch.setattr(module, "run", command)
    values, url = module.local_mail_settings()
    assert url == "http://127.0.0.1:8125"
    assert values["SMTP_HOST"] == "127.0.0.1" and values["SMTP_PORT"] == "1125"
    assert values["SMTP_PASSWORD"] == values["SMTP_USERNAME"] == ""
    assert values["SMTP_STARTTLS"] == "false"
    monkeypatch.setattr(
        module,
        "run",
        lambda args: subprocess.CompletedProcess(
            args, 0, stdout=b"smtp.example.com:1025"
        ),
    )
    with pytest.raises(module.SetupError):
        module.local_mail_settings()


@pytest.mark.parametrize("endpoint", ["dashboard", "history"])
def test_authenticated_snapshots_work_with_one_connection(accounts, endpoint):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import get_settings
    from app.db import get_db
    from app.main import app

    client, areas, _, headers = accounts
    limited = create_engine(
        get_settings().database_url, pool_size=1, max_overflow=0, pool_timeout=1
    )
    sessions = sessionmaker(limited)

    def override():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override
    try:
        params = {"location_id": areas[0]}
        if endpoint == "history":
            params.update(
                start=(now() - timedelta(days=1)).isoformat(), end=now().isoformat()
            )
        response = client.get("/api/" + endpoint, params=params, headers=headers[0])
        assert response.status_code == 200
        assert limited.pool.checkedout() == 0
    finally:
        app.dependency_overrides.pop(get_db, None)
        limited.dispose()
