"""Sections 7–8: ownership, bounded schedules and independent personal evidence."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Location, Notice, PersonalEpisode, Report, Schedule, User
from app.security import now


@pytest.fixture
def accounts():
    c = TestClient(app)
    people = []
    for _ in range(4):
        r = c.post(
            "/api/auth/register",
            json={
                "email": uuid.uuid4().hex + "@example.com",
                "password": "test-password",
                "display_name": "Dashboard tester",
            },
        )
        assert r.status_code == 201
        people.append(r.json())
    areas = []
    with SessionLocal.begin() as db:
        for _ in range(2):
            loc = Location(
                name_bn="পরীক্ষা " + uuid.uuid4().hex,
                name_en="Fictional " + uuid.uuid4().hex,
                kind="division",
                slug=uuid.uuid4().hex,
                verification_status="verified",
                source_url="https://example.com/test",
                verified_at=now(),
            )
            db.add(loc)
            db.flush()
            areas.append(str(loc.id))
    headers = [{"Authorization": "Bearer " + p["access_token"]} for p in people]
    return c, areas, people, headers


def test_saved_default_concurrency_persistence_and_ownership(accounts):
    c, areas, _, headers = accounts
    u, v = headers[:2]
    for area in areas:
        assert c.post("/api/saved-areas/" + area, headers=u).status_code == 201
    assert c.post("/api/saved-areas/" + areas[0], headers=u).json()["already_saved"]
    assert (
        c.put(
            "/api/saved-areas/" + areas[0],
            headers=v,
            json={"label": "Stolen", "is_default": True},
        ).status_code
        == 404
    )
    assert (
        c.put(
            "/api/saved-areas/" + areas[0],
            headers=u,
            json={"user_id": str(uuid.uuid4()), "label": "Bad"},
        ).status_code
        == 422
    )

    def choose(area):
        with TestClient(app) as other:
            return other.put(
                "/api/saved-areas/" + area,
                headers=u,
                json={"label": "বাসা", "is_default": True},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(choose, areas)) == [200, 200]
    with TestClient(app) as device:
        saved = device.get("/api/saved-areas", headers=u)
        assert "no-store" in saved.headers["cache-control"]
        rows = saved.json()["items"]
        assert sum(x["is_default"] for x in rows) == 1
        assert all(x["label"] == "বাসা" for x in rows)
        default = next(x for x in rows if x["is_default"])
    with SessionLocal.begin() as db:
        db.get(Location, uuid.UUID(default["id"])).verification_status = "unverified"
    rows = c.get("/api/saved-areas", headers=u).json()["items"]
    assert next(x for x in rows if x["is_default"])["available"] is False
    assert (
        c.put(
            "/api/saved-areas/" + default["id"], headers=u, json={"is_default": True}
        ).status_code
        == 422
    )
    assert c.delete("/api/saved-areas/" + default["id"], headers=u).status_code == 204
    assert not any(
        x["is_default"] for x in c.get("/api/saved-areas", headers=u).json()["items"]
    )
    assert c.get("/api/saved-areas", headers=v).json()["items"] == []


def test_dashboard_midnight_coverage_cancellation_and_privacy(accounts, monkeypatch):
    c, areas, people, headers = accounts
    uid = uuid.UUID(people[0]["user"]["id"])
    fixed = datetime(2026, 10, 28, 17, 30, tzinfo=UTC)  # 23:30 Bangladesh
    monkeypatch.setattr("app.dashboard.now", lambda: fixed)
    monkeypatch.setattr("app.evidence.now", lambda: fixed)
    with SessionLocal.begin() as db:
        notice = Notice(
            title="Fictional midnight source",
            body="Test only",
            source_url="https://example.com/midnight.pdf",
            publisher="Fictional office",
            published_at=None,
            verification_status="verified",
            verified_by=uid,
            verified_at=fixed,
            lifecycle="published",
        )
        db.add(notice)
        db.flush()
        for status in ["announced", "cancelled", "superseded"]:
            db.add(
                Schedule(
                    notice_id=notice.id,
                    location_id=uuid.UUID(areas[1]),
                    starts_at=fixed - timedelta(hours=1),
                    ends_at=fixed + timedelta(hours=2),
                    status=status,
                    lifecycle="published",
                    coverage=[
                        {"id": areas[0], "name_bn": "Only this named local area"}
                    ],
                )
            )
        # Other location, draft, demo and boundary-touching windows must not leak.
        for kw in [
            {"location_id": uuid.UUID(areas[1])},
            {"lifecycle": "draft"},
            {"is_demo": True},
            {
                "ends_at": datetime(2026, 10, 27, 18, tzinfo=UTC),
                "starts_at": datetime(2026, 10, 27, 17, tzinfo=UTC),
            },
        ]:
            fields = (
                dict(
                    notice_id=notice.id,
                    location_id=uuid.UUID(areas[0]),
                    starts_at=fixed,
                    ends_at=fixed + timedelta(hours=1),
                    lifecycle="published",
                )
                | kw
            )
            db.add(Schedule(**fields))
        db.add(
            PersonalEpisode(
                user_id=uid,
                location_id=uuid.UUID(areas[0]),
                started_at=fixed - timedelta(hours=2),
                last_observed_at=fixed,
                is_open=True,
            )
        )
    response = c.get("/api/dashboard?location_id=" + areas[0], headers=headers[0])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["schedules"]["total"] == 3
    assert {r["status"] for r in data["schedules"]["items"]} == {
        "announced",
        "cancelled",
        "superseded",
    }
    assert all(
        r["notice"]["publisher"] == "Fictional office"
        and r["notice"]["published_at"] is None
        for r in data["schedules"]["items"]
    )
    assert all(
        r["window_state"] == "within_announced_window"
        for r in data["schedules"]["items"]
    )
    assert data["personal"]["episode"]["is_open"]
    assert data["restoration_estimate"] is None
    assert "private" in response.headers["cache-control"]
    assert (
        c.get("/api/dashboard?location_id=" + areas[0], headers=headers[1]).json()[
            "personal"
        ]["episode"]
        is None
    )
    assert (
        c.get(
            "/api/dashboard?location_id=" + areas[0] + "&page=0", headers=headers[0]
        ).status_code
        == 422
    )
    assert c.get("/api/dashboard?location_id=" + areas[0]).status_code == 401
    assert (
        c.get("/api/dashboard?location_id=" + areas[1], headers=headers[0]).json()[
            "personal"
        ]["episode"]
        is None
    )


def test_summary_latest_per_person_stale_rejected_and_demo(accounts, monkeypatch):
    c, areas, people, headers = accounts
    instant = now()
    monkeypatch.setattr("app.evidence.now", lambda: instant)
    with SessionLocal.begin() as db:

        def row(person, kind, age, **kwargs):
            db.add(
                Report(
                    user_id=uuid.UUID(people[person]["user"]["id"]),
                    location_id=uuid.UUID(areas[0]),
                    kind=kind,
                    observed_at=instant - timedelta(minutes=age),
                    idempotency_key=uuid.uuid4(),
                    note="PRIVATE-NOTE",
                    **kwargs,
                )
            )

        row(0, "power_off", 20)
        row(0, "power_back", 10)
        row(1, "still_off", 5)
        row(2, "power_off", 61)
        row(2, "power_back", 1, moderation="rejected")
        row(3, "power_off", 1, is_demo=True)
        row(3, "power_off", 2, moderation="pending")
    evidence = c.get("/api/reports/summary?location_id=" + areas[0]).json()
    assert evidence["unique_reporters"] == 2
    assert evidence["counts"] == {"power_off": 0, "power_back": 1, "still_off": 1}
    assert evidence["evidence_label"] == "mixed"
    assert evidence["area_status"] == "unknown"
    assert "PRIVATE-NOTE" not in str(evidence)
    assert "user_id" not in evidence
    empty = c.get("/api/reports/summary?location_id=" + areas[1]).json()
    assert empty["evidence_label"] == "no_recent_reports"
    assert (
        c.get("/api/dashboard?location_id=" + areas[1], headers=headers[0]).json()[
            "schedules"
        ]["total"]
        == 0
    )


def test_dashboard_still_off_preserves_episode_and_personal_times(accounts):
    c, areas, _, headers = accounts

    def send(user, kind):
        r = c.post(
            "/api/reports",
            headers=headers[user],
            json={
                "location_id": areas[0],
                "kind": kind,
                "observed_at": now().isoformat(),
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        assert r.status_code == 201, r.text
        return r.json()

    first = send(0, "power_off")
    send(1, "power_back")
    before = c.get("/api/dashboard?location_id=" + areas[0], headers=headers[0]).json()
    polled = c.get("/api/dashboard?location_id=" + areas[0], headers=headers[0]).json()
    assert (
        polled["personal"]["latest_report"]["observed_at"]
        == before["personal"]["latest_report"]["observed_at"]
    )
    assert (
        polled["personal"]["episode"]["started_at"]
        == before["personal"]["episode"]["started_at"]
    )
    send(0, "still_off")
    after = c.get("/api/dashboard?location_id=" + areas[0], headers=headers[0]).json()
    assert after["personal"]["episode"]["id"] == first["episode_id"]
    assert (
        before["personal"]["episode"]["started_at"]
        == after["personal"]["episode"]["started_at"]
    )
    assert after["personal"]["episode"]["is_open"]
    assert after["community"]["evidence_label"] == "mixed"
    send(0, "power_back")
    restored = c.get(
        "/api/dashboard?location_id=" + areas[0], headers=headers[0]
    ).json()["personal"]["episode"]
    assert not restored["is_open"] and restored["ended_at"]
    send(2, "still_off")
    assert (
        c.get("/api/dashboard?location_id=" + areas[0], headers=headers[2]).json()[
            "personal"
        ]["episode"]["started_at"]
        is None
    )


def test_partial_coverage_snapshot_survives_location_move_and_queries_are_bounded(
    accounts,
):
    from sqlalchemy import event

    from app.db import engine

    c, areas, people, headers = accounts
    admin_id = uuid.UUID(people[0]["user"]["id"])
    with SessionLocal.begin() as db:
        db.get(User, admin_id).role = "admin"
        child = Location(
            name_bn="আংশিক পরীক্ষা " + uuid.uuid4().hex,
            name_en="Partial test " + uuid.uuid4().hex,
            slug=uuid.uuid4().hex,
            kind="district",
            parent_id=uuid.UUID(areas[0]),
            verification_status="verified",
            source_url="https://example.com/child",
            verified_at=now(),
        )
        db.add(child)
        db.flush()
        child_id = str(child.id)
    n = c.post(
        "/api/admin/notices",
        headers=headers[0],
        json={
            "title": "Partial test notice",
            "body": "Fictional scoped test announcement",
            "source_url": "https://example.com/partial",
            "publisher": "Test office",
        },
    ).json()
    assert (
        c.post(
            "/api/admin/notices/" + n["id"] + "/verify",
            headers=headers[0],
            json={"version": 1},
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/api/admin/notices/" + n["id"] + "/publish",
            headers=headers[0],
            json={"version": 2},
        ).status_code
        == 200
    )
    s = c.post(
        "/api/admin/schedules",
        headers=headers[0],
        json={
            "notice_id": n["id"],
            "location_id": child_id,
            "starts_at": now().isoformat(),
            "ends_at": (now() + timedelta(hours=1)).isoformat(),
        },
    )
    assert s.status_code == 201, s.text
    assert areas[0] in s.json()["coverage"][0]["ancestor_ids"]
    assert (
        c.post(
            "/api/admin/schedules/" + s.json()["id"] + "/publish",
            headers=headers[0],
            json={"version": 1},
        ).status_code
        == 200
    )
    with SessionLocal.begin() as db:
        db.get(Location, uuid.UUID(child_id)).parent_id = uuid.UUID(areas[1])
        for _ in range(9):
            notice = Notice(
                title="Query bound test",
                body="Fictional",
                source_url="https://example.com/query",
                publisher="Test office",
                verification_status="verified",
                verified_by=admin_id,
                verified_at=now(),
                lifecycle="published",
            )
            db.add(notice)
            db.flush()
            db.add(
                Schedule(
                    notice_id=notice.id,
                    location_id=uuid.UUID(areas[0]),
                    starts_at=now(),
                    ends_at=now() + timedelta(hours=1),
                    lifecycle="published",
                )
            )
    queries = []

    def count(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        response = c.get("/api/dashboard?location_id=" + areas[0], headers=headers[0])
        assert response.status_code == 200, response.text
        assert len(response.json()["schedules"]["items"]) == 10
        assert (
            sum(r["partial_coverage"] for r in response.json()["schedules"]["items"])
            == 1
        )
        # The number of database requests stays bounded even with different notices.
        assert len(queries) <= 14
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert (
        c.get("/api/dashboard?location_id=" + areas[1], headers=headers[0]).json()[
            "schedules"
        ]["total"]
        == 0
    )
