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
