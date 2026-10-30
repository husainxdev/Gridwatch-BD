"""Operator-only private demo provisioning; no public route and no data reset."""

import json
import os
import secrets
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from .models import Location, Notice, OutageEvent, Report, Schedule, User
from .security import hash_password


def provision_demo(settings, db, output):
    if not settings.demo_instance or not (
        make_url(settings.database_url).database or ""
    ).startswith("gridwatch_demo_"):
        raise ValueError(
            "Only a separately configured gridwatch_demo_ instance can receive demo accounts"
        )
    if any(
        db.scalar(select(func.count()).select_from(model))
        for model in (User, Location, Notice, Schedule, Report, OutageEvent)
    ):
        raise ValueError(
            "Demo provisioning requires an empty operational database; existing accounts and records are preserved"
        )
    path = Path(output).resolve()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("x", encoding="utf-8") as stream:
        path.chmod(0o600)
        try:
            records = []
            for role in ("admin", "user"):
                password = secrets.token_urlsafe(24)
                email = f"gridwatch-demo-{role}@example.com"
                db.add(
                    User(
                        email=email,
                        display_name=f"কাল্পনিক ডেমো {role}",
                        password_hash=hash_password(password),
                        role=role,
                    )
                )
                records.append({"role": role, "email": email, "password": password})
            stream.write(
                json.dumps(
                    {
                        "scope": "private local disposable demo; not a deployed credential handoff",
                        "accounts": records,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            stream.flush()
            os.fsync(stream.fileno())
            db.commit()
        except Exception:
            db.rollback()
            path.unlink(missing_ok=True)
            raise
    return [record["role"] for record in records]
