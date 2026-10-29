"""Create/promote an administrator locally after explicit operator authentication."""

import getpass
import os
import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[1] / "backend"
os.chdir(backend)
sys.path.insert(0, str(backend))
from app.db import SessionLocal
from app.models import User
from app.security import hash_password
from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select


def main():
    email = input("Admin email: ").strip().lower()
    name = input("Display name: ").strip()
    try:
        email = validate_email(email, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise SystemExit("Valid email required") from None
    if len(name) < 2:
        raise SystemExit("Display name must be at least two characters")
    with SessionLocal.begin() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("Account already exists; no role changed.")
        raw = getpass.getpass("New admin password (8–72 UTF-8 bytes): ")
        try:
            hashed = hash_password(raw)
        except ValueError as exc:
            raise SystemExit(str(exc)) from None
        db.add(User(email=email, display_name=name, password_hash=hashed, role="admin"))
    print(
        "Administrator account created. Password was not displayed or stored in a file."
    )


if __name__ == "__main__":
    main()
