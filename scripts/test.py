"""Run integration tests in an isolated disposable PostgreSQL database."""

import os
import subprocess
import uuid
from pathlib import Path

root = Path(__file__).resolve().parents[1]
name = "gridwatch_test_" + uuid.uuid4().hex[:12]
backend = root / "backend"


def run(args, **kwargs):
    subprocess.run(args, cwd=kwargs.pop("cwd", root), check=True, **kwargs)


run(["docker", "compose", "up", "-d", "--wait", "db"])
run(["docker", "compose", "exec", "-T", "db", "createdb", "-U", "gridwatch", name])
try:
    lines = (backend / ".env").read_text().splitlines()
    matches = [
        line.split("=", 1)[1] for line in lines if line.startswith("DATABASE_URL=")
    ]
    original = matches[0] if len(matches) == 1 else None
    if not original or not original.endswith("/gridwatch"):
        raise SystemExit("Unexpected development database URL; test setup stopped.")
    env = dict(os.environ, DATABASE_URL=original.rsplit("/", 1)[0] + "/" + name)
    run([".venv/bin/alembic", "upgrade", "head"], cwd=backend, env=env)
    run([".venv/bin/alembic", "downgrade", "0001"], cwd=backend, env=env)
    run([".venv/bin/alembic", "upgrade", "head"], cwd=backend, env=env)
    # Prove an existing 0003 saved-area row survives the new preferences migration.
    run([".venv/bin/alembic", "downgrade", "0003"], cwd=backend, env=env)
    run(
        [
            ".venv/bin/python",
            "-c",
            """
from sqlalchemy import text
from app.db import engine
with engine.begin() as db:
    db.execute(text("INSERT INTO users(id,email,display_name,password_hash,role,is_active) VALUES ('00000000-0000-0000-0000-000000000071','migration-probe@example.test','Migration fixture','not-a-login-hash','user',true)"))
    db.execute(text("INSERT INTO locations(id,name_bn,name_en,kind,slug,verification_status) VALUES ('00000000-0000-0000-0000-000000000072','Migration fixture','Migration fixture','division','migration-probe','unverified')"))
    db.execute(text("INSERT INTO saved_areas(user_id,location_id) VALUES ('00000000-0000-0000-0000-000000000071','00000000-0000-0000-0000-000000000072')"))
""",
        ],
        cwd=backend,
        env=env,
    )
    run([".venv/bin/alembic", "upgrade", "head"], cwd=backend, env=env)
    run(
        [
            ".venv/bin/python",
            "-c",
            """
from sqlalchemy import text
from app.db import engine
with engine.begin() as db:
    row=db.execute(text("SELECT label,is_default FROM saved_areas WHERE user_id='00000000-0000-0000-0000-000000000071'")).one()
    assert row.label == '' and row.is_default is False
    db.execute(text("DELETE FROM saved_areas WHERE user_id='00000000-0000-0000-0000-000000000071'"))
    db.execute(text("DELETE FROM locations WHERE id='00000000-0000-0000-0000-000000000072'"))
    db.execute(text("DELETE FROM users WHERE id='00000000-0000-0000-0000-000000000071'"))
print('Populated 0003 saved-area upgrade preserved its record')
""",
        ],
        cwd=backend,
        env=env,
    )
    run([".venv/bin/pytest", "-q"], cwd=backend, env=env)
    run([".venv/bin/alembic", "check"], cwd=backend, env=env)
finally:
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
