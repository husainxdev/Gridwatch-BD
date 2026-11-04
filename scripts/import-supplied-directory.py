"""Controlled one-time import of the reviewed source SQLite into PostgreSQL."""

import argparse
import json

from release_common import expected_database, load_settings
from sqlalchemy.exc import SQLAlchemyError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    args = parser.parse_args()
    settings = load_settings()
    expected_database(settings, args.expected_database)
    from app.db import SessionLocal
    from app.supplied_directory import import_supplied_directory

    with SessionLocal.begin() as db:
        result = import_supplied_directory(db)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, SQLAlchemyError):
        raise SystemExit(
            "Source directory import stopped safely. Check target, schema and conflicts. Existing records were preserved; no secrets displayed."
        ) from None
