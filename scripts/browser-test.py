"""Browser journey against its own disposable database and servers (ports 18000/15173)."""

import os
import secrets
import subprocess
import time
import uuid
from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
backend = root / "backend"
python = str(
    backend / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
)
name = "gridwatch_browser_" + uuid.uuid4().hex[:12]
processes = []


def run(args, **kwargs):
    subprocess.run(args, cwd=kwargs.pop("cwd", root), check=True, **kwargs)


def wait_ready(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("Test server exited; check test server output")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError("Test server did not become ready")


run(["docker", "compose", "up", "-d", "--wait", "db"])
run(["docker", "compose", "exec", "-T", "db", "createdb", "-U", "gridwatch", name])
try:
    lines = (backend / ".env").read_text().splitlines()
    urls = [line.split("=", 1)[1] for line in lines if line.startswith("DATABASE_URL=")]
    if len(urls) != 1 or not urls[0].endswith("/gridwatch"):
        raise RuntimeError("Unexpected development database URL; stopping")
    browser_password = secrets.token_urlsafe(24)
    env = dict(
        os.environ,
        BROWSER_TEST_PASSWORD=browser_password,
        DATABASE_URL=urls[0].rsplit("/", 1)[0] + "/" + name,
        FRONTEND_URL="http://localhost:15173",
        APP_ENV="test",
        CORS_ORIGINS='["http://localhost:15173"]',
        GRIDWATCH_API_TARGET="http://127.0.0.1:18000",
        GRIDWATCH_TEST_BUILD="1",
        NEXT_PUBLIC_E2E_TEST="1",
        NEXT_TELEMETRY_DISABLED="1",
    )
    run([python, "-m", "alembic", "upgrade", "head"], cwd=backend, env=env)
    # Fictional fixtures exist ONLY inside this disposable browser database.
    run(
        [
            python,
            "-c",
            """
from datetime import datetime, UTC
from app.db import SessionLocal
from app.models import Location, User
from app.security import hash_password
import os
with SessionLocal.begin() as db:
    db.add(User(email="phase-admin@example.com",display_name="Phase test admin",password_hash=hash_password(os.environ["BROWSER_TEST_PASSWORD"]),role="admin"))
    root = Location(name_bn="পরীক্ষামূলক বিভাগ", name_en="Browser test division", slug="browser-division", kind="division")
    db.add(root)
    db.flush()
    db.add(Location(name_bn="দ্বিতীয় পরীক্ষামূলক জেলা", name_en="Browser alternate district", slug="browser-alternate", kind="district", parent_id=root.id, aliases=["Alternate area alias"], verification_status="verified", source_url="https://example.com/fictional-alternate", verified_at=datetime.now(UTC)))
    db.add(Location(name_bn="পরীক্ষামূলক জেলা", name_en="Browser test district", slug="browser-district", kind="district", parent_id=root.id, aliases=["Browser district alias"], verification_status="verified", source_url="https://example.com/fictional-test-only", verified_at=datetime.now(UTC)))
""",
        ],
        cwd=backend,
        env=env,
    )
    api = subprocess.Popen(
        [python, "-m", "uvicorn", "app.main:app", "--port", "18000", "--no-access-log"],
        cwd=backend,
        env=env,
    )
    processes.append(api)
    wait_ready("http://127.0.0.1:18000/api/health/ready", api)
    run(
        ["node", "node_modules/next/dist/bin/next", "build"],
        cwd=root / "frontend",
        env=env,
    )
    web = subprocess.Popen(
        [
            "node",
            "node_modules/next/dist/bin/next",
            "start",
            "--hostname",
            "127.0.0.1",
            "--port",
            "15173",
        ],
        cwd=root / "frontend",
        env=env,
    )
    processes.append(web)
    wait_ready("http://127.0.0.1:15173", web)
    run(
        ["node", "node_modules/@playwright/test/cli.js", "test"],
        cwd=root / "frontend",
        env=env,
    )
finally:
    for process in reversed(processes):
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    run(
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
        ]
    )
