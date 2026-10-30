"""One command for a populated private local demo. Never reset existing databases."""

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
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
API_PORT, WEB_PORT = 8001, 5174
API = f"http://127.0.0.1:{API_PORT}"
WEB = f"http://127.0.0.1:{WEB_PORT}"


class SetupError(Exception):
    """Safe operator-facing error; never contains private configuration."""


def run(command, cwd=ROOT, **kwargs):
    result = subprocess.run(
        command, cwd=cwd, capture_output=True, timeout=120, check=False, **kwargs
    )
    if result.returncode:
        raise SetupError(
            "Command failed: " + Path(command[0]).name + "; existing records preserved"
        )
    return result


def docker_ready():
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


def start_docker():
    if docker_ready():
        return
    if os.name == "nt":
        for directory in [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/DockerDesktop",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Docker/Docker",
        ]:
            exe = directory / "Docker Desktop.exe"
            if exe.is_file():
                subprocess.Popen(
                    [str(exe)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                break
        print("Waiting for Docker Desktop engine...", flush=True)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if docker_ready():
                return
            time.sleep(0.5)
    raise SetupError(
        "Start Docker Desktop and wait for Engine running, then run this command again"
    )


def check_ports():
    for port in (API_PORT, WEB_PORT):
        with socket.socket() as candidate:
            try:
                candidate.bind(("127.0.0.1", port))
            except OSError:
                raise SetupError(
                    f"Demo port {port} is already in use; close the earlier demo terminal first"
                ) from None


def wait_ready(url, process):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SetupError("Demo server exited; inspect its private log file")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.15)
    raise SetupError("Demo server did not become ready; inspect its private log file")


def stop(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        # Only this launcher's child tree; never kill other Node/Python processes.
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


def main():
    if not PYTHON.is_file():
        raise SetupError(
            "Backend venv is missing; run py -m uv sync --project backend --frozen --python 3.12"
        )
    if Path(sys.prefix).resolve() != (BACKEND / ".venv").resolve():
        return subprocess.call(
            [str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]]
        )
    from dotenv import dotenv_values

    sys.path.insert(0, str(BACKEND))
    from app.config import Settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default=".private/demo-ready")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    directory = Path(args.directory)
    directory = (directory if directory.is_absolute() else ROOT / directory).resolve()
    if not shutil.which("docker") or not shutil.which("node"):
        raise SetupError(
            "Docker and Node must be installed and available in this terminal"
        )
    if not (ROOT / "frontend/node_modules/next/dist/bin/next").is_file():
        raise SetupError(
            "Frontend dependencies are missing; run npm.cmd ci --prefix frontend"
        )
    check_ports()
    start_docker()
    print("Starting existing local database/mail containers; no reset...", flush=True)
    run(["docker", "compose", "up", "-d", "--wait", "db", "mail"])
    if not directory.exists():
        print(
            "Creating a separate fictional demo database and private accounts...",
            flush=True,
        )
        run(
            [
                str(PYTHON),
                str(ROOT / "scripts/create-local-demo.py"),
                "--private-directory",
                str(directory),
                "--with-content",
            ]
        )
    config = directory / "backend.env"
    if not config.is_file() or not (directory / "credentials.json").is_file():
        raise SetupError(
            "Private demo configuration is incomplete; choose a new --directory; existing data was preserved"
        )
    values = dict(dotenv_values(config))
    constructor = {
        k.lower(): json.loads(v) if k == "CORS_ORIGINS" else v
        for k, v in values.items()
    }
    settings = Settings(_env_file=None, **constructor)
    if (
        settings.app_env != "development"
        or not settings.demo_instance
        or settings.frontend_url != WEB
        or settings.cors_origins != [WEB]
    ):
        raise SetupError(
            "Launcher requires its isolated development demo config; normal/production config is refused"
        )
    backend_env = dict(os.environ, **values)
    result = run([str(PYTHON), "-m", "app.demo_seed"], env=backend_env, cwd=BACKEND)
    manifest = json.loads(result.stdout)
    print(
        f"Fictional demo ready: {manifest['locations']} locations, {manifest['notices']} notices, {manifest['schedules']} schedules, {manifest['reports']} reports, {manifest['personal_episodes']} personal episodes, {manifest['activities']} activities.",
        flush=True,
    )
    print(
        "All data is fictional; no official source or live API is connected.",
        flush=True,
    )
    print(
        "Private login file: "
        + str(directory / "credentials.json")
        + " (do not share publicly)",
        flush=True,
    )
    if args.prepare_only:
        return 0
    processes, logs = [], []
    try:

        def launch(command, cwd, env, name):
            stream = (directory / name).open("a", encoding="utf-8")
            (directory / name).chmod(0o600)
            logs.append(stream)
            options = (
                {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                if os.name == "nt"
                else {"start_new_session": True}
            )
            process = subprocess.Popen(
                command, cwd=cwd, env=env, stdout=stream, stderr=stream, **options
            )
            processes.append(process)
            return process

        backend = launch(
            [
                str(PYTHON),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(API_PORT),
                "--no-access-log",
            ],
            BACKEND,
            backend_env,
            "backend.log",
        )
        wait_ready(API + "/api/health/ready", backend)
        frontend_env = {
            k: v
            for k, v in os.environ.items()
            if k
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
        frontend_env.update(
            GRIDWATCH_API_TARGET=API,
            NEXT_PUBLIC_DEMO_INSTANCE="true",
            NEXT_PUBLIC_E2E_TEST="",
            GRIDWATCH_TEST_BUILD="0",
            GRIDWATCH_LOCAL_DEMO="1",
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
                str(WEB_PORT),
            ],
            ROOT / "frontend",
            frontend_env,
            "frontend.log",
        )
        wait_ready(WEB + "/login", web)
        print("Open: " + WEB + "/login", flush=True)
        print(
            "Keep this terminal open. Ctrl+C stops this demo's servers; database records remain.",
            flush=True,
        )
        if not args.no_browser:
            webbrowser.open(WEB + "/login")
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
        raise SetupError(
            "A demo server stopped; inspect the private backend/frontend log"
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
        print("Local demo servers stopped. Database/configuration preserved.")
    except SetupError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError):
        # No raw configuration, request bodies, credentials or database URLs.
        print(
            "Local demo could not start. Check Docker Engine, installed dependencies, free ports 8001/5174 and a complete private demo directory. Existing records were not reset.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
