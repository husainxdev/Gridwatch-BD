"""Import only reviewed Sylhet administrative records. No live-source fetching."""

import argparse
import json

from release_common import expected_database, load_settings
from sqlalchemy.exc import SQLAlchemyError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--only-if-empty", action="store_true")
    args = parser.parse_args()
    settings = load_settings()
    expected_database(settings, args.expected_database)
    from app.db import SessionLocal
    from app.location_catalog import import_catalog

    with SessionLocal.begin() as db:
        result = import_catalog(db, only_if_empty=args.only_if_empty)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, SQLAlchemyError):
        raise SystemExit(
            "Administrative catalog import refused or conflicted. Existing records preserved; no secrets displayed."
        ) from None
