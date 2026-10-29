"""Sections 9–10 on the runner's isolated PostgreSQL, never a user's database."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import (
    EvidenceAudit,
    Location,
    Report,
    User,
)
from app.planning import history_calculations, union_intervals
from app.security import now


@pytest.fixture
def phase():
    c = TestClient(app)
    people = []
    for _ in range(3):
        r = c.post(
            "/api/auth/register",
            json={
                "email": uuid.uuid4().hex + "@example.com",
                "password": "test-password",
                "display_name": "Planning fixture",
            },
        )
        assert r.status_code == 201, r.text
        people.append(r.json())
    with SessionLocal.begin() as db:
        db.get(User, uuid.UUID(people[0]["user"]["id"])).role = "admin"
        root = Location(
            name_bn="কাল্পনিক " + uuid.uuid4().hex,
            name_en="Fictional " + uuid.uuid4().hex,
            kind="division",
            slug=uuid.uuid4().hex,
            verification_status="verified",
            source_url="https://example.com/fictional",
            verified_at=now(),
        )
        db.add(root)
        db.flush()
        child = Location(
            name_bn="কাল্পনিক জেলা " + uuid.uuid4().hex,
            name_en="Fictional district " + uuid.uuid4().hex,
            kind="district",
            slug=uuid.uuid4().hex,
            parent_id=root.id,
            verification_status="verified",
            source_url="https://example.com/fictional",
            verified_at=now(),
        )
        db.add(child)
        db.flush()
        areas = [str(root.id), str(child.id)]
    return (
        c,
        areas,
        [{"Authorization": "Bearer " + p["access_token"]} for p in people],
        [uuid.UUID(p["user"]["id"]) for p in people],
    )


def announcement(c, admin, area, start, end, **extra):
    n = c.post(
        "/api/admin/notices",
        headers=admin,
        json={
            "title": "Fictional planning " + uuid.uuid4().hex,
            "body": "Fictional automated testing announcement",
            "publisher": "Fictional office",
            "source_url": "https://example.com/fictional.pdf",
            "published_at": None,
        },
    ).json()
    for action, version in [("verify", 1), ("publish", 2)]:
        r = c.post(
            f"/api/admin/notices/{n['id']}/{action}",
            headers=admin,
            json={"version": version},
        )
        assert r.status_code == 200, r.text
    body = {
        "notice_id": n["id"],
        "location_id": area,
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
        **extra,
    }
    s = c.post("/api/admin/schedules", headers=admin, json=body)
    assert s.status_code == 201, s.text
    sid = s.json()["id"]
    assert (
        c.post(
            f"/api/admin/schedules/{sid}/publish", headers=admin, json={"version": 1}
        ).status_code
        == 200
    )
    return sid, body


def test_checker_union_boundaries_midnight_and_fresh_saved_activity(phase):
    c, areas, (admin, u, v), _ = phase
    t = datetime(2030, 1, 1, 17, 30, tzinfo=UTC)  # 23:30 Dhaka
    sid, body = announcement(c, admin, areas[1], t, t + timedelta(hours=2))
    other, _ = announcement(
        c, admin, areas[1], t + timedelta(hours=1), t + timedelta(hours=3)
    )
    activity = {
        "location_id": areas[1],
        "starts_at": t.isoformat(),
        "ends_at": (t + timedelta(hours=4)).isoformat(),
    }
    assert c.post("/api/activities/check", json=activity).status_code == 401
    result = c.post("/api/activities/check", headers=u, json=activity).json()
    assert result["announced_overlap"] and result["affected_minutes"] == 180
    assert (
        len(result["conflicts"]) == 2 and result["conflicts"][0]["notice"]["source_url"]
    )
    edge = {**activity, "starts_at": (t + timedelta(hours=3)).isoformat()}
    assert (
        c.post("/api/activities/check", headers=u, json=edge).json()["conflicts"] == []
    )
    for invalid in [
        {**activity, "ends_at": activity["starts_at"]},
        {**activity, "starts_at": "2030-01-01T00:00:00"},
    ]:
        assert (
            c.post("/api/activities/check", headers=u, json=invalid).status_code == 422
        )
    saved = c.post(
        "/api/activities", headers=u, json={**activity, "title": "Online exam"}
    )
    assert saved.status_code == 201, saved.text
    aid = saved.json()["id"]
    for verb in ["get", "put", "delete"]:
        kwargs = {"headers": v}
        path = f"/api/activities/{aid}"
        if verb == "put":
            kwargs["json"] = {**activity, "title": "Stolen"}
        if verb == "delete":
            path += "?version=1"
        assert getattr(c, verb)(path, **kwargs).status_code == 404
    assert (
        c.post(
            f"/api/admin/schedules/{sid}/cancel", headers=admin, json={"version": 2}
        ).status_code
        == 422
    )
    assert (
        c.post(
            f"/api/admin/schedules/{sid}/cancel",
            headers=admin,
            json={"version": 2, "reason": "Source cancelled"},
        ).status_code
        == 200
    )
    assert (
        c.get(f"/api/activities/{aid}", headers=u).json()["check"]["affected_minutes"]
        == 120
    )
    revised = {
        **body,
        "notice_id": c.get(
            f"/api/admin/list/schedules?search={other}", headers=admin
        ).json()["items"][0]["notice_id"],
        "starts_at": (t + timedelta(days=1)).isoformat(),
        "ends_at": (t + timedelta(days=1, hours=1)).isoformat(),
        "version": 2,
    }
    assert (
        c.put(f"/api/admin/schedules/{other}", headers=admin, json=revised).status_code
        == 200
    )
    assert (
        c.get(f"/api/activities/{aid}", headers=u).json()["check"]["affected_minutes"]
        == 0
    )
    assert (
        c.post(
            f"/api/admin/schedules/{other}/publish", headers=admin, json={"version": 3}
        ).status_code
        == 200
    )
    assert (
        c.get(f"/api/activities/{aid}", headers=u).json()["check"]["affected_minutes"]
        == 0
    )
    changed = c.put(
        f"/api/activities/{aid}",
        headers=u,
        json={**activity, "title": "New title", "version": 1},
    )
    assert changed.status_code == 200
    assert (
        c.put(
            f"/api/activities/{aid}",
            headers=u,
            json={**activity, "title": "Stale", "version": 1},
        ).status_code
        == 409
    )
    assert c.delete(f"/api/activities/{aid}?version=1", headers=u).status_code == 409
    assert c.delete(f"/api/activities/{aid}?version=2", headers=u).status_code == 204


def test_partial_parent_and_whole_area_coverage(phase):
    c, areas, (admin, u, _), _ = phase
    t = now() + timedelta(days=2)
    announcement(c, admin, areas[1], t, t + timedelta(hours=1))
    body = {
        "location_id": areas[0],
        "starts_at": t.isoformat(),
        "ends_at": (t + timedelta(hours=2)).isoformat(),
    }
    result = c.post("/api/activities/check", headers=u, json=body).json()
    assert (
        not result["announced_overlap"]
        and len(result["uncertain"]) == 1
        and result["affected_minutes"] == 0
    )
    announcement(
        c,
        admin,
        areas[0],
        t,
        t + timedelta(hours=2),
        coverage_scope="entire_administrative_area",
    )
    result = c.post(
        "/api/activities/check", headers=u, json={**body, "location_id": areas[1]}
    ).json()
    assert result["affected_minutes"] == 120
    with SessionLocal.begin() as db:
        db.get(Location, uuid.UUID(areas[1])).updated_at = now() + timedelta(hours=1)
    uncertain = c.post(
        "/api/activities/check", headers=u, json={**body, "location_id": areas[1]}
    ).json()
    assert uncertain["affected_minutes"] == 60 and len(uncertain["uncertain"]) == 1
    with SessionLocal.begin() as db:
        db.get(Location, uuid.UUID(areas[1])).verification_status = "unverified"
    assert (
        c.post(
            "/api/activities/check", headers=u, json={**body, "location_id": areas[1]}
        ).status_code
        == 422
    )


def test_history_math_clipping_daily_union_unknown_and_contradiction():
    t = datetime(2026, 1, 1, 17, 30, tzinfo=UTC)

    def episode(a, b, opened=False):
        return SimpleNamespace(started_at=a, ended_at=b, is_open=opened)

    eps = [
        episode(t, t + timedelta(hours=2)),
        episode(None, t + timedelta(hours=3)),
        episode(t + timedelta(hours=4), None, True),
    ]
    s = history_calculations(eps, t + timedelta(minutes=15), t + timedelta(hours=5))
    assert (
        s["known_minutes"] == 105
        and s["completed"] == 1
        and s["open"] == 1
        and s["incomplete"] == 1
    )
    assert s["average_completed_minutes"] == 120
    assert s["daily"] == [
        {"date": "2026-01-01", "known_minutes": 15},
        {"date": "2026-01-02", "known_minutes": 90},
    ]
    assert s["starting_in_range"] == 1
    overlap = history_calculations(
        [eps[0], episode(t + timedelta(hours=1), t + timedelta(hours=3))],
        t,
        t + timedelta(hours=4),
    )
    assert (
        overlap["known_minutes"] == 180
        and overlap["overlapping_records"]
        and overlap["average_completed_minutes"] is None
    )
    invalid = history_calculations(
        [episode(t, t - timedelta(minutes=1))], t, t + timedelta(hours=1)
    )
    assert invalid["contradictory"] == 1 and invalid["known_minutes"] == 0
    assert (
        history_calculations([], t, t + timedelta(hours=1))["average_completed_minutes"]
        is None
    )
    assert union_intervals(
        [(t, t + timedelta(hours=1)), (t + timedelta(hours=1), t + timedelta(hours=2))]
    ) == [(t, t + timedelta(hours=2))]


def test_history_privacy_repeated_reports_and_moderation_audit(phase, monkeypatch):
    c, areas, (admin, u, v), ids = phase
    monkeypatch.setattr(get_settings(), "report_cooldown_seconds", 0)
    t = now() - timedelta(hours=3)

    def report(headers, kind, minute):
        r = c.post(
            "/api/reports",
            headers=headers,
            json={
                "location_id": areas[1],
                "kind": kind,
                "observed_at": (t + timedelta(minutes=minute)).isoformat(),
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        assert r.status_code == 201, r.text
        return r.json()

    report(u, "power_off", 0)
    report(u, "still_off", 30)
    back = report(u, "power_back", 60)
    report(v, "power_off", 0)
    report(v, "power_back", 120)
    query = {"location_id": areas[1], "start": t.isoformat(), "end": now().isoformat()}
    h = c.get("/api/history", headers=u, params=query)
    assert "no-store" in h.headers["cache-control"]
    assert h.json()["summary"]["known_minutes"] == 60
    assert h.json()["total"] == 1 and h.json()["items"][0]["accepted_observations"] == 3
    assert (
        c.get("/api/history", headers=v, params=query).json()["summary"][
            "known_minutes"
        ]
        == 120
    )
    r = c.post(
        f"/api/admin/reports/{back['id']}/moderate",
        headers=admin,
        json={
            "version": 1,
            "state": "rejected",
            "reason": "Restoration observation disputed",
        },
    )
    assert r.status_code == 200, r.text
    assert (
        c.post(
            f"/api/admin/reports/{back['id']}/moderate",
            headers=admin,
            json={"version": 1, "state": "accepted", "reason": "Stale decision"},
        ).status_code
        == 409
    )
    s = c.get("/api/history", headers=u, params=query).json()["summary"]
    assert (
        s["known_minutes"] == 0
        and s["open"] == 1
        and s["average_completed_minutes"] is None
    )
    with SessionLocal() as db:
        original = db.get(Report, uuid.UUID(back["id"]))
        assert (
            original.observed_at == t + timedelta(minutes=60)
            and original.kind == "power_back"
        )
        audit = db.scalars(
            select(EvidenceAudit).where(
                EvidenceAudit.entity_id == original.id,
                EvidenceAudit.action == "changes",
            )
        ).all()
        assert any(
            a.snapshot["changes"].get("moderation")
            == {"before": "accepted", "after": "rejected"}
            for a in audit
        )
    assert (
        c.get(
            "/api/history", headers=u, params={**query, "start": "2026-01-01T00:00:00"}
        ).status_code
        == 422
    )
    for params in [{"page_size": 101}, {"page": 0}, {"sort": "sql injection"}]:
        assert (
            c.get("/api/history", headers=u, params={**query, **params}).status_code
            == 422
        )


def test_admin_lists_counts_permissions_concurrency_audit(phase):
    c, areas, (admin, u, _), _ = phase
    for path in [
        "/api/admin/overview",
        "/api/admin/offices",
        "/api/admin/list/notices",
        "/api/admin/list/audit",
    ]:
        assert c.get(path, headers=u).status_code == 403
    t = now() + timedelta(days=3)
    sid, body = announcement(c, admin, areas[1], t, t + timedelta(hours=1))
    result = c.get(
        "/api/admin/list/schedules",
        headers=admin,
        params={
            "location_id": areas[1],
            "status": "published",
            "office": "Fictional office",
            "category": "maintenance",
            "start": t.isoformat(),
            "page_size": 1,
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["total"] == 1 and result.json()["items"][0]["id"] == sid
    for params in [
        {"sort": "starts_at;DROP TABLE users"},
        {"page_size": 101},
        {"page": 0},
        {"status": "accepted"},
        {"start": "2026-01-01T00:00:00"},
    ]:
        assert (
            c.get("/api/admin/list/schedules", headers=admin, params=params).status_code
            == 422
        )

    def change(_):
        with TestClient(app) as client:
            return client.put(
                f"/api/admin/schedules/{sid}",
                headers=admin,
                json={**body, "version": 2},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(change, range(2))) == [200, 409]
    audits = c.get(
        "/api/admin/list/audit", headers=admin, params={"search": sid}
    ).json()
    assert any(
        x["action"] == "changes" and "lifecycle" in x["snapshot"]["changes"]
        for x in audits["items"]
    )
    assert (
        c.delete(f"/api/admin/schedules/{sid}?version=3", headers=admin).status_code
        == 409
    )
    # Defaults are deterministic; ties use ID, totals use the identical predicates.
    first = c.get("/api/admin/list/audit?sort=oldest&page_size=1", headers=admin).json()
    again = c.get("/api/admin/list/audit?sort=oldest&page_size=1", headers=admin).json()
    assert first == again
    assert (
        c.get("/api/admin/overview", headers=admin).json()["candidate_events_supported"]
        is False
    )


def test_location_reference_deactivation_versions_and_event_independence(phase):
    c, areas, (admin, u, _), _ = phase
    t = now() - timedelta(hours=2)
    activity = {
        "title": "Reference guard",
        "location_id": areas[1],
        "starts_at": t.isoformat(),
        "ends_at": (t + timedelta(hours=1)).isoformat(),
    }
    assert (
        c.post(
            "/api/activities",
            headers=u,
            json={**activity, "user_id": str(uuid.uuid4())},
        ).status_code
        == 422
    )
    assert c.post("/api/activities", headers=u, json=activity).status_code == 201
    assert (
        c.delete(
            f"/api/admin/locations/{areas[1]}?version=1", headers=admin
        ).status_code
        == 409
    )
    report = c.post(
        "/api/reports",
        headers=u,
        json={
            "location_id": areas[1],
            "kind": "power_off",
            "observed_at": t.isoformat(),
            "idempotency_key": str(uuid.uuid4()),
        },
    ).json()
    event = c.post(
        "/api/admin/events",
        headers=admin,
        json={
            "location_id": areas[1],
            "started_at": t.isoformat(),
            "start_evidence": "Fictional event start evidence",
        },
    ).json()
    decision = {
        "version": 1,
        "state": "accepted",
        "reason": "Reviewed association only",
        "candidate_event_id": event["id"],
    }
    assert (
        c.post(
            f"/api/admin/reports/{report['id']}/moderate", headers=admin, json=decision
        ).status_code
        == 200
    )
    assert (
        c.post(
            f"/api/admin/events/{event['id']}/restore",
            headers=admin,
            json={
                "version": 1,
                "restored_at": (t + timedelta(hours=1)).isoformat(),
                "evidence": "Fictional broader restoration evidence",
            },
        ).status_code
        == 200
    )
    h = c.get(
        "/api/history",
        headers=u,
        params={
            "location_id": areas[1],
            "start": t.isoformat(),
            "end": now().isoformat(),
        },
    ).json()
    assert h["summary"]["open"] == 1 and h["summary"]["known_minutes"] == 0
    assert h["items"][0]["reviewed_observations"] == 1
    assert (
        c.post(
            f"/api/admin/reports/{report['id']}/moderate",
            headers=admin,
            json={**decision, "version": 2, "candidate_event_id": None},
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        assert db.get(Report, uuid.UUID(report["id"])).candidate_event_id is None
    suspension = {"version": 1, "reason": "Boundary review required"}
    assert (
        c.post(
            f"/api/admin/locations/{areas[1]}/deactivate", headers=u, json=suspension
        ).status_code
        == 403
    )
    assert (
        c.post(
            f"/api/admin/locations/{areas[1]}/deactivate",
            headers=admin,
            json=suspension,
        ).status_code
        == 200
    )
    assert (
        c.post(
            f"/api/admin/locations/{areas[1]}/deactivate",
            headers=admin,
            json=suspension,
        ).status_code
        == 409
    )
    detail = c.get(f"/api/locations/{areas[1]}").json()
    assert detail["verification_status"] == "unverified" and detail["source_url"]
    assert (
        c.get(
            "/api/history",
            headers=u,
            params={
                "location_id": areas[1],
                "start": t.isoformat(),
                "end": now().isoformat(),
            },
        ).json()["total"]
        == 1
    )


def test_repeated_restorations_keep_first_end_and_one_episode(phase, monkeypatch):
    c, areas, (admin, u, _), _ = phase
    monkeypatch.setattr(get_settings(), "report_cooldown_seconds", 0)
    t = now() - timedelta(hours=2)
    ids = []
    for kind, minute in [
        ("power_off", 0),
        ("power_off", 10),
        ("still_off", 20),
        ("power_back", 30),
        ("power_back", 40),
    ]:
        r = c.post(
            "/api/reports",
            headers=u,
            json={
                "location_id": areas[1],
                "kind": kind,
                "observed_at": (t + timedelta(minutes=minute)).isoformat(),
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    query = {"location_id": areas[1], "start": t.isoformat(), "end": now().isoformat()}
    h = c.get("/api/history", headers=u, params=query).json()
    assert h["total"] == 1 and h["summary"]["known_minutes"] == 30
    assert h["items"][0]["accepted_observations"] == 5
    # Replay through moderation's rebuilding service retains identical counting.
    assert (
        c.post(
            f"/api/admin/reports/{ids[0]}/moderate",
            headers=admin,
            json={
                "version": 1,
                "state": "accepted",
                "reason": "Confirm original observation",
            },
        ).status_code
        == 200
    )
    rebuilt = c.get("/api/history", headers=u, params=query).json()
    assert rebuilt["total"] == 1 and rebuilt["summary"]["known_minutes"] == 30


def test_office_and_feeder_registry_review_permissions_references_and_audit(phase):
    c, areas, (admin, u, _), _ = phase
    name = "Fictional test office " + uuid.uuid4().hex
    body = {
        "name_bn": name,
        "name_en": name,
        "source_url": "https://example.com/fictional-office",
    }
    assert (
        c.post("/api/admin/registry/offices", headers=u, json=body).status_code == 403
    )
    assert c.get("/api/admin/registry/mappings", headers=u).status_code == 403
    assert (
        c.post(
            "/api/admin/registry/offices",
            headers=admin,
            json={**body, "verification_status": "verified"},
        ).status_code
        == 422
    )
    office = c.post("/api/admin/registry/offices", headers=admin, json=body)
    assert office.status_code == 201, office.text
    oid = office.json()["id"]
    mapping = {
        "office_id": oid,
        "location_id": areas[1],
        "feeder_name": "Fictional feeder test",
        "coverage_description": "Fictional source names this coverage explicitly",
        "source_url": "https://example.com/fictional-coverage",
    }
    assert (
        c.post("/api/admin/registry/mappings", headers=admin, json=mapping).status_code
        == 422
    )
    assert (
        c.post(
            f"/api/admin/registry/offices/{oid}/verify",
            headers=admin,
            json={"version": 1, "reason": "Source reviewed in test only"},
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/api/admin/registry/offices",
            headers=admin,
            json={**body, "name_en": name.upper()},
        ).status_code
        == 409
    )
    m = c.post("/api/admin/registry/mappings", headers=admin, json=mapping)
    assert m.status_code == 201, m.text
    mid = m.json()["id"]
    assert (
        c.post(
            "/api/admin/registry/mappings",
            headers=admin,
            json={**mapping, "feeder_name": " FICTIONAL FEEDER TEST "},
        ).status_code
        == 409
    )
    assert (
        c.post(
            f"/api/admin/registry/mappings/{mid}/verify",
            headers=admin,
            json={"version": 1, "reason": "Coverage source reviewed"},
        ).status_code
        == 200
    )
    rows = c.get(
        "/api/admin/registry/mappings",
        headers=admin,
        params={
            "office_id": oid,
            "location_id": areas[1],
            "status": "verified",
            "sort": "name",
            "page_size": 1,
        },
    ).json()
    assert rows["total"] == 1 and rows["items"][0]["usable"]
    assert rows["items"][0]["office_name"] == name
    assert (
        c.delete(
            f"/api/admin/registry/mappings/{mid}?version=2", headers=admin
        ).status_code
        == 409
    )
    assert (
        c.delete(
            f"/api/admin/registry/offices/{oid}?version=2", headers=admin
        ).status_code
        == 409
    )
    assert (
        c.delete(
            f"/api/admin/locations/{areas[1]}?version=1", headers=admin
        ).status_code
        == 409
    )
    for params in [
        {"sort": "oops"},
        {"page_size": 101},
        {"page": 0},
        {"status": "official"},
    ]:
        assert (
            c.get(
                "/api/admin/registry/mappings", headers=admin, params=params
            ).status_code
            == 422
        )
    # Editing the office invalidates all claims tied to its identity.
    assert (
        c.put(
            f"/api/admin/registry/offices/{oid}",
            headers=admin,
            json={**body, "version": 2, "name_bn": name + " revised"},
        ).status_code
        == 200
    )
    stale = c.post(
        f"/api/admin/registry/mappings/{mid}/verify",
        headers=admin,
        json={"version": 2, "reason": "Stale review attempt"},
    )
    assert stale.status_code == 409
    row = c.get(
        "/api/admin/registry/mappings", headers=admin, params={"search": mid}
    ).json()["items"][0]
    assert (
        row["verification_status"] == "unverified"
        and not row["usable"]
        and row["version"] == 3
    )
    assert (
        c.post(
            f"/api/admin/registry/offices/{oid}/verify",
            headers=admin,
            json={"version": 3, "reason": "Revised office reviewed"},
        ).status_code
        == 200
    )
    assert (
        c.post(
            f"/api/admin/registry/mappings/{mid}/verify",
            headers=admin,
            json={"version": 3, "reason": "Revised coverage reviewed"},
        ).status_code
        == 200
    )
    assert (
        c.post(
            f"/api/admin/locations/{areas[1]}/deactivate",
            headers=admin,
            json={"version": 1, "reason": "Boundary review required"},
        ).status_code
        == 200
    )
    row = c.get(
        "/api/admin/registry/mappings", headers=admin, params={"search": mid}
    ).json()["items"][0]
    assert row["verification_status"] == "unverified" and not row["usable"]
    audit = c.get(
        "/api/admin/list/audit", headers=admin, params={"search": mid}
    ).json()["items"]
    assert any(
        x["entity_type"] == "feeder_mappings" and x["action"] == "changes"
        for x in audit
    )
    draft = c.post(
        "/api/admin/registry/offices",
        headers=admin,
        json={**body, "name_en": name + " removable"},
    ).json()
    assert (
        c.delete(
            f"/api/admin/registry/offices/{draft['id']}?version=1", headers=admin
        ).status_code
        == 204
    )


def test_history_snapshot_does_not_mix_concurrent_versions(phase, monkeypatch):
    from app import planning
    from app.models import PersonalEpisode

    c, areas, (_, u, _), ids = phase
    t = now() - timedelta(hours=3)

    def insert_episode(offset):
        with SessionLocal.begin() as db:
            db.add(
                PersonalEpisode(
                    user_id=ids[1],
                    location_id=uuid.UUID(areas[1]),
                    started_at=t + timedelta(minutes=offset),
                    ended_at=t + timedelta(minutes=offset + 10),
                    last_observed_at=t + timedelta(minutes=offset + 10),
                    is_open=False,
                )
            )

    insert_episode(0)
    original = planning.history_calculations
    inserted = False

    def concurrent_change(*args):
        nonlocal inserted
        if not inserted:
            insert_episode(60)
            inserted = True
        return original(*args)

    monkeypatch.setattr(planning, "history_calculations", concurrent_change)
    query = {"location_id": areas[1], "start": t.isoformat(), "end": now().isoformat()}
    first = c.get("/api/history", headers=u, params=query).json()
    assert (
        first["summary"]["recorded_episodes"]
        == first["total"]
        == len(first["items"])
        == 1
    )
    second = c.get("/api/history", headers=u, params=query).json()
    assert second["total"] == 2 and second["summary"]["known_minutes"] == 20


def test_exact_expiry_boundaries_and_malformed_password_hash(phase, monkeypatch):
    from app import auth, security
    from app.models import PasswordReset, RefreshSession

    c, _, (_, _, v), ids = phase
    instant = now()
    raw = c.cookies.get("gridwatch_refresh")
    csrf = c.cookies.get("gridwatch_csrf")
    with SessionLocal.begin() as db:
        session = db.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == security.digest(raw)
            )
        )
        session.expires_at = instant
        db.add(
            PasswordReset(
                user_id=ids[2],
                token_hash=security.digest("expired-reset-fixture"),
                expires_at=instant,
            )
        )
        account = db.get(User, ids[1])
        account.password_hash = "malformed fixture hash"
        email = account.email
    monkeypatch.setattr(security, "now", lambda: instant)
    monkeypatch.setattr(auth, "now", lambda: instant)
    assert c.get("/api/auth/me", headers=v).status_code == 401
    assert (
        c.post(
            "/api/auth/refresh",
            headers={"Origin": get_settings().frontend_url, "X-CSRF-Token": csrf},
        ).status_code
        == 401
    )
    assert (
        c.post(
            "/api/auth/password-reset/confirm",
            json={"token": "expired-reset-fixture", "password": "valid-password"},
        ).status_code
        == 400
    )
    assert (
        c.post(
            "/api/auth/login", json={"email": email, "password": "valid-password"}
        ).status_code
        == 401
    )


def test_future_observation_is_pending_and_never_restores_early(phase, monkeypatch):
    from app import evidence

    c, areas, (admin, u, _), _ = phase
    instant = now()
    monkeypatch.setattr(evidence, "now", lambda: instant)
    off = {
        "location_id": areas[1],
        "kind": "power_off",
        "observed_at": (instant - timedelta(minutes=10)).isoformat(),
        "idempotency_key": str(uuid.uuid4()),
    }
    assert c.post("/api/reports", headers=u, json=off).status_code == 201
    future = {
        **off,
        "kind": "power_back",
        "observed_at": (instant + timedelta(minutes=1)).isoformat(),
        "idempotency_key": str(uuid.uuid4()),
    }
    r = c.post("/api/reports", headers=u, json=future)
    assert r.status_code == 201 and r.json()["moderation"] == "pending"
    key = r.json()["id"]
    decision = {"version": 1, "state": "accepted", "reason": "Observation time checked"}
    assert (
        c.post(
            f"/api/admin/reports/{key}/moderate", headers=admin, json=decision
        ).status_code
        == 422
    )
    query = {
        "location_id": areas[1],
        "start": (instant - timedelta(hours=1)).isoformat(),
        "end": (instant + timedelta(hours=1)).isoformat(),
    }
    assert c.get("/api/history", headers=u, params=query).json()["summary"]["open"] == 1
    monkeypatch.setattr(evidence, "now", lambda: instant + timedelta(minutes=2))
    assert (
        c.post(
            f"/api/admin/reports/{key}/moderate", headers=admin, json=decision
        ).status_code
        == 200
    )
    assert (
        c.get("/api/history", headers=u, params=query).json()["summary"][
            "known_minutes"
        ]
        == 11
    )


def test_normalized_length_validation_and_whitespace_review_reasons(phase):
    c, areas, (admin, _, _), _ = phase
    expanded = "ﬃ" * 160
    office = {
        "name_bn": "Fictional office",
        "name_en": expanded,
        "source_url": "https://example.com/test",
    }
    assert (
        c.post("/api/admin/registry/offices", headers=admin, json=office).status_code
        == 422
    )
    location = {
        "name_bn": "Fictional location",
        "name_en": expanded,
        "slug": uuid.uuid4().hex,
        "kind": "division",
    }
    assert (
        c.post("/api/admin/locations", headers=admin, json=location).status_code == 422
    )
    assert (
        c.post(
            f"/api/admin/locations/{areas[1]}/deactivate",
            headers=admin,
            json={"version": 1, "reason": "     "},
        ).status_code
        == 422
    )


def test_concurrent_saved_area_is_not_cascade_deleted(phase):
    import time

    from fastapi import HTTPException
    from sqlalchemy import text

    from app.api import delete_location
    from app.models import SavedArea

    _, areas, _, ids = phase
    marker = "gridwatch_delete_" + uuid.uuid4().hex
    location_id = uuid.UUID(areas[1])
    writer = SessionLocal()
    writer.add(SavedArea(user_id=ids[1], location_id=location_id))
    writer.flush()  # Holds a foreign-key KEY SHARE lock until commit.

    def remove():
        with SessionLocal() as db:
            db.execute(
                text("SELECT set_config('application_name',:name,false)"),
                {"name": marker},
            )
            try:
                delete_location(
                    location_id=location_id,
                    version=1,
                    db=db,
                    admin=SimpleNamespace(id=ids[0]),
                )
                return 204
            except HTTPException as e:
                return e.status_code

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            task = pool.submit(remove)
            waiting = False
            with SessionLocal() as monitor:
                for _ in range(100):
                    monitor.execute(text("SELECT pg_stat_clear_snapshot()"))
                    waiting = bool(
                        monitor.scalar(
                            text(
                                "SELECT count(*) FROM pg_stat_activity WHERE application_name=:name AND wait_event_type='Lock'"
                            ),
                            {"name": marker},
                        )
                    )
                    if waiting:
                        break
                    time.sleep(0.01)
            writer.commit()
            assert waiting, "Delete did not reach the expected foreign-key lock"
            assert task.result(timeout=5) == 409
        with SessionLocal() as db:
            assert db.get(SavedArea, {"user_id": ids[1], "location_id": location_id})
            assert db.get(Location, location_id)
    finally:
        writer.rollback()
        writer.close()
