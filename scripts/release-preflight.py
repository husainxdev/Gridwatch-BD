"""Sanitized production configuration audit; does not deploy or contact providers."""

import argparse
import json
import os

from release_common import ROOT, load_settings, operator_path, revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    parser.add_argument("--manual-provider-setup", action="store_true")
    args = parser.parse_args()
    os.environ.setdefault("RELEASE_REVISION", revision())
    settings = load_settings()
    if settings.app_env != "production":
        raise ValueError("Set production configuration for a release audit")
    checks = {
        "production_configuration": True,
        "separate_demo_database": not settings.demo_instance
        or "gridwatch_demo_" in settings.database_url,
        "email_configured": bool(
            settings.smtp_host
            and settings.smtp_starttls
            and settings.smtp_username
            and settings.smtp_password
        ),
        "provider_credentials_present": bool(
            os.environ.get("VERCEL_TOKEN") and os.environ.get("RENDER_API_KEY")
        ),
        "provider_origins_recorded": bool(
            os.environ.get("LIVE_FRONTEND_ORIGIN")
            and os.environ.get("LIVE_BACKEND_ORIGIN")
        ),
        "no_browser_test_build": os.environ.get("NEXT_PUBLIC_E2E_TEST") != "1",
    }
    result = {
        "source_revision": os.environ["RELEASE_REVISION"],
        "schema_target": "0006",
        "checks": checks,
        "deployed_verification": "not_performed",
        "live_urls": None,
    }
    if args.output:
        output = operator_path(args.output)
        if ROOT not in output.parents or "artifacts" not in output.parts:
            raise ValueError(
                "Write sanitized receipts under the ignored repository artifacts directory"
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    required = {
        key: value
        for key, value in checks.items()
        if not (args.manual_provider_setup and key == "provider_credentials_present")
    }
    return 0 if all(required.values()) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, TypeError):
        raise SystemExit(
            "Release configuration rejected. Check production env names, TLS, trusted HTTPS origin and source revision; no secrets displayed."
        ) from None
