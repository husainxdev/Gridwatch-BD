"""Normal website launch must preserve credentials and refuse fixture databases."""

import importlib.util
from pathlib import Path

import pytest

from app.config import Settings

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "website_launcher", ROOT / "scripts/start-website.py"
)
website = importlib.util.module_from_spec(spec)
spec.loader.exec_module(website)


def configuration(**changes):
    return {
        "DATABASE_URL": "postgresql+psycopg://gridwatch:not-a-real-secret@127.0.0.1:15432/gridwatch",
        "JWT_SECRET": "website-qa-key-at-least-thirty-two-characters",
        "APP_ENV": "development",
        "DEMO_INSTANCE": "false",
        "DEMO_ENABLED": "true",  # Older config is accepted but disabled at runtime.
        "CORS_ORIGINS": '["http://localhost:5173"]',
    } | changes


def test_normal_launcher_preserves_port_secrets_and_disables_inherited_demo(
    monkeypatch,
):
    values = configuration()
    original = values.copy()
    monkeypatch.setenv("DEMO_INSTANCE", "true")
    monkeypatch.setenv("NEXT_PUBLIC_DEMO_INSTANCE", "true")
    monkeypatch.setenv("NEXT_PUBLIC_E2E_TEST", "1")
    target = website.normal_configuration(values, Settings)
    assert target.database == "gridwatch" and target.port == 15432
    env = website.environment(values)
    assert values == original
    assert env["DATABASE_URL"] == values["DATABASE_URL"]
    assert env["JWT_SECRET"] == values["JWT_SECRET"]
    assert env["DEMO_INSTANCE"] == env["DEMO_ENABLED"] == "false"
    assert env["NEXT_PUBLIC_DEMO_INSTANCE"] == "false"
    assert env["NEXT_PUBLIC_E2E_TEST"] == ""
    assert env["FRONTEND_URL"] == "http://localhost:5173"
    assert env["CORS_ORIGINS"] == '["http://localhost:5173"]'


@pytest.mark.parametrize(
    "changes",
    [
        {
            "DATABASE_URL": "postgresql+psycopg://gridwatch:private@localhost/gridwatch_demo_existing",
            "DEMO_INSTANCE": "true",
        },
        {
            "DATABASE_URL": "postgresql+psycopg://gridwatch:private@db.example.com/gridwatch"
        },
        {
            "DATABASE_URL": "postgresql+psycopg://gridwatch:private@localhost/gridwatch_test_existing"
        },
        {
            "DATABASE_URL": "postgresql+psycopg://gridwatch:private@localhost/gridwatch_browser_existing"
        },
        {
            "DATABASE_URL": "postgresql+psycopg://gridwatch:private@localhost/gridwatch_restore_existing"
        },
        {"JWT_SECRET": "short"},
        {"APP_ENV": "test"},
    ],
)
def test_normal_launcher_refuses_demo_test_remote_or_weak_configuration(changes):
    with pytest.raises((website.StartupError, ValueError)):
        website.normal_configuration(configuration(**changes), Settings)
