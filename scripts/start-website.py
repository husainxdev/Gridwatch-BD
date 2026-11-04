"""Start the normal local website without seeding accounts or fictional records."""

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
API, WEB = "http://127.0.0.1:8000", "http://localhost:5173"


class StartupError(Exception):
    """Safe errors: never include connection strings or subprocess output."""


def run(command, **kwargs):
    result = subprocess.run(
        command,
        cwd=kwargs.pop("cwd", ROOT),
        capture_output=True,
        timeout=120,
        check=False,
        **kwargs,
    )
    if result.returncode:
        raise StartupError(
            "A setup command failed. Existing files and records were preserved."
        )
    return result


def normal_configuration(values, settings_type):
    """Do not disguise a demo DB by turning its banner off."""
    normalized = {
        key.lower(): json.loads(value) if key == "CORS_ORIGINS" else value
        for key, value in values.items()
        if value is not None
    }
    settings = settings_type(_env_file=None, **normalized)
    from sqlalchemy.engine import make_url

    database = make_url(settings.database_url)
    if (
        settings.app_env != "development"
        or settings.demo_instance
        or database.host not in {"127.0.0.1", "localhost"}
        or (database.database or "").startswith(
            (
                "gridwatch_demo_",
                "gridwatch_test_",
                "gridwatch_browser_",
                "gridwatch_restore_",
            )
        )
    ):
        raise StartupError(
            "Use the normal local development database, not a demo, test or hosted database."
        )
    if not settings.jwt_secret or len(settings.jwt_secret) < 32:
        raise StartupError(
            "Configure a random JWT_SECRET of at least 32 characters in backend/.env."
        )
    return database


def environment(values):
    # File configuration wins; inherited demo flags must never enable fixtures.
    env = dict(os.environ, **{k: v for k, v in values.items() if v is not None})
    env.update(
        APP_ENV="development",
        DEMO_INSTANCE="false",
        DEMO_ENABLED="false",
        FRONTEND_URL=WEB,
        CORS_ORIGINS=json.dumps([WEB]),
        NEXT_PUBLIC_E2E_TEST="",
        NEXT_PUBLIC_DEMO_INSTANCE="false",
        GRIDWATCH_LOCAL_DEMO="0",
        GRIDWATCH_TEST_BUILD="0",
    )
    return env


def engine_ready():
    try:
        return (
            subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                timeout=3,
                check=False,
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


def start_engine():
    if engine_ready():
        return
    if os.name == "nt":
        for directory in (
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/DockerDesktop",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Docker/Docker",
        ):
            executable = directory / "Docker Desktop.exe"
            if executable.is_file():
                subprocess.Popen(
                    [str(executable)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                break
        print("Waiting for Docker Desktop Engine...", flush=True)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if engine_ready():
                return
            time.sleep(0.5)
    raise StartupError(
        "Open Docker Desktop and wait for Engine running, then retry START-WEBSITE.cmd."
    )


def stop(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_ready(url, process):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise StartupError(
                "A website server stopped. Inspect .private/website/*.log locally; do not share secrets."
            )
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.15)
    raise StartupError(
        "Website startup timed out. Inspect .private/website/*.log locally."
    )


def main():
    if not PYTHON.is_file():
        raise StartupError(
            "Install backend dependencies: py -m uv sync --project backend --frozen --python 3.12"
        )
    if Path(sys.prefix).resolve() != (BACKEND / ".venv").resolve():
        return subprocess.call(
            [str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]]
        )
    from dotenv import dotenv_values

    sys.path.insert(0, str(BACKEND))
    from app.config import Settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--create-admin", action="store_true")
    parser.add_argument("--backup-reference", default="")
    args = parser.parse_args()
    if not shutil.which("docker") or not shutil.which("node"):
        raise StartupError(
            "Docker and Node.js must be installed and available in this terminal."
        )
    if not (ROOT / "frontend/node_modules/next/dist/bin/next").is_file():
        raise StartupError(
            "Install frontend dependencies: npm.cmd ci --prefix frontend"
        )
    run([str(PYTHON), str(ROOT / "scripts/init-local.py")])
    values = dict(dotenv_values(BACKEND / ".env"))
    database = normal_configuration(values, Settings)
    env = environment(values)
    start_engine()
    print(
        "Starting database and local mailbox. No sample data or accounts will be added.",
        flush=True,
    )
    run(["docker", "compose", "up", "-d", "--wait", "db", "mail"])
    # Verify Compose uses the configured host port; preserve custom Windows ports.
    binding = run(["docker", "compose", "port", "db", "5432"]).stdout.decode().strip()
    if binding != f"127.0.0.1:{database.port or 5432}":
        raise StartupError(
            "Compose database port differs from backend/.env. Match their ports without changing credentials."
        )
    command = [
        str(PYTHON),
        str(ROOT / "scripts/release-migrate.py"),
        "--expected-database",
        database.database,
    ]
    if args.backup_reference:
        command.extend(["--backup-reference", args.backup_reference])
    try:
        run(command, env=env)
    except StartupError:
        raise StartupError(
            "Schema check stopped. An older populated database needs a backup first; see docs/WEBSITE.md. No database reset was performed."
        ) from None
    if args.create_admin:
        # Interactive getpass; never generate, print or save a public Admin password.
        return subprocess.call(
            [str(PYTHON), str(ROOT / "scripts/create-admin.py")], cwd=ROOT, env=env
        )
    if args.check_only:
        print(
            "Normal database/schema ready; demo endpoints disabled. No fixture accounts or records added."
        )
        return 0
    for port in (8000, 5173):
        with socket.socket() as candidate:
            try:
                candidate.bind(("127.0.0.1", port))
            except OSError:
                raise StartupError(
                    f"Port {port} is busy. Stop the earlier API/frontend terminal with Ctrl+C and retry."
                ) from None
    directory = ROOT / ".private/website"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    processes, logs = [], []
    try:

        def launch(command, cwd, process_env, filename):
            logfile = directory / filename
            stream = logfile.open("a", encoding="utf-8")
            logfile.chmod(0o600)
            logs.append(stream)
            options = (
                {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                if os.name == "nt"
                else {"start_new_session": True}
            )
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=process_env,
                stdout=stream,
                stderr=stream,
                **options,
            )
            processes.append(process)
            return process

        api = launch(
            [
                str(PYTHON),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--no-access-log",
            ],
            BACKEND,
            env,
            "backend.log",
        )
        wait_ready(API + "/api/health/ready", api)
        web_env = {
            key: value
            for key, value in env.items()
            if key
            not in {
                "DATABASE_URL",
                "JWT_SECRET",
                "SMTP_PASSWORD",
                "SMTP_USERNAME",
                "POSTGRES_PASSWORD",
                "VERCEL",
                "VERCEL_GIT_COMMIT_SHA",
            }
        }
        web_env.update(
            GRIDWATCH_API_TARGET=API,
            GRIDWATCH_LOCAL_WEBSITE="1",
            NODE_ENV="development",
        )
        web = launch(
            [
                shutil.which("node"),
                "node_modules/next/dist/bin/next",
                "dev",
                "--hostname",
                "127.0.0.1",
                "--port",
                "5173",
            ],
            ROOT / "frontend",
            web_env,
            "frontend.log",
        )
        wait_ready(WEB, web)
        print("Website: " + WEB, flush=True)
        mail = (
            run(["docker", "compose", "port", "mail", "8025"]).stdout.decode().strip()
        )
        parsed = urlsplit("http://" + mail)
        if parsed.hostname in {"127.0.0.1", "localhost", "::1"} and parsed.port:
            print("Local password-reset mailbox: http://" + parsed.netloc, flush=True)
        print(
            "Register your own account. Existing normal records persist; fixture data is excluded.",
            flush=True,
        )
        print(
            "Keep this terminal open. Ctrl+C stops only these website servers. This is local access, not public hosting.",
            flush=True,
        )
        if not args.no_browser:
            webbrowser.open(WEB)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise StartupError(
            "A website server stopped. Inspect .private/website/*.log locally."
        )
    finally:
        for process in reversed(processes):
            stop(process)
        for stream in logs:
            stream.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Website servers stopped. Database and configuration preserved.")
    except StartupError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
    except (ValueError, TypeError, OSError, subprocess.SubprocessError):
        raise SystemExit(
            "Website startup failed safely. Check Docker, backend/.env and free ports 8000/5173. No secrets displayed; existing files/records preserved."
        ) from None
