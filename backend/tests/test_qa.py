"""Independent Section 11 numeric oracles and a bounded local query benchmark."""

import json
import os
import platform
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from time import perf_counter
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import delete, event
from test_planning_admin import announcement
from test_planning_admin import phase as phase

from app.db import SessionLocal, engine
from app.main import app
from app.models import Notice, PersonalEpisode, Schedule
from app.planning import history_calculations


def test_exact_numeric_oracles_and_persisted_private_history(phase):
    c, areas, (admin, a, b), users = phase
    # 14:00–15:00 and 14:30–15:30 Bangladesh time: exactly 90 union minutes.
    t = datetime(2030, 1, 1, 8, 0, tzinfo=UTC)
    for offset in (0, 30):
        announcement(
            c,
            admin,
            areas[1],
            t + timedelta(minutes=offset),
            t + timedelta(minutes=offset + 60),
        )
    check = c.post(
        "/api/activities/check",
        headers=a,
        json={
            "location_id": areas[1],
            "starts_at": t.isoformat(),
            "ends_at": (t + timedelta(hours=2)).isoformat(),
        },
    )
    assert check.status_code == 200
    assert check.json()["affected_minutes"] == 90
    boundary = c.post(
        "/api/activities/check",
        headers=a,
        json={
            "location_id": areas[1],
            "starts_at": (t + timedelta(minutes=90)).isoformat(),
            "ends_at": (t + timedelta(hours=2)).isoformat(),
        },
    ).json()
    assert boundary["affected_minutes"] == 0 and boundary["conflicts"] == []
    # Independent wall-clock oracle: 23:50–00:20 = 10 + 20 minutes.
    start = datetime(2025, 1, 1, 17, 50, tzinfo=UTC)
    end = start + timedelta(minutes=30)
    with SessionLocal.begin() as db:
        for user, began, ended, opened, observed in [
            (users[1], start, end, False, end),
            (users[1], end + timedelta(hours=1), None, True, end + timedelta(hours=1)),
            (users[1], None, end + timedelta(hours=2), False, end + timedelta(hours=2)),
            (
                users[2],
                start,
                start + timedelta(hours=3),
                False,
                start + timedelta(hours=3),
            ),
        ]:
            db.add(
                PersonalEpisode(
                    user_id=user,
                    location_id=uuid.UUID(areas[1]),
                    started_at=began,
                    ended_at=ended,
                    is_open=opened,
                    last_observed_at=observed,
                )
            )
    params = {
        "location_id": areas[1],
        "start": "2025-01-01T00:00:00+06:00",
        "end": "2025-01-03T00:00:00+06:00",
    }
    result = c.get("/api/history", params=params, headers=a).json()
    summary = result["summary"]
    assert summary["recorded_episodes"] == 3
    assert summary["known_minutes"] == 30 and summary["average_completed_minutes"] == 30
    assert summary["completed"] == summary["open"] == summary["incomplete"] == 1
    assert summary["daily"] == [
        {"date": "2025-01-01", "known_minutes": 10},
        {"date": "2025-01-02", "known_minutes": 20},
    ]
    other = c.get("/api/history", params=params, headers=b).json()
    assert other["summary"]["known_minutes"] == 180
    clipped = history_calculations(
        [SimpleNamespace(started_at=start, ended_at=end, is_open=False)],
        start + timedelta(minutes=5),
        end - timedelta(minutes=5),
    )
    assert clipped["known_minutes"] == 20 and clipped["average_completed_minutes"] == 30


def test_source_protocol_credentials_and_sql_input(phase):
    c, areas, (admin, a, _), _ = phase
    for source in [
        "javascript:alert(1)",
        "data:text/html,hello",
        "http://example.com",
        "https://user:private@example.com/file.pdf",
    ]:
        r = c.post(
            "/api/admin/notices",
            headers=admin,
            json={
                "title": "QA rejected source",
                "body": "Fictional source validation only",
                "publisher": "Fictional QA",
                "source_url": source,
                "published_at": None,
            },
        )
        assert r.status_code == 422
        assert "private" not in r.text
    for endpoint in ["/api/admin/list/notices", "/api/activities"]:
        r = c.get(
            endpoint, headers=admin, params={"search": "' OR 1=1 --", "sort": "newest"}
        )
        assert r.status_code == 200 and r.json()["total"] == 0
    assert c.get("/api/admin/list/notices", headers=a).status_code == 403
    assert (
        c.get(
            "/api/admin/list/notices",
            headers=admin,
            params={"sort": "id; DROP TABLE users"},
        ).status_code
        == 422
    )


def test_bounded_schedule_listing_benchmark(phase):
    c, areas, (admin, _, _), _ = phase
    t = datetime(2030, 1, 1, tzinfo=UTC)
    sid, _ = announcement(c, admin, areas[1], t, t + timedelta(hours=1))
    with SessionLocal.begin() as db:
        base = db.get(Schedule, uuid.UUID(sid))
        notice_id = base.notice_id
        title = db.get(Notice, notice_id).title
        for offset in range(1, 1000):
            db.add(
                Schedule(
                    notice_id=notice_id,
                    location_id=base.location_id,
                    starts_at=t + timedelta(minutes=offset),
                    ends_at=t + timedelta(minutes=offset + 60),
                    lifecycle="published",
                    coverage=base.coverage,
                )
            )
    count = [0]
    lock = Lock()

    def observed(*args):
        with lock:
            count[0] += 1

    def measure(_):
        instant = perf_counter()
        with TestClient(app) as client:
            response = client.get(
                "/api/schedules", params={"search": title, "page_size": 100}
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1000 and len(payload["items"]) == 100
        assert all(
            x["notice"]["source_url"].startswith("https://") for x in payload["items"]
        )
        return round((perf_counter() - instant) * 1000, 2)

    try:
        measure(0)  # Warm connection pools before the bounded 5-request measurement.
        event.listen(engine, "before_cursor_execute", observed)
        try:
            with ThreadPoolExecutor(max_workers=5) as pool:
                timings = list(pool.map(measure, range(5)))
        finally:
            event.remove(engine, "before_cursor_execute", observed)
        assert count[0] <= 15  # Count + page + batch metadata; never 100 lookups.
        result = {
            "environment": f"local {platform.system()} test environment (FastAPI TestClient)",
            "logical_cpus": os.cpu_count(),
            "dataset_schedules": 1000,
            "concurrency": 5,
            "requests": 5,
            "page_size": 100,
            "sql_queries_total": count[0],
            "latency_ms": timings,
            "mean_ms": round(sum(timings) / 5, 2),
            "max_ms": max(timings),
        }
        (Path(tempfile.gettempdir()) / "gridwatch-qa-performance.json").write_text(
            json.dumps(result, indent=2)
        )
    finally:
        with SessionLocal.begin() as db:
            db.execute(delete(Schedule).where(Schedule.notice_id == notice_id))
            db.execute(delete(Notice).where(Notice.id == notice_id))


def test_legacy_collection_endpoints_are_bounded_owned_and_stable(phase):
    from app.models import Location, SavedArea

    c, areas, (_, a, b), users = phase
    with SessionLocal.begin() as db:
        for number in range(105):
            loc = Location(
                name_bn=f"কাল্পনিক QA {number:03}",
                name_en=f"Fictional QA bounded {number:03}",
                slug="qa-bounded-" + uuid.uuid4().hex,
                kind="district",
                parent_id=uuid.UUID(areas[0]),
            )
            db.add(loc)
            db.flush()
            db.add(
                SavedArea(user_id=users[1], location_id=loc.id, is_default=number == 0)
            )
        start = datetime(2025, 1, 1, tzinfo=UTC)
        for number in range(25):
            t = start + timedelta(hours=number)
            db.add(
                PersonalEpisode(
                    user_id=users[1],
                    location_id=uuid.UUID(areas[1]),
                    started_at=t,
                    ended_at=t + timedelta(minutes=20),
                    last_observed_at=t + timedelta(minutes=20),
                    is_open=False,
                )
            )
    for endpoint, total, default, second in [
        ("/api/saved-areas", 105, 100, 5),
        ("/api/me/episodes", 25, 20, 5),
    ]:
        first = c.get(endpoint, headers=a).json()
        next_page = c.get(endpoint, headers=a, params={"page": 2}).json()
        assert first["total"] == total and len(first["items"]) == default
        assert len(next_page["items"]) == second
        assert {r["id"] for r in first["items"]}.isdisjoint(
            {r["id"] for r in next_page["items"]}
        )
        assert c.get(endpoint, headers=a, params={"page": 2}).json() == next_page
        assert c.get(endpoint, headers=b).json()["total"] == 0
        for params in [{"page": 0}, {"page_size": 101}]:
            assert c.get(endpoint, headers=a, params=params).status_code == 422
