"""Create unique private demo accounts on a separate, empty, marked demo DB."""

import argparse

from release_common import load_settings, operator_path
from sqlalchemy.exc import SQLAlchemyError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", required=True)
    args = parser.parse_args()
    output = operator_path(args.credentials_file)
    settings = load_settings()
    from app.db import SessionLocal
    from app.demo_operator import provision_demo

    with SessionLocal() as db:
        provision_demo(settings, db, output)
    print(
        "Demo Admin/User created. Credentials are only in the requested private file; no live deployment verified."
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, SQLAlchemyError):
        raise SystemExit(
            "Demo provisioning refused or failed; verify separate demo configuration, empty operational DB and a new private output path. No existing users changed."
        ) from None
