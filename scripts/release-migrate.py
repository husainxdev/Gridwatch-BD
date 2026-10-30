from alembic.util import CommandError

"""One controlled migration owner, expected-target guard and backup gate."""

import argparse
import os

from release_common import BACKEND, expected_database, load_settings
from sqlalchemy.exc import SQLAlchemyError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument(
        "--backup-reference", default=os.environ.get("MIGRATION_BACKUP_REFERENCE", "")
    )
    args = parser.parse_args()
    settings = load_settings()
    expected_database(settings, args.expected_database)
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from app.db import engine
    from sqlalchemy import inspect, text

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    head = ScriptDirectory.from_config(config).get_current_head()
    with engine.connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(34131)"))
        connection.commit()
        try:
            tables = inspect(connection).get_table_names()
            current = (
                connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
                if "alembic_version" in tables
                else None
            )
            if current == head:
                print("Schema already current; no migration executed.")
                return
            if tables and not args.backup_reference.strip():
                raise ValueError(
                    "Existing database requires a recorded backup/restore reference before upgrade"
                )
            connection.commit()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            print("Controlled migration completed.")
        finally:
            connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(34131)"))
            connection.commit()
    engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, SQLAlchemyError, CommandError):
        raise SystemExit(
            "Migration stopped: verify expected target, configuration, backup reference and database access. No secrets displayed."
        ) from None
