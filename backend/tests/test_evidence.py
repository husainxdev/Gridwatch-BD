"""Phase 5–6 behavior, using the runner's disposable PostgreSQL database."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import Location, User
from app.security import now


@pytest.fixture
def setup():
    client = TestClient(app)

    def user():
        r = client.post(
            "/api/auth/register",
            json={
                "email": uuid.uuid4().hex + "@example.com",
                "password": "test-password",
                "display_name": "Evidence tester",
            },
        )
        assert r.status_code == 201
        return r.json()

    admin, user1, user2 = user(), user(), user()
    with SessionLocal.begin() as db:
        db.get(User, uuid.UUID(admin["user"]["id"])).role = "admin"
        loc = Location(
            name_bn="কাল্পনিক" + uuid.uuid4().hex,
            name_en="Fictional " + uuid.uuid4().hex,
            kind="division",
            slug=uuid.uuid4().hex,
            verification_status="verified",
            source_url="https://example.com/test",
            verified_at=now(),
        )
        db.add(loc)
        db.flush()
        key = str(loc.id)

    def headers(u):
        return {"Authorization": "Bearer " + u["access_token"]}

    return client, key, headers(admin), headers(user1), headers(user2)


def test_lifecycle_visibility_versions_and_revision(setup):
    c, area, a, u, _ = setup
    body = {
        "title": "Fictional test notice",
        "body": "This is fictional test evidence only",
        "publisher": "Fictional office",
        "source_url": "https://example.com/file.pdf",
        "published_at": None,
    }
    assert c.post("/api/admin/notices", headers=u, json=body).status_code == 403
    r = c.post("/api/admin/notices", headers=a, json=body)
    assert r.status_code == 201, r.text
    n = r.json()
    key = n["id"]
    assert c.get("/api/notices/" + key).status_code == 404
    assert (
        c.post(
            "/api/admin/notices/" + key + "/publish", headers=a, json={"version": 1}
        ).status_code
        == 422
    )
    assert (
        c.post(
            "/api/admin/notices/" + key + "/verify", headers=a, json={"version": 1}
        ).status_code
        == 200
    )
    assert c.put("/api/admin/notices/" + key, headers=a, json=body).status_code == 409
    assert (
        c.post(
            "/api/admin/notices/" + key + "/publish", headers=a, json={"version": 2}
        ).status_code
        == 200
    )
    assert c.get("/api/notices/" + key).status_code == 200
    t = now() + timedelta(hours=1)
    payload = {
        "notice_id": key,
        "location_id": area,
        "starts_at": t.isoformat(),
        "ends_at": (t + timedelta(hours=1)).isoformat(),
    }
    assert (
        c.post(
            "/api/admin/schedules",
            headers=a,
            json={**payload, "feeder_id": str(uuid.uuid4())},
        ).status_code
        == 422
    )
    assert (
        c.post(
            "/api/admin/schedules",
            headers=a,
            json={**payload, "ends_at": t.isoformat()},
        ).status_code
        == 422
    )
    s = c.post("/api/admin/schedules", headers=a, json=payload)
    assert s.status_code == 201, s.text
    sid = s.json()["id"]
    assert c.get("/api/schedules/" + sid).status_code == 404
    assert (
        c.post(
            "/api/admin/schedules/" + sid + "/publish", headers=a, json={"version": 1}
        ).status_code
        == 200
    )
    assert (
        c.get(
            "/api/schedules?location_id="
            + area
            + "&starts_before="
            + (t + timedelta(minutes=1)).isoformat().replace("+", "%2B")
        ).json()["total"]
        == 1
    )
    assert c.post("/api/admin/schedules", headers=a, json=payload).json()["warning"]
    assert (
        c.put(
            "/api/admin/schedules/" + sid, headers=a, json={**payload, "version": 1}
        ).status_code
        == 409
    )
    assert (
        c.put(
            "/api/admin/schedules/" + sid, headers=a, json={**payload, "version": 2}
        ).status_code
        == 200
    )
    assert c.get("/api/schedules/" + sid).status_code == 404
    assert (
        len(
            c.get(
                "/api/admin/evidence/schedules/" + sid + "/revisions", headers=a
            ).json()["items"]
        )
        == 3
    )
    assert (
        c.post(
            "/api/admin/schedules/" + sid + "/publish", headers=a, json={"version": 3}
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/api/admin/schedules/" + sid + "/cancel", headers=a, json={"version": 4}
        ).json()["status"]
        == "cancelled"
    )
    assert (
        c.delete("/api/admin/schedules/" + sid + "?version=5", headers=a).status_code
        == 409
    )
    assert (
        c.post(
            "/api/admin/notices/" + key + "/withdraw", headers=a, json={"version": 3}
        ).status_code
        == 200
    )
    assert c.get("/api/schedules/" + sid).status_code == 404


def test_personal_transitions_idempotency_privacy_and_review(setup, monkeypatch):
    c, area, a, u, v = setup
    monkeypatch.setattr(get_settings(), "report_cooldown_seconds", 0)
    base = now() - timedelta(minutes=10)

    def report(h, kind, minute=0):
        return c.post(
            "/api/reports",
            headers=h,
            json={
                "location_id": area,
                "kind": kind,
                "observed_at": (base + timedelta(minutes=minute)).isoformat(),
                "idempotency_key": str(uuid.uuid4()),
            },
        )

    first = report(u, "power_off")
    assert first.status_code == 201, first.text
    assert report(u, "power_off", 1).json()["episode_id"] == first.json()["episode_id"]
    assert report(v, "still_off", 1).status_code == 201
    assert report(u, "power_back", -1).status_code == 422
    assert report(u, "power_back", 2).status_code == 201
    episodes = c.get("/api/me/episodes", headers=u).json()["items"]
    assert len(episodes) == 1 and episodes[0]["duration_seconds"] == 120
    assert c.get("/api/me/episodes", headers=v).json()["items"][0]["is_open"]
    counts = c.get("/api/reports/summary?location_id=" + area).json()["counts"]
    assert counts == {"power_off": 0, "still_off": 1, "power_back": 1}
    assert report(u, "power_off", 3).json()["episode_id"] != first.json()["episode_id"]
    assert report(u, "still_off", 1).json()["moderation"] == "pending"
    assert len(c.get("/api/me/episodes", headers=u).json()["items"]) == 2
    public = c.get("/api/reports?location_id=" + area).json()["items"]
    assert all(
        "user_id" not in r and "note" not in r and "idempotency_key" not in r
        for r in public
    )
    latest = c.get("/api/me/reports", headers=u).json()["items"][1]
    # Rejecting the latest accepted observation rebuilds personal history without it.
    assert (
        c.post(
            "/api/admin/reports/" + latest["id"] + "/moderate",
            headers=a,
            json={"state": "rejected", "reason": "Test correction"},
        ).status_code
        == 200
    )
    assert (
        c.get("/api/reports/summary?location_id=" + area).json()["counts"]["power_off"]
        == 0
    )


def test_concurrent_identical_retry_and_changed_payload(setup):
    c, area, _, u, _ = setup
    payload = {
        "location_id": area,
        "kind": "power_back",
        "observed_at": now().isoformat(),
        "idempotency_key": str(uuid.uuid4()),
        "note": "my connection",
    }

    def send(_):
        with TestClient(app) as client:
            return client.post("/api/reports", headers=u, json=payload)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, range(2)))
    assert all(r.status_code == 201 for r in responses)
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert (
        c.post(
            "/api/reports", headers=u, json={**payload, "note": "changed"}
        ).status_code
        == 409
    )
    episode = c.get("/api/me/episodes", headers=u).json()["items"][0]
    assert episode["duration_seconds"] is None and episode["started_at"] is None


def test_report_limits_clock_validation_and_independent_users(setup, monkeypatch):
    c, area, _, u, v = setup
    monkeypatch.setattr(get_settings(), "report_rate_limit", 1)

    def payload(kind="power_off", time=None):
        return {
            "location_id": area,
            "kind": kind,
            "observed_at": (time or now()).isoformat(),
            "idempotency_key": str(uuid.uuid4()),
        }

    assert (
        c.post(
            "/api/reports", headers=u, json=payload(time=now() + timedelta(hours=1))
        ).status_code
        == 422
    )
    assert (
        c.post(
            "/api/reports", headers=u, json=payload(time=now() - timedelta(days=2))
        ).status_code
        == 422
    )
    body = payload()
    assert c.post("/api/reports", headers=u, json=body).status_code == 201
    assert c.post("/api/reports", headers=u, json=body).status_code == 201
    assert (
        c.post("/api/reports", headers=u, json=payload("power_back")).status_code == 429
    )
    assert c.post("/api/reports", headers=v, json=payload()).status_code == 201


def test_demo_private_and_concurrent_admin_edits(setup):
    c, _, a, _, _ = setup
    body = {
        "title": "Fictional demo test",
        "body": "Fictional demonstration only",
        "source_url": "https://example.com/demo.png",
        "publisher": "Fictional office",
        "is_demo": True,
    }
    created = c.post("/api/admin/notices", headers=a, json=body).json()
    key = created["id"]

    def update(_):
        with TestClient(app) as client:
            return client.put(
                "/api/admin/notices/" + key, headers=a, json={**body, "version": 1}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update, range(2))) == [200, 409]
    assert (
        c.post(
            "/api/admin/notices/" + key + "/verify", headers=a, json={"version": 2}
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/api/admin/notices/" + key + "/publish", headers=a, json={"version": 3}
        ).status_code
        == 200
    )
    assert c.get("/api/notices/" + key).status_code == 404
