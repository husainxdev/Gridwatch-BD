"""Integration checks use rollback-only transactions against migrated PostgreSQL."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db import SessionLocal, get_db
from app.main import app, settings
from app.models import DemoArea, Location, Notice, OutageEvent, Report, Schedule, User
from app.seed import main as seed


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session
        session.rollback()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def records(db):
    location = Location(
        name_bn="পরীক্ষা", name_en="Test", kind="neighborhood", slug=str(uuid.uuid4())
    )
    user = User(
        email=f"{uuid.uuid4()}@example.test",
        display_name="Test",
        password_hash="not-a-login-credential",
    )
    db.add_all([location, user])
    db.flush()
    return location, user


def test_live_and_ready(client):
    assert client.get("/api/health/live").json()["status"] == "ok"
    assert client.get("/api/health/ready").json() == {
        "status": "ready",
        "database": "connected",
        "schema": "0004",
    }


def test_readiness_failure_is_safe():
    class BrokenDB:
        def execute(self, *_):
            raise OperationalError("private database details", {}, None)

    app.dependency_overrides[get_db] = lambda: BrokenDB()
    try:
        response = TestClient(app).get("/api/health/ready")
        assert response.status_code == 503
        assert "private" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_seed_repeatability_and_isolation(db, client):
    before = {
        model.__tablename__: db.scalar(select(func.count()).select_from(model))
        for model in (Location, Notice, Schedule, Report, OutageEvent, User)
    }
    seed()
    seed()
    assert db.scalar(select(func.count()).select_from(DemoArea)) == 2
    for model in (Location, Notice, Schedule, Report, OutageEvent, User):
        assert (
            db.scalar(select(func.count()).select_from(model))
            == before[model.__tablename__]
        )
    payload = client.get("/api/demo/areas").json()
    assert payload["data_mode"] == "demonstration"
    assert len(payload["items"]) == 2
    assert all(item["power_status"] == "unknown" for item in payload["items"])


def test_demo_unavailable_in_production(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    assert client.get("/api/demo/areas").status_code == 404


def test_demo_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_enabled", False)
    assert client.get("/api/demo/areas").status_code == 404


def test_seed_refuses_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(SystemExit):
        seed()


def test_schedule_requires_positive_interval(db, records):
    location, _ = records
    now = datetime.now(UTC)
    notice = Notice(
        title="Test",
        body="Test",
        source_url="https://example.test/notice",
        publisher="Test",
        published_at=now,
    )
    db.add(notice)
    db.flush()
    db.add(
        Schedule(
            notice_id=notice.id, location_id=location.id, starts_at=now, ends_at=now
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_restoration_requires_evidence(db, records):
    location, user = records
    now = datetime.now(UTC)
    db.add(
        OutageEvent(
            location_id=location.id,
            started_at=now,
            restored_at=now + timedelta(minutes=5),
            verified_by=user.id,
            verified_at=now,
            start_evidence="Test observation",
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_report_idempotency_constraint(db, records):
    location, user = records
    key = uuid.uuid4()
    for _ in range(2):
        db.add(
            Report(
                location_id=location.id,
                user_id=user.id,
                kind="power_off",
                observed_at=datetime.now(UTC),
                idempotency_key=key,
            )
        )
    with pytest.raises(IntegrityError):
        db.flush()


def test_location_verification_requires_source(db):
    db.add(
        Location(
            name_bn="পরীক্ষা",
            name_en="Test",
            kind="ward",
            slug=str(uuid.uuid4()),
            verification_status="verified",
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_expired_schedule_does_not_create_restoration(db, records):
    location, user = records
    now = datetime.now(UTC)
    notice = Notice(
        title="Test",
        body="Test",
        source_url="https://example.test/notice",
        publisher="Test",
        published_at=now,
    )
    db.add(notice)
    db.flush()
    event = OutageEvent(
        location_id=location.id,
        started_at=now - timedelta(hours=2),
        verified_by=user.id,
        verified_at=now,
        start_evidence="Test evidence",
    )
    db.add_all(
        [
            event,
            Schedule(
                location_id=location.id,
                notice_id=notice.id,
                starts_at=now - timedelta(hours=2),
                ends_at=now - timedelta(hours=1),
            ),
        ]
    )
    db.flush()
    db.refresh(event)
    assert event.restored_at is None
