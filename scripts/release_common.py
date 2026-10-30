"""Operator helpers: load config without printing secrets, identify source and DB."""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def load_settings():
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    from app.config import get_settings

    return get_settings()


def revision():
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    checkout = result.stdout.strip() if result.returncode == 0 else ""
    values = [
        value
        for value in (
            os.environ.get("RELEASE_REVISION"),
            os.environ.get("RENDER_GIT_COMMIT"),
            checkout,
        )
        if value
    ]
    if (
        not values
        or any(not re.fullmatch(r"[0-9a-f]{40}", value) for value in values)
        or len(set(values)) != 1
    ):
        raise ValueError(
            "Source revision is missing, invalid or differs from the checked-out/provider commit"
        )
    return values[0]


def expected_database(settings, expected):
    from sqlalchemy.engine import make_url

    url = make_url(settings.database_url)
    if not expected or url.database != expected:
        raise ValueError(
            "Target database does not match the explicit expected database name"
        )
    return url


def operator_path(path):
    path = Path(path)
    return (path if path.is_absolute() else ROOT / path).resolve()


def private_output(path):
    path = operator_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    stream = path.open("xb")
    path.chmod(0o600)
    return stream
