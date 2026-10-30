"""New isolated local demo DB + private accounts/config; never reset existing data."""

import argparse
import json
import os
import secrets
import subprocess
import uuid

from release_common import BACKEND, ROOT, load_settings, operator_path, private_output
from sqlalchemy.engine import make_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--private-directory", default=str(ROOT / ".private" / "local-demo")
    )
    args = parser.parse_args()
    settings = load_settings()
    base = make_url(settings.database_url)
    if settings.app_env == "production" or base.host not in {"localhost", "127.0.0.1"}:
        raise ValueError("Use only an authorized local development PostgreSQL instance")
    directory = operator_path(args.private_directory)
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    name = "gridwatch_demo_" + uuid.uuid4().hex[:12]
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "createdb", "-U", "gridwatch", name],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError("Could not create a fresh local demo database")
    values = {
        "DATABASE_URL": base.set(database=name).render_as_string(hide_password=False),
        "APP_ENV": "development",
        "DEMO_INSTANCE": "true",
        "DEMO_ENABLED": "true",
        "JWT_SECRET": secrets.token_urlsafe(48),
        "SMTP_HOST": "",
        "FRONTEND_URL": "http://127.0.0.1:5174",
        "CORS_ORIGINS": '["http://127.0.0.1:5174"]',
    }
    with private_output(directory / "backend.env") as stream:
        stream.write(
            (
                "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"
            ).encode()
        )
    env = dict(os.environ, **values)
    python = str(
        BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    for command in [
        [
            python,
            str(ROOT / "scripts" / "release-migrate.py"),
            "--expected-database",
            name,
        ],
        [
            python,
            str(ROOT / "scripts" / "provision-demo.py"),
            "--credentials-file",
            str(directory / "credentials.json"),
        ],
        [python, "-m", "app.seed"],
    ]:
        result = subprocess.run(
            command, cwd=BACKEND, env=env, capture_output=True, check=False
        )
        if result.returncode:
            raise ValueError(
                "Local demo preparation stopped; new DB/config preserved for private operator inspection"
            )
    receipt = {
        "database": name,
        "instance_mode": "local_disposable_demo",
        "publicly_deployed": False,
        "credentials": "credentials.json",
        "reset_procedure": "Create another fresh namespace/directory; this command never deletes or resets existing records.",
    }
    with private_output(directory / "status.json") as stream:
        stream.write(json.dumps(receipt, indent=2).encode())
    print(
        "Local isolated demo prepared. Private files are in the requested directory; no passwords printed and no public deployment performed."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError):
        raise SystemExit(
            "Local demo preparation refused/failed. Check local DB, a new private directory and operator instructions. Existing records were not reset; no secrets displayed."
        ) from None
