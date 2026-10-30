"""Private PostgreSQL backup or isolated-only restore. Never reset a user DB."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from release_common import (
    ROOT,
    expected_database,
    load_settings,
    operator_path,
    private_output,
)
from sqlalchemy.exc import SQLAlchemyError


def command(args, url, tool):
    if args.local_compose:
        if url.host not in {"127.0.0.1", "localhost"}:
            raise ValueError("Compose archive mode only supports loopback databases")
        mapping = subprocess.run(
            ["docker", "compose", "port", "db", "5432"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if int(mapping.rsplit(":", 1)[1]) != (url.port or 5432):
            raise ValueError("Compose port differs from selected database")
        return [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            tool,
            "-U",
            url.username or "gridwatch",
            "--dbname",
            url.database,
        ], os.environ.copy()
    env = os.environ.copy()
    env.update(
        PGHOST=url.host or "",
        PGPORT=str(url.port or 5432),
        PGDATABASE=url.database,
        PGUSER=url.username or "",
        PGPASSWORD=url.password or "",
    )
    for key, value in url.query.items():
        names = {
            "sslmode": "PGSSLMODE",
            "sslrootcert": "PGSSLROOTCERT",
            "sslcert": "PGSSLCERT",
            "sslkey": "PGSSLKEY",
            "channel_binding": "PGCHANNELBINDING",
        }
        if key not in names or not isinstance(value, str):
            raise ValueError(
                "Unsupported archive connection option; use a reviewed operator configuration"
            )
        env[names[key]] = value
    return [tool], env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--local-compose", action="store_true")
    args = parser.parse_args()
    settings = load_settings()
    url = expected_database(settings, args.expected_database)
    from app.db import engine
    from sqlalchemy import inspect, text

    with engine.connect() as db:
        if (
            db.execute(text("SELECT current_database()")).scalar_one()
            != args.expected_database
        ):
            raise ValueError("Connected database does not match expected target")
        tables = inspect(db).get_table_names()
        revision = (
            db.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            if "alembic_version" in tables
            else None
        )
        if args.action == "restore" and (
            not url.database.startswith("gridwatch_restore_") or tables
        ):
            raise ValueError(
                "Restore requires a fresh empty gridwatch_restore_ database"
            )
    file = operator_path(args.file)
    if args.action == "backup":
        cmd, env = command(args, url, "pg_dump")
        try:
            with private_output(file) as stream:
                result = subprocess.run(
                    [*cmd, "--format=custom", "--no-owner", "--no-privileges"],
                    cwd=ROOT,
                    check=False,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.PIPE,
                )
            if result.returncode:
                file.unlink(missing_ok=True)
                raise ValueError(
                    "pg_dump failed; check client version and authorized database connectivity"
                )
            receipt = {
                "database": url.database,
                "schema": revision,
                "created_at": datetime.now(UTC).isoformat(),
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "restore_verified": False,
            }
            with private_output(str(file) + ".receipt.json") as stream:
                stream.write(json.dumps(receipt, indent=2).encode())
        except FileExistsError:
            raise ValueError(
                "Archive or receipt already exists; choose a new private path"
            ) from None
        print(
            "Private backup and checksum receipt created; restoration not yet verified."
        )
    else:
        if os.name != "nt" and file.stat().st_mode & 0o077:
            raise ValueError("Backup must have private filesystem permissions")
        receipt = json.loads(Path(str(file) + ".receipt.json").read_text())
        if receipt.get("sha256") != hashlib.sha256(file.read_bytes()).hexdigest():
            raise ValueError("Archive checksum does not match its private receipt")
        cmd, env = command(args, url, "pg_restore")
        with file.open("rb") as stream:
            result = subprocess.run(
                [*cmd, "--exit-on-error", "--no-owner", "--no-privileges"],
                cwd=ROOT,
                check=False,
                env=env,
                stdin=stream,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        if result.returncode:
            raise ValueError(
                "Restore failed; target is isolated and was not reset automatically"
            )
        print(
            "Archive restored to an isolated database; verify application records before recording success."
        )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, SQLAlchemyError, subprocess.SubprocessError):
        raise SystemExit(
            "Archive operation stopped. Check expected target, private paths, empty restore namespace, client version and connection configuration; no secrets displayed."
        ) from None
