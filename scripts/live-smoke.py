"""Read-only HTTPS checks. No signup, email, publication or load generation."""

import argparse
import json
import re
from urllib.parse import urlsplit
from urllib.request import urlopen


def origin(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("An exact trusted HTTPS origin is required")
    return value.rstrip("/")


def check(frontend, backend, expected):
    frontend, backend = origin(frontend), origin(backend)
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("Full expected source commit required")
    checks = []

    def get(base, path, as_json=False):
        with urlopen(base + path, timeout=30) as response:
            if (
                urlsplit(response.url).scheme != "https"
                or urlsplit(response.url).netloc != urlsplit(base).netloc
            ):
                raise ValueError("Unexpected cross-origin or insecure redirect")
            content = response.read(2_000_001)
            if len(content) > 2_000_000 or response.status != 200:
                raise ValueError("Unexpected response size or status")
            checks.append({"path": path, "status": response.status})
            return json.loads(content) if as_json else (response.headers, content)

    for path in ("/", "/dashboard", "/notices", "/reset"):
        headers, body = get(frontend, path)
        if b"/_next/" not in body or headers.get("X-Content-Type-Options") != "nosniff":
            raise ValueError("Frontend shell/security header mismatch")
    for base, path in ((frontend, "/api/health/ready"), (backend, "/api/health/ready")):
        result = get(base, path, True)
        if result.get("schema") != "0006" or result.get("status") != "ready":
            raise ValueError("Database/schema not ready")
    web = get(frontend, "/release-info", True)
    proxied = get(frontend, "/api/health/live", True)
    direct = get(backend, "/api/health/live", True)
    if any(
        item.get("revision") != expected for item in (web, proxied, direct)
    ) or web.get("instance_mode") != proxied.get("instance_mode"):
        raise ValueError("Frontend/backend source or instance-mode mismatch")
    return {
        "source_revision": expected,
        "frontend": frontend,
        "backend": backend,
        "read_only_checks": checks,
        "core_authenticated_journeys": "not_run_by_this_read_only_check",
        "email_delivery": "not_verified",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--expected-revision", required=True)
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                check(args.frontend, args.backend, args.expected_revision), indent=2
            )
        )
    except (ValueError, OSError, TypeError, KeyError, AttributeError):
        raise SystemExit(
            "Live read-only verification failed; check configured origins, TLS, health, revision and headers. No credentials or response bodies displayed."
        ) from None
