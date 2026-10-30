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
