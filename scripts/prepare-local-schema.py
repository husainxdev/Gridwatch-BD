"""Back up a populated local DB before a controlled upgrade; never reset it."""

import argparse
import json
import os
import subprocess
import uuid
from pathlib import Path

from release_common import BACKEND, ROOT, expected_database, load_settings
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--backup-reference", default="")
    args = parser.parse_args()
    settings = load_settings()
    url = expected_database(settings, args.expected_database)
    if settings.app_env != "development" or url.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Automatic schema preparation is local development only")
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from app.db import engine

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    head = ScriptDirectory.from_config(config).get_current_head()
    with engine.connect() as connection:
        if (
            connection.execute(text("SELECT current_database()")).scalar_one()
            != url.database
        ):
            raise ValueError("Database target mismatch")
        tables = inspect(connection).get_table_names()
        current = (
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            if "alembic_version" in tables
            else None
        )
    if current == head:
        print(json.dumps({"schema": head, "migrated": False, "backup_created": False}))
        return
    python = str(
        BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    reference = args.backup_reference
    backup = None
    if tables and not reference:
        backup = (
            ROOT
            / ".private/backups"
            / ("before-directory-" + uuid.uuid4().hex + ".dump")
        )
        subprocess.run(
            [
                python,
                str(ROOT / "scripts/db-archive.py"),
                "backup",
                "--expected-database",
                url.database,
                "--file",
                str(backup),
                "--local-compose",
            ],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
        receipt = json.loads(Path(str(backup) + ".receipt.json").read_text())
        reference = receipt["sha256"]
    command = [
        python,
        str(ROOT / "scripts/release-migrate.py"),
        "--expected-database",
        url.database,
    ]
    if reference:
        command.extend(["--backup-reference", reference])
    subprocess.run(command, cwd=ROOT, capture_output=True, check=True)
    print(
        json.dumps(
            {
                "schema": head,
                "migrated": True,
                "backup_created": backup is not None,
                "backup_file": str(backup) if backup else None,
                "backup_restore_verified": False,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, SQLAlchemyError, subprocess.SubprocessError):
        raise SystemExit(
            "Local upgrade stopped. Check database target and backup permissions; no reset and no secrets displayed."
        ) from None
