"""Official administrative directory and search use their own disposable DBs."""

import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.location_catalog import import_catalog, load_catalog
from app.main import app
from app.models import FeederMapping, Location, Notice, Report, Schedule, User

ROOT = Path(__file__).resolve().parents[2]
PYTHON = (
    ROOT / "backend/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
)


@pytest.fixture
def catalog_engine():
    base = make_url(get_settings().database_url)
    assert base.database.startswith("gridwatch_test_")
    name = "gridwatch_catalogqa_" + uuid.uuid4().hex[:12]
    subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "createdb", "-U", "gridwatch", name],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    url = base.set(database=name).render_as_string(hide_password=False)
    engine = None
    try:
        subprocess.run(
            [str(PYTHON), "-m", "alembic", "upgrade", "head"],
            cwd=ROOT / "backend",
            env=dict(os.environ, DATABASE_URL=url),
            check=True,
            capture_output=True,
        )
        engine = create_engine(url)
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


def test_reviewed_catalog_contains_only_corroborated_administrative_facts():
    data, sources, reviewed = load_catalog()
    assert len(data["locations"]) == 45
    assert sum(row["kind"] == "ward" for row in data["locations"]) == 42
    assert reviewed.isoformat() == "2026-11-04T10:54:45+00:00"
    assert {source["url"].split("/")[2] for source in sources.values()} == {
        "scc.gov.bd",
        "sylhetdiv.gov.bd",
    }
    assert len(sources["city-wards"]["ward_groups"]) == 14
    assert all(len(source["response_sha256"]) == 64 for source in sources.values())
    assert not any(
        row["kind"] in {"neighborhood", "upazila"} for row in data["locations"]
    )


def test_catalog_is_idempotent_and_never_creates_electricity_facts(catalog_engine):
    with Session(catalog_engine) as db, db.begin():
        first = import_catalog(db)
        assert first["created"] == 45
        assert import_catalog(db) == first | {"created": 0, "preserved": 45}
        for model in (Notice, Schedule, Report, FeederMapping, User):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        city = db.scalar(
            select(Location).where(Location.slug == "sylhet-city-corporation")
        )
        ward = db.scalar(select(Location).where(Location.slug == "sylhet-city-ward-01"))
        assert ward.parent_id == city.id and city.kind == "city_corporation"
        original = ward.verified_at
        ward.verification_status = "unverified"
        ward.version = 9
        ward.name_bn = "পর্যালোচনাধীন নাম"
        db.flush()
        import_catalog(db)
        assert ward.verification_status == "unverified" and ward.version == 9
        assert ward.name_bn == "পর্যালোচনাধীন নাম" and ward.verified_at == original


def test_auto_import_preserves_nonempty_user_directory(catalog_engine):
    with Session(catalog_engine) as db, db.begin():
        existing = Location(
            name_bn="নিজস্ব বিভাগ",
            name_en="Existing division",
            kind="division",
            slug="owner-location",
        )
        db.add(existing)
        db.flush()
        assert import_catalog(db, only_if_empty=True)["skipped_nonempty"]
        assert db.scalar(select(func.count()).select_from(Location)) == 1
        assert existing.verification_status == "unverified"


def test_catalog_conflict_rolls_back_the_whole_import(catalog_engine):
    with Session(catalog_engine) as db, db.begin():
        db.add(
            Location(
                name_bn="বিদ্যমান বিভাগ",
                name_en="Existing conflicting division",
                kind="division",
                slug="sylhet-city-ward-01",
            )
        )
    with pytest.raises(ValueError, match="hierarchy"):
        with Session(catalog_engine) as db, db.begin():
            import_catalog(db)
    with Session(catalog_engine) as db:
        assert db.scalar(select(func.count()).select_from(Location)) == 1


def test_real_catalog_search_alias_numbers_context_paging_and_literal_wildcards(
    catalog_engine,
):
    with Session(catalog_engine) as db, db.begin():
        import_catalog(db)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                for term in [
                    "Ward 1",
                    " ward  1 ",
                    "সিলেট ওয়ার্ড ১",
                    "ওয়ার্ড ১",
                    "ওয়ার্ড ০১",
                    "SCC Ward 1",
                ]:
                    response = client.get("/api/locations", params={"search": term})
                    assert response.status_code == 200, term
                    result = response.json()
                    assert result["items"][0]["slug"] == "sylhet-city-ward-01", term
                    assert result["items"][0]["ancestor_names"] == [
                        "সিলেট বিভাগ",
                        "সিলেট জেলা",
                        "সিলেট সিটি কর্পোরেশন",
                    ]
                for term in ["%", "_", "Ambarkhana", "আম্বরখানা"]:
                    assert (
                        client.get("/api/locations", params={"search": term}).json()[
                            "total"
                        ]
                        == 0
                    )
                a = client.get(
                    "/api/locations", params={"kind": "ward", "page_size": 20}
                ).json()
                b = client.get(
                    "/api/locations",
                    params={"kind": "ward", "page_size": 20, "page": 2},
                ).json()
                assert a["total"] == b["total"] == 42
                assert not {row["id"] for row in a["items"]} & {
                    row["id"] for row in b["items"]
                }
                node = a["items"][0]
                assert (
                    client.get("/api/locations", params={"search": node["id"]}).json()[
                        "total"
                    ]
                    == 1
                )
                assert (
                    client.get(
                        "/api/locations", params={"search": "x" * 101}
                    ).status_code
                    == 422
                )
        finally:
            app.dependency_overrides.clear()


def test_concurrent_first_starts_create_one_catalog(catalog_engine):
    def start(_):
        with Session(catalog_engine) as db, db.begin():
            return import_catalog(db, only_if_empty=True)

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(start, range(2)))
    assert sorted(result["created"] for result in results) == [0, 45]
    assert sum(result["skipped_nonempty"] for result in results) == 1
    with Session(catalog_engine) as db:
        assert db.scalar(select(func.count()).select_from(Location)) == 45


def test_explicit_merge_reuses_short_existing_names_without_overwriting(catalog_engine):
    with Session(catalog_engine) as db, db.begin():
        parent = None
        owners = []
        for kind in ["division", "district", "city_corporation"]:
            item = Location(
                name_bn="সিলেট",
                name_en="Sylhet",
                kind=kind,
                slug="owner-" + kind,
                parent_id=parent,
            )
            db.add(item)
            db.flush()
            owners.append(item)
            parent = item.id
        result = import_catalog(db)
        assert result["created"] == 42 and result["preserved"] == 3
        assert db.scalar(select(func.count()).select_from(Location)) == 45
        assert all(
            item.name_bn == "সিলেট" and item.verification_status == "unverified"
            for item in owners
        )
        ward = db.scalar(select(Location).where(Location.slug == "sylhet-city-ward-01"))
        assert ward.parent_id == parent
