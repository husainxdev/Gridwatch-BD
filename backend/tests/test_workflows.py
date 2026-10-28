"""End-to-end API correctness against an isolated migrated PostgreSQL test database."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import User
from app.security import digest

client = TestClient(app, headers={"Origin": "http://localhost:5173"})
uid = uuid.uuid4().hex
email = f"user-{uid}@example.com"
admin_email = f"admin-{uid}@example.com"
password = "long-enough-password"


def now():
    return datetime.now(UTC).isoformat()


def register(address):
    r = client.post(
        "/api/auth/register",
        json={"email": address, "password": password, "display_name": "Tester"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def headers(token):
    return {"Authorization": "Bearer " + token}


def csrf_headers(token=None):
    h = {"X-CSRF-Token": client.cookies.get("gridwatch_csrf") or ""}
    if token:
        h.update(headers(token))
    return h


def test_complete_workflow(monkeypatch):
    user_token = register(email)
    assert (
        client.get("/api/auth/me", headers=headers(user_token)).json()["role"] == "user"
    )
    assert (
        client.post(
            "/api/admin/locations", headers=headers(user_token), json={}
        ).status_code
        == 403
    )
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": email, "password": "wrong"}
        ).status_code
        == 401
    )
    admin_token = register(admin_email)
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.email == admin_email))
        user.role = "admin"
    admin_token = client.post(
        "/api/auth/login", json={"email": admin_email, "password": password}
    ).json()["access_token"]
    division = client.post(
        "/api/admin/locations",
        headers=headers(admin_token),
        json={
            "name_bn": "পরীক্ষা বিভাগ",
            "name_en": "Test Division",
            "slug": "test-division-" + uid,
            "kind": "division",
        },
    )
    assert division.status_code == 201, division.text
    division_id = division.json()["id"]
    bad = client.post(
        "/api/admin/locations",
        headers=headers(admin_token),
        json={
            "name_bn": "ভুল এলাকা",
            "name_en": "Wrong Area",
            "slug": "wrong-" + uid,
            "kind": "ward",
            "parent_id": division_id,
        },
    )
    assert bad.status_code == 422
    district = client.post(
        "/api/admin/locations",
        headers=headers(admin_token),
        json={
            "name_bn": "পরীক্ষা জেলা",
            "name_en": "Test District",
            "slug": "test-district-" + uid,
            "kind": "district",
            "parent_id": division_id,
        },
    )
    assert district.status_code == 201, district.text
    district_id = district.json()["id"]
    assert (
        client.put(
            "/api/admin/locations/" + division_id,
            headers=headers(admin_token),
            json={
                "name_bn": "পরীক্ষা বিভাগ",
                "name_en": "Test Division",
                "slug": "test-division-" + uid,
                "kind": "division",
                "parent_id": district_id,
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/saved-areas/" + district_id, headers=headers(user_token)
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/admin/locations/" + district_id + "/verify",
            headers=headers(admin_token),
            json={"source_url": "https://example.test/area"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/saved-areas/" + district_id, headers=headers(user_token)
        ).status_code
        == 201
    )
    assert (
        len(client.get("/api/saved-areas", headers=headers(user_token)).json()["items"])
        == 1
    )
    notice_body = {
        "title": "Test notice",
        "body": "Original published test notice",
        "source_url": "https://example.test/notice",
        "publisher": "Test publisher",
        "published_at": now(),
    }
    notice = client.post(
        "/api/admin/notices", headers=headers(admin_token), json=notice_body
    )
    assert notice.status_code == 201, notice.text
    nid = notice.json()["id"]
    start = datetime.now(UTC) + timedelta(hours=1)
    end = start + timedelta(hours=1)
    schedule = {
        "notice_id": nid,
        "location_id": district_id,
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
    }
    assert (
        client.post(
            "/api/admin/schedules", headers=headers(admin_token), json=schedule
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/admin/notices/" + nid + "/verify",
            headers=headers(admin_token),
            json={"version": 1},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/admin/notices/" + nid + "/publish",
            headers=headers(admin_token),
            json={"version": 2},
        ).status_code
        == 200
    )
    planned = client.post(
        "/api/admin/schedules", headers=headers(admin_token), json=schedule
    )
    assert planned.status_code == 201, planned.text
    sid = planned.json()["id"]
    assert (
        client.post(
            "/api/admin/schedules/" + sid + "/publish",
            headers=headers(admin_token),
            json={"version": 1},
        ).status_code
        == 200
    )
    activity = {
        "location_id": district_id,
        "starts_at": (start + timedelta(minutes=30)).isoformat(),
        "ends_at": (end + timedelta(minutes=30)).isoformat(),
    }
    conflict = client.post("/api/activities/check", json=activity)
    assert len(conflict.json()["conflicts"]) == 1
    assert (
        client.post(
            "/api/activities/check",
            json={
                **activity,
                "starts_at": end.isoformat(),
                "ends_at": (end + timedelta(hours=1)).isoformat(),
            },
        ).json()["conflicts"]
        == []
    )
    key = str(uuid.uuid4())
    report = {
        "location_id": district_id,
        "kind": "power_off",
        "observed_at": now(),
        "idempotency_key": key,
    }
    first = client.post("/api/reports", headers=headers(user_token), json=report)
    assert first.status_code == 201, first.text
    assert first.json()["scope"] == "individual_connection"
    assert (
        client.post("/api/reports", headers=headers(user_token), json=report).json()[
            "id"
        ]
        == first.json()["id"]
    )
    assert (
        client.post(
            "/api/reports",
            headers=headers(user_token),
            json={**report, "kind": "power_back"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/reports",
            headers=headers(user_token),
            json={**report, "idempotency_key": str(uuid.uuid4())},
        ).status_code
        == 429
    )
    assert client.get("/api/events?location_id=" + district_id).json()["total"] == 0
    event = client.post(
        "/api/admin/events",
        headers=headers(admin_token),
        json={
            "location_id": district_id,
            "started_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
            "start_evidence": "Verified test evidence",
        },
    )
    assert event.status_code == 201, event.text
    assert event.json()["restored_at"] is None
    event_id = event.json()["id"]
    restored = client.post(
        "/api/admin/events/" + event_id + "/restore",
        headers=headers(admin_token),
        json={"restored_at": now(), "evidence": "Separate restoration evidence"},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["restoration_evidence"] == "Separate restoration evidence"
    assert client.get("/api/notices?page_size=1").json()["page_size"] == 1
    assert client.get("/api/notices?sort=invalid").status_code == 422
    assert client.get("/api/locations?page_size=101").status_code == 422
    assert (
        client.post(
            "/api/admin/schedules/" + sid + "/cancel",
            headers=headers(admin_token),
            json={"version": 2},
        ).json()["status"]
        == "cancelled"
    )
    assert client.post("/api/activities/check", json=activity).json()["conflicts"] == []
    second = client.post(
        "/api/admin/schedules", headers=headers(admin_token), json=schedule
    )
    assert second.status_code == 201, second.text
    assert (
        client.put(
            "/api/admin/notices/" + nid,
            headers=headers(admin_token),
            json={**notice_body, "version": 3},
        ).status_code
        == 200
    )
    assert client.post("/api/activities/check", json=activity).json()["conflicts"] == []
    assert any(
        x["status"] == "superseded"
        for x in client.get(
            "/api/admin/schedules", headers=headers(admin_token)
        ).json()["items"]
    )
    assert client.get("/api/schedules?status=superseded").json()["total"] == 0
    assert (
        client.delete(
            "/api/admin/locations/" + district_id, headers=headers(admin_token)
        ).status_code
        == 409
    )


def test_session_rotation_replay_logout_and_password_reset(monkeypatch):
    reset_email = f"reset-{uuid.uuid4().hex}@example.com"
    token = register(reset_email)
    old = client.cookies.get("gridwatch_refresh")
    csrf = client.cookies.get("gridwatch_csrf")
    assert (
        client.post(
            "/api/auth/refresh",
            headers={"X-CSRF-Token": csrf, "Origin": "https://bad.example"},
        ).status_code
        == 403
    )
    rotated = client.post("/api/auth/refresh", headers=csrf_headers())
    assert rotated.status_code == 200, rotated.text
    assert client.get("/api/auth/me", headers=headers(token)).status_code == 401
    new = client.cookies.get("gridwatch_refresh")
    assert old != new
    client.cookies.set("gridwatch_refresh", old, path="/api/auth")
    assert client.post("/api/auth/refresh", headers=csrf_headers()).status_code == 401
    client.cookies.set("gridwatch_refresh", new, path="/api/auth")
    assert client.post("/api/auth/refresh", headers=csrf_headers()).status_code == 401
    token = client.post(
        "/api/auth/login", json={"email": reset_email, "password": password}
    ).json()["access_token"]
    assert (
        client.post("/api/auth/logout", headers=csrf_headers(token)).status_code == 204
    )
    assert client.get("/api/auth/me", headers=headers(token)).status_code == 401
    assert client.post("/api/auth/refresh", headers=csrf_headers()).status_code in (
        401,
        403,
    )
    live_token = client.post(
        "/api/auth/login", json={"email": reset_email, "password": password}
    ).json()["access_token"]
    sent = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def send_message(self, msg):
            sent.append(msg)

    monkeypatch.setattr("app.auth.smtplib.SMTP", FakeSMTP)
    assert (
        client.post(
            "/api/auth/password-reset/request", json={"email": "absent@example.com"}
        ).status_code
        == 202
    )
    assert not sent
    assert (
        client.post(
            "/api/auth/password-reset/request", json={"email": reset_email}
        ).status_code
        == 202
    )
    assert len(sent) == 1
    raw = sent[0].get_content().split("token=")[1].strip()
    with SessionLocal() as db:
        from app.models import PasswordReset

        assert (
            db.scalar(
                select(PasswordReset).where(PasswordReset.token_hash == digest(raw))
            )
            is not None
        )
    changed = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": raw, "password": "new-secret-password"},
    )
    assert changed.status_code == 200, changed.text
    assert client.get("/api/auth/me", headers=headers(live_token)).status_code == 401
    assert client.post("/api/auth/refresh", headers=csrf_headers()).status_code == 401
    assert (
        client.post(
            "/api/auth/password-reset/confirm",
            json={"token": raw, "password": "another-secret"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": reset_email, "password": password}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": reset_email, "password": "new-secret-password"},
        ).status_code
        == 200
    )
