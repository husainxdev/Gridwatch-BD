"""Release guards and real backup/restore/restart, only on fresh isolated DBs."""

import json
import os
import socket
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import Settings, get_settings

ROOT = Path(__file__).resolve().parents[2]
PYTHON = (
    str(ROOT / "backend" / ".venv" / "bin" / "python")
    if os.name != "nt"
    else str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe")
)


def test_production_config_normalization_tls_origin_revision_and_demo_isolation():
    values = dict(
        _env_file=None,
        database_url="postgres://qa:private@localhost/gridwatch?sslmode=require",
        jwt_secret="release-test-key-with-sufficient-length-1234",
        app_env="production",
        release_revision="a" * 40,
        frontend_url="https://front.example.com",
        cors_origins=["https://front.example.com"],
        demo_enabled=False,
    )
    settings = Settings(**values)
    assert settings.database_url.startswith("postgresql+psycopg://")
    for invalid in [
        dict(database_url="postgresql://qa:private@localhost/gridwatch"),
        dict(cors_origins=["*"]),
        dict(frontend_url="http://front.example.com"),
        dict(frontend_url="https://front.example.com/path"),
        dict(release_revision="unversioned"),
        dict(jwt_secret="REPLACE_WITH_SOMETHING_LONG_ENOUGH"),
        dict(demo_instance=True),
        dict(demo_enabled=True),
        dict(
            database_url="postgresql://qa:private@localhost/gridwatch_demo_isolated?sslmode=require"
        ),
    ]:
        with pytest.raises(ValidationError) as error:
            Settings(**(values | invalid))
        assert "qa:private" not in str(error.value)
    assert Settings(
        **(
            values
            | {
                "demo_instance": True,
                "demo_enabled": True,
                "database_url": "postgresql://qa:private@localhost/gridwatch_demo_isolated?sslmode=require",
            }
        )
    ).demo_instance
    with pytest.raises(ValidationError):
        Settings(**(values | {"db_pool_size": 0}))


@pytest.fixture
def release_databases():
    suffix = uuid.uuid4().hex[:12]
    names = [
        "gridwatch_release_" + suffix,
        "gridwatch_restore_" + suffix,
        "gridwatch_demo_" + suffix,
    ]
    base = make_url(get_settings().database_url)
    created = []
    try:
        for name in names:
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "db",
                    "createdb",
                    "-U",
                    "gridwatch",
                    name,
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
            created.append(name)
        yield [
            {
                **os.environ,
                "DATABASE_URL": base.set(database=n).render_as_string(
                    hide_password=False
                ),
                "APP_ENV": "test",
                "DEMO_INSTANCE": "true" if n.startswith("gridwatch_demo_") else "false",
                "DEMO_ENABLED": "false",
                "SMTP_HOST": "",
                "FRONTEND_URL": "http://localhost:5173",
                "CORS_ORIGINS": '["http://localhost:5173"]',
            }
            for n in names
        ]
    finally:
        for name in reversed(created):
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


def script(name, env, *args):
    return subprocess.run(
        [PYTHON, str(ROOT / "scripts" / name), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_backup_restore_populated_upgrade_and_target_guards(
    release_databases, tmp_path
):
    source, target, _ = release_databases
    src = make_url(source["DATABASE_URL"])
    dst = make_url(target["DATABASE_URL"])
    assert (
        script(
            "release-migrate.py", source, "--expected-database", src.database
        ).returncode
        == 0
    )
    subprocess.run(
        [PYTHON, "-m", "alembic", "downgrade", "0003"],
        cwd=ROOT / "backend",
        env=source,
        check=True,
        capture_output=True,
    )
    source_engine = create_engine(src)
    target_engine = create_engine(dst)
    user, area = uuid.uuid4(), uuid.uuid4()
    try:
        with source_engine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO users(id,email,display_name,password_hash,role,is_active) VALUES(:id,'backup-marker@example.com','Fictional backup marker','not-a-login','user',true)"
                ),
                {"id": user},
            )
            db.execute(
                text(
                    "INSERT INTO locations(id,name_bn,name_en,kind,slug,verification_status) VALUES(:id,'কাল্পনিক backup','Fictional backup','division','qa-backup','unverified')"
                ),
                {"id": area},
            )
            db.execute(
                text("INSERT INTO saved_areas(user_id,location_id) VALUES(:u,:a)"),
                {"u": user, "a": area},
            )
        assert (
            script(
                "release-migrate.py", source, "--expected-database", "wrong-target"
            ).returncode
            != 0
        )
        assert (
            script(
                "release-migrate.py", source, "--expected-database", src.database
            ).returncode
            != 0
        )
        backup = tmp_path / "release.dump"
        assert (
            script(
                "db-archive.py",
                source,
                "backup",
                "--expected-database",
                src.database,
                "--file",
                str(backup),
                "--local-compose",
            ).returncode
            == 0
        )
        receipt = json.loads(Path(str(backup) + ".receipt.json").read_text())
        assert receipt["schema"] == "0003" and not receipt["restore_verified"]
        # Reject corrupted backups before pg_restore writes any target tables.
        original = backup.read_bytes()
        backup.write_bytes(original + b"corruption")
        assert (
            script(
                "db-archive.py",
                target,
                "restore",
                "--expected-database",
                dst.database,
                "--file",
                str(backup),
                "--local-compose",
            ).returncode
            != 0
        )
        with target_engine.connect() as db:
            assert (
                db.execute(
                    text(
                        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
                    )
                ).scalar_one()
                == 0
            )
        backup.write_bytes(original)
        assert (
            script(
                "db-archive.py",
                source,
                "restore",
                "--expected-database",
                src.database,
                "--file",
                str(backup),
                "--local-compose",
            ).returncode
            != 0
        )
        assert (
            script(
                "db-archive.py",
                target,
                "restore",
                "--expected-database",
                dst.database,
                "--file",
                str(backup),
                "--local-compose",
            ).returncode
            == 0
        )
        assert (
            script(
                "db-archive.py",
                target,
                "restore",
                "--expected-database",
                dst.database,
                "--file",
                str(backup),
                "--local-compose",
            ).returncode
            != 0
        )
        for env, engine in [(source, source_engine), (target, target_engine)]:
            name = make_url(env["DATABASE_URL"]).database
            assert (
                script(
                    "release-migrate.py",
                    env,
                    "--expected-database",
                    name,
                    "--backup-reference",
                    receipt["sha256"],
                ).returncode
                == 0
            )
            assert (
                script(
                    "release-migrate.py", env, "--expected-database", name
                ).returncode
                == 0
            )
            with engine.connect() as db:
                assert (
                    db.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalar_one()
                    == "0006"
                )
                row = db.execute(
                    text("SELECT label,is_default FROM saved_areas WHERE user_id=:id"),
                    {"id": user},
                ).one()
                assert row.label == "" and not row.is_default
                assert (
                    db.execute(
                        text("SELECT version FROM locations WHERE id=:id"), {"id": area}
                    ).scalar_one()
                    == 1
                )
    finally:
        source_engine.dispose()
        target_engine.dispose()


def test_private_demo_accounts_and_real_process_restart(release_databases, tmp_path):
    source, _, demo = release_databases
    name = make_url(demo["DATABASE_URL"]).database
    assert (
        script("release-migrate.py", demo, "--expected-database", name).returncode == 0
    )
    private = tmp_path / "private-credentials.json"
    assert (
        script(
            "provision-demo.py", source, "--credentials-file", str(private)
        ).returncode
        != 0
    )
    assert not private.exists()
    assert (
        script("provision-demo.py", demo, "--credentials-file", str(private)).returncode
        == 0
    )
    # Never print credentials or response bodies; assertions only inspect roles/statuses.
    credentials = json.loads(private.read_text())["accounts"]
    assert {c["role"] for c in credentials} == {"admin", "user"}
    assert (
        script(
            "provision-demo.py",
            demo,
            "--credentials-file",
            str(tmp_path / "other.json"),
        ).returncode
        != 0
    )
    if os.name != "nt":
        assert private.stat().st_mode & 0o077 == 0
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    running = None

    def start():
        process = subprocess.Popen(
            [
                PYTHON,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            cwd=ROOT / "backend",
            env=demo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Test API failed to start")
                try:
                    if (
                        httpx.get(
                            f"http://127.0.0.1:{port}/api/health/ready", timeout=1
                        ).status_code
                        == 200
                    ):
                        return process
                except httpx.HTTPError:
                    pass
                time.sleep(0.05)
            raise RuntimeError("Test API startup timed out")
        except Exception:
            process.terminate()
            process.wait(timeout=5)
            raise

    try:
        running = start()
        base = f"http://127.0.0.1:{port}"
        with (
            httpx.Client(base_url=base, timeout=10) as admin,
            httpx.Client(base_url=base, timeout=10) as user,
        ):
            for client, account in zip([admin, user], credentials, strict=True):
                response = client.post(
                    "/api/auth/login",
                    json={"email": account["email"], "password": account["password"]},
                )
                assert response.status_code == 200
                client.headers["Authorization"] = (
                    "Bearer " + response.json()["access_token"]
                )
                assert response.json()["user"]["role"] == account["role"]
            assert admin.get("/api/admin/overview").status_code == 200
            assert user.get("/api/admin/overview").status_code == 403
            area = admin.post(
                "/api/admin/locations",
                json={
                    "name_bn": "কাল্পনিক release area",
                    "name_en": "Fictional release area",
                    "slug": "fictional-release-area",
                    "kind": "division",
                },
            ).json()["id"]
            assert (
                admin.post(
                    f"/api/admin/locations/{area}/verify",
                    json={
                        "version": 1,
                        "source_url": "https://example.com/fictional-release",
                    },
                ).status_code
                == 200
            )
            assert user.post(f"/api/saved-areas/{area}").status_code == 201
            assert (
                user.put(
                    f"/api/saved-areas/{area}",
                    json={"label": "Fictional restart marker", "is_default": True},
                ).status_code
                == 200
            )
            running.terminate()
            running.wait(timeout=5)
            running = start()
            assert user.get("/api/auth/me").status_code == 200
            csrf = user.cookies.get("gridwatch_csrf")
            refreshed = user.post(
                "/api/auth/refresh",
                headers={"Origin": "http://localhost:5173", "X-CSRF-Token": csrf},
            )
            assert refreshed.status_code == 200
            user.headers["Authorization"] = "Bearer " + refreshed.json()["access_token"]
            saved = user.get("/api/saved-areas").json()
            assert (
                saved["total"] == 1
                and saved["items"][0]["id"] == area
                and saved["items"][0]["is_default"]
            )
    finally:
        if running is not None:
            running.terminate()
            running.wait(timeout=5)


def test_release_entrypoint_port_revision_and_untrusted_forwarding():
    base = make_url(get_settings().database_url).update_query_dict(
        {"sslmode": "verify-full", "sslrootcert": "/nonexistent/gridwatch-qa-ca.pem"}
    )
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    env = dict(
        os.environ,
        DATABASE_URL=base.render_as_string(hide_password=False),
        APP_ENV="production",
        DEMO_INSTANCE="false",
        DEMO_ENABLED="false",
        FRONTEND_URL="https://front.example.com",
        CORS_ORIGINS='["https://front.example.com"]',
        JWT_SECRET="release-entrypoint-test-key-not-real-1234",
        RELEASE_REVISION=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        PORT=str(port),
        TRUSTED_PROXY_IPS="",
        AUTH_RATE_LIMIT="1",
    )
    process = subprocess.Popen(
        [PYTHON, str(ROOT / "scripts" / "serve.py")],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Production entrypoint failed")
                try:
                    response = client.get("/api/health/live")
                    if response.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.05)
            else:
                raise RuntimeError("Production entrypoint did not bind configured PORT")
            assert response.json()["revision"] == env["RELEASE_REVISION"]
            assert (
                client.get("/api/health/ready").status_code == 503
            )  # Invalid QA CA; never a claimed provider TLS check.
            body = {
                "email": "release-absent@example.com",
                "password": "not-a-real-password",
            }
            assert (
                client.post(
                    "/api/auth/login",
                    json=body,
                    headers={"X-Forwarded-For": "198.51.100.10"},
                ).status_code
                == 503
            )
            assert (
                client.post(
                    "/api/auth/login",
                    json=body,
                    headers={"X-Forwarded-For": "198.51.100.11"},
                ).status_code
                == 429
            )
    finally:
        process.terminate()
        process.wait(timeout=5)
    env["TRUSTED_PROXY_IPS"] = "*"
    assert (
        subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "serve.py")],
            cwd=ROOT,
            env=env,
            capture_output=True,
            check=False,
        ).returncode
        != 0
    )

    env["TRUSTED_PROXY_IPS"] = ""
    env["RELEASE_REVISION"] = "0" * 40
    rejected = script("serve.py", env)
    assert rejected.returncode != 0
    assert env["JWT_SECRET"] not in rejected.stderr


def test_populated_demo_walkthrough_and_normal_instance_exclusion(
    release_databases, tmp_path, monkeypatch
):
    from datetime import UTC, datetime, timedelta

    from fastapi.testclient import TestClient
    from sqlalchemy import func, select
    from sqlalchemy.orm import sessionmaker

    from app import data_mode, evidence, planning
    from app.db import get_db
    from app.demo_seed import key, seed_content
    from app.main import app
    from app.models import EvidenceAudit, Notice, PersonalEpisode, Report, User

    _, _, demo = release_databases
    name = make_url(demo["DATABASE_URL"]).database
    assert (
        script("release-migrate.py", demo, "--expected-database", name).returncode == 0
    )
    private = tmp_path / "accounts.json"
    assert (
        script("provision-demo.py", demo, "--credentials-file", str(private)).returncode
        == 0
    )
    settings = Settings(
        _env_file=None,
        database_url=demo["DATABASE_URL"],
        jwt_secret=get_settings().jwt_secret,
        demo_instance=True,
        app_env="test",
    )
    engine = create_engine(settings.database_url)
    sessions = sessionmaker(engine)
    anchor = datetime.now(UTC).replace(microsecond=0)
    try:
        with sessions.begin() as db:
            manifest = seed_content(settings, db, anchor)
            assert not manifest["already_seeded"] and manifest["locations"] == 9
        with sessions.begin() as db:
            # Re-running after time has passed keeps observations and source timestamps.
            again = seed_content(settings, db, anchor + timedelta(days=5))
            assert (
                again["already_seeded"] and again["seeded_at"] == manifest["seeded_at"]
            )
            assert db.scalar(select(func.count()).select_from(Report)) == 10
            assert db.scalar(select(func.count()).select_from(PersonalEpisode)) == 5
            assert db.scalar(select(func.count()).select_from(User)) == 3
            assert (
                db.get(EvidenceAudit, key("manifest")).snapshot["official_sources_used"]
                == []
            )

        def override():
            with sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override
        for module in (data_mode, evidence, planning):
            monkeypatch.setattr(module, "get_settings", lambda: settings)
        with TestClient(app, headers={"Origin": "http://localhost:5173"}) as browser:
            assert (
                browser.get("/api/notices").json()["total"] == 1
            )  # Draft/withdrawn stay private.
            schedules = browser.get("/api/schedules").json()
            assert schedules["total"] == 3 and all(
                row["is_demo"] for row in schedules["items"]
            )
            credentials = json.loads(private.read_text())["accounts"]
            account = next(a for a in credentials if a["role"] == "user")
            login = browser.post(
                "/api/auth/login",
                json={"email": account["email"], "password": account["password"]},
            )
            assert login.status_code == 200
            browser.headers["Authorization"] = "Bearer " + login.json()["access_token"]
            saved = browser.get("/api/saved-areas").json()
            assert saved["total"] == 2 and saved["items"][0]["is_default"]
            area = manifest["default_location_id"]
            dashboard = browser.get(
                "/api/dashboard", params={"location_id": area}
            ).json()
            assert dashboard["community"]["evidence_label"] == "mixed"
            assert dashboard["community"]["unique_reporters"] == 2
            assert dashboard["community"]["area_status"] == "unknown"
            assert len(dashboard["schedules"]["items"]) == 3
            assert dashboard["personal"]["latest_report"]["kind"] == "power_back"
            check = browser.get(f"/api/activities/{key('activity:conflict')}").json()[
                "check"
            ]
            assert check["affected_minutes"] == 60 and len(check["conflicts"]) == 2
            boundary = browser.get(
                f"/api/activities/{key('activity:boundary')}"
            ).json()["check"]
            assert not boundary["announced_overlap"]
            history = browser.get(
                "/api/history",
                params={
                    "location_id": area,
                    "start": (anchor - timedelta(days=7)).isoformat(),
                    "end": anchor.isoformat(),
                },
            ).json()
            assert history["summary"]["known_minutes"] == 60
            assert history["summary"]["completed"] == 2
            assert history["summary"]["incomplete"] == 1
            assert "fictional" in history["source"]
            assert sum(row["accepted_observations"] for row in history["items"]) == 5
            assert browser.get("/api/admin/overview").status_code == 403
            report = browser.post(
                "/api/reports",
                json={
                    "location_id": area,
                    "kind": "power_off",
                    "observed_at": datetime.now(UTC).isoformat(),
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
            assert report.status_code == 201 and report.json()["is_demo"] is True
            # Changing mode never exposes flagged fixtures through normal evidence queries.
            admin_account = next(a for a in credentials if a["role"] == "admin")
            admin_login = browser.post(
                "/api/auth/login",
                json={
                    "email": admin_account["email"],
                    "password": admin_account["password"],
                },
            )
            assert admin_login.status_code == 200
            browser.headers["Authorization"] = (
                "Bearer " + admin_login.json()["access_token"]
            )
            overview = browser.get("/api/admin/overview").json()
            assert overview["draft_notices"] == 1 and overview["pending_reports"] == 1
            assert browser.get("/api/admin/list/notices").json()["total"] == 3
            normal = settings.model_copy(update={"demo_instance": False})
            monkeypatch.setattr(data_mode, "get_settings", lambda: normal)
            assert browser.get("/api/notices").json()["total"] == 0
            assert browser.get("/api/schedules").json()["total"] == 0
            assert (
                browser.get("/api/reports", params={"location_id": area}).json()[
                    "total"
                ]
                == 0
            )
            assert (
                browser.get(
                    "/api/reports/summary", params={"location_id": area}
                ).json()["unique_reporters"]
                == 0
            )
        with sessions.begin() as db:
            with pytest.raises(ValueError):
                seed_content(normal, db, anchor)
            assert db.scalar(select(func.count()).select_from(Notice)) == 3
            with db.begin_nested() as temporary:
                db.delete(db.get(EvidenceAudit, key("manifest")))
                db.flush()
                with pytest.raises(ValueError, match="empty operational"):
                    seed_content(settings, db, anchor)
                temporary.rollback()
            assert db.get(EvidenceAudit, key("manifest")) is not None
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
