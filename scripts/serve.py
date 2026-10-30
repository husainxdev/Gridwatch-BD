"""Single-process production entry point; migrations are a separate release step."""

import ipaddress
import os

from release_common import load_settings, revision


def main():
    os.environ["RELEASE_REVISION"] = revision()
    settings = load_settings()
    if settings.app_env != "production":
        raise ValueError("Release entry point requires APP_ENV=production")
    port = int(os.environ.get("PORT", "10000"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid PORT")
    proxies = os.environ.get("TRUSTED_PROXY_IPS", "").strip()
    for item in proxies.split(",") if proxies else []:
        ipaddress.ip_network(item.strip(), strict=False)  # No arbitrary '*' trust.
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        proxy_headers=bool(proxies),
        forwarded_allow_ips=proxies,
        access_log=False,
        server_header=False,
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError):
        raise SystemExit(
            "Production startup rejected: check configuration names and release instructions; no secrets displayed."
        ) from None
