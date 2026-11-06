"""Supplied SQLite remains source data; census/current and user records stay separate."""

import hashlib
import os
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.location_catalog import import_catalog
from app.main import app
from app.models import (
    DirectoryDataset,
    DirectoryPlace,
    FeederMapping,
    Location,
    Notice,
    Report,
    Schedule,
    User,
)
from app.supplied_directory import SOURCE_FILE, import_supplied_directory, read_source

ROOT = Path(__file__).resolve().parents[2]
PYTHON = (
    ROOT / "backend/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
)


@pytest.fixture
def directory_engine():
    url = make_url(get_settings().database_url)
    assert url.database.startswith("gridwatch_test_")
    name = "gridwatch_directoryqa_" + uuid.uuid4().hex[:12]
    subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "createdb", "-U", "gridwatch", name],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    private_url = url.set(database=name).render_as_string(hide_password=False)
    engine = None
    try:
        subprocess.run(
            [str(PYTHON), "-m", "alembic", "upgrade", "head"],
            cwd=ROOT / "backend",
            env=dict(os.environ, DATABASE_URL=private_url),
            check=True,
            capture_output=True,
        )
        engine = create_engine(private_url)
        yield engine
    finally:
        if engine:
            engine.dispose()
        subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "db",
                "dropdb",
                "-U",
                "gridwatch",
                "--force",
                name,
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )


def test_read_only_source_counts_links_and_no_supplied_instructions_executed():
    before = hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest()
    checksum, data = read_source()
    assert (
        checksum
        == before
        == "452a74777756002e59e39c36b4d47a91faccf764ae8006590aaaabe7cc8fb6a9"
    )
    assert len(data["locations"]) == 428 and len(data["census_locations"]) == 5765
    assert len(data["sources"]) == 19 and len(data["review_queue"]) == 4
    assert len(data["electricity_references"]) == 32
    assert any(row["kind"] == "census_thana" for row in data["census_locations"])
    assert any("SELECT" in row["details"] for row in data["guide"])
    assert hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("change", ["cycle", "url", "view"])
def test_untrusted_source_is_bounded_and_views_are_not_queried(tmp_path, change):
    copied = tmp_path / "input.sqlite"
    shutil.copyfile(SOURCE_FILE, copied)
    with sqlite3.connect(copied) as db:
        if change == "cycle":
            db.execute("UPDATE locations SET parent_id=id WHERE id='sylhet-division'")
        elif change == "url":
            db.execute("UPDATE sources SET url='javascript:alert(1)' WHERE id='up'")
        else:
            db.execute("DROP TABLE guide")
            db.execute(
                "CREATE VIEW guide AS SELECT 'scope' AS topic,'untrusted instructions' AS details"
            )
    with pytest.raises(ValueError):
        read_source(copied)


def test_import_is_idempotent_preserves_current_ids_and_no_outage_facts(
    directory_engine,
):
    with Session(directory_engine) as db, db.begin():
        import_catalog(db)
        ward = db.scalar(select(Location).where(Location.slug == "sylhet-city-ward-01"))
        original = (ward.id, ward.name_bn, ward.version, ward.verified_at)
        result = import_supplied_directory(db)
        assert result["created_locations"] == 383
        assert db.scalar(select(func.count()).select_from(Location)) == 428
        assert db.scalar(select(func.count()).select_from(DirectoryPlace)) == 6193
        assert import_supplied_directory(db)["already_imported"]
        assert db.scalar(select(func.count()).select_from(DirectoryDataset)) == 1
        assert (ward.id, ward.name_bn, ward.version, ward.verified_at) == original
        assert (
            db.scalar(
                select(func.count())
                .select_from(Location)
                .where(Location.name_en.is_(None))
            )
            == 379
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Location)
                .where(Location.verification_status == "unverified")
            )
            == 9
        )
        for model in [Report, Schedule, Notice, User, FeederMapping]:
            assert db.scalar(select(func.count()).select_from(model)) == 0
        ward.verification_status = "unverified"
        db.flush()
        import_supplied_directory(db)
        assert ward.verification_status == "unverified"


def test_directory_search_breadcrumbs_history_permissions_and_paging(directory_engine):
    with Session(directory_engine) as db, db.begin():
        import_catalog(db)
        import_supplied_directory(db)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                summary = client.get("/api/directory/summary").json()
                assert summary["counts"] == {"portal": 428, "census2022": 5765}
                assert len(summary["sources"]) == 19
                page = client.get(
                    "/api/directory",
                    params={"branch": "census2022", "search": "আম্বরখানা"},
                ).json()
                assert page["total"] > 0
                assert all(
                    row["census_year"] == 2022
                    and row["location_id"] is None
                    and not row["reportable"]
                    for row in page["items"]
                )
                assert any(
                    a["kind"] == "census_thana" for a in page["items"][0]["ancestors"]
                )
                portal = client.get(
                    "/api/directory", params={"search": "বালাগঞ্জ", "kind": "upazila"}
                ).json()
                assert portal["total"] == 1 and portal["items"][0]["reportable"]
                assert [a["kind"] for a in portal["items"][0]["ancestors"]] == [
                    "division",
                    "district",
                ]
                assert (
                    client.get("/api/locations", params={"search": "আম্বরখানা"}).json()[
                        "total"
                    ]
                    == 0
                )
                for term in ["%", "_"]:
                    assert (
                        client.get("/api/directory", params={"search": term}).json()[
                            "total"
                        ]
                        == 0
                    )
                a = client.get(
                    "/api/directory",
                    params={"branch": "census2022", "kind": "village", "page_size": 50},
                ).json()
                b = client.get(
                    "/api/directory",
                    params={
                        "branch": "census2022",
                        "kind": "village",
                        "page_size": 50,
                        "page": 2,
                    },
                ).json()
                assert a["total"] == b["total"] == 3318
                assert not {r["id"] for r in a["items"]} & {r["id"] for r in b["items"]}
                for params in [
                    {"page": 0},
                    {"page_size": 51},
                    {"branch": "merged"},
                    {"branch": "portal", "kind": "census_thana"},
                    {"search": "x" * 101},
                ]:
                    assert (
                        client.get("/api/directory", params=params).status_code == 422
                    )
                assert (
                    client.get(
                        "/api/directory",
                        params={
                            "branch": "portal",
                            "parent_id": page["items"][0]["id"],
                        },
                    ).status_code
                    == 422
                )
        finally:
            app.dependency_overrides.clear()


def test_missing_english_names_preserve_uniqueness_and_safe_downgrade(directory_engine):
    with Session(directory_engine) as db, db.begin():
        db.add_all(
            [
                Location(
                    name_bn="অন্য বিভাগ এক",
                    name_en=None,
                    kind="division",
                    slug="null-one",
                ),
                Location(
                    name_bn="অন্য বিভাগ দুই",
                    name_en=None,
                    kind="division",
                    slug="null-two",
                ),
            ]
        )
    with pytest.raises(IntegrityError):
        with Session(directory_engine) as db, db.begin():
            db.add(
                Location(
                    name_bn="অন্য বিভাগ এক",
                    name_en=None,
                    kind="division",
                    slug="null-duplicate",
                )
            )
    result = subprocess.run(
        [str(PYTHON), "-m", "alembic", "downgrade", "0006"],
        cwd=ROOT / "backend",
        env=dict(
            os.environ,
            DATABASE_URL=directory_engine.url.render_as_string(hide_password=False),
        ),
        capture_output=True,
    )
    assert result.returncode != 0
    with directory_engine.connect() as db:
        assert (
            db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0007"
        )
        assert db.execute(text("SELECT COUNT(*) FROM locations")).scalar_one() == 2


def test_historical_reference_cannot_be_used_as_saved_or_report_location(
    directory_engine,
):
    with Session(directory_engine) as db, db.begin():
        import_catalog(db)
        import_supplied_directory(db)
        historic = db.scalar(
            select(DirectoryPlace).where(DirectoryPlace.branch == "census2022")
        )
        historic_id = historic.id
        current = db.scalar(
            select(Location).where(Location.slug == "sylhet-city-ward-01")
        )
        current_id = current.id

    def session():
        with Session(directory_engine) as db:
            yield db

    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/auth/register",
                json={
                    "email": "isolated-directory-user@example.com",
                    "password": "isolated-directory-only-password",
                    "display_name": "Fictional directory test user",
                },
            )
            assert login.status_code == 201
            headers = {"Authorization": "Bearer " + login.json()["access_token"]}
            assert (
                client.post(
                    f"/api/saved-areas/{historic_id}", headers=headers
                ).status_code
                == 404
            )
            assert (
                client.post(
                    f"/api/saved-areas/{current_id}", headers=headers
                ).status_code
                == 201
            )
    finally:
        app.dependency_overrides.clear()


def test_unified_search_names_ancestor_context_ranking_and_source_separation(
    directory_engine,
):
    with Session(directory_engine) as db, db.begin():
        import_catalog(db)
        import_supplied_directory(db)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:

                def search(term, **kwargs):
                    response = client.get(
                        "/api/directory",
                        params={"branch": "all", "search": term, **kwargs},
                    )
                    assert response.status_code == 200, response.text
                    return response.json()

                for term in [
                    "আম্বরখানা",
                    "Ambarkhana",
                    "ambarkhana airport",
                    "Airport Ambarkhana",
                ]:
                    result = search(term)
                    assert result["total"] > 0
                    assert all(
                        row["branch"] == "census2022"
                        and not row["reportable"]
                        and row["location_id"] is None
                        for row in result["items"]
                    )
                result = search("বালাগঞ্জ")
                assert result["items"][0]["name_bn"] == "বালাগঞ্জ"
                assert result["items"][0]["branch"] == "portal"
                assert result["items"][0]["reportable"]
                assert (
                    search("বালাগঞ্জ", page_size=2)["items"]
                    == search("বালাগঞ্জ", page_size=2)["items"]
                )
                first = search("Sylhet", page_size=12)
                second = search("Sylhet", page_size=12, page=2)
                assert not {r["id"] for r in first["items"]} & {
                    r["id"] for r in second["items"]
                }
                for term in ["%", "_", "this-name-does-not-exist-xyzz"]:
                    assert search(term)["total"] == 0
                assert search("ওয়ার্ড ০১", kind="ward")["total"] > 0
                assert search("", kind="division")["total"] == 1
                assert search("", kind="village")["total"] == 3318
                assert (
                    client.get(
                        "/api/directory?branch=all&kind=sql-injection"
                    ).status_code
                    == 422
                )
                assert (
                    client.get("/api/directory?branch=all&page_size=5000").status_code
                    == 422
                )
        finally:
            app.dependency_overrides.clear()
