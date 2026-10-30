"""Sanitized local evidence receipt; never claims a hosted deployment."""

import argparse
import hashlib
import json
import re
import subprocess

from release_common import ROOT, operator_path, revision

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--backend-log", required=True)
parser.add_argument("--browser-log", required=True)
parser.add_argument("--output", default="artifacts/release-receipt.json")
args = parser.parse_args()
checks = {}
for label, name in [("backend", args.backend_log), ("browser", args.browser_log)]:
    file = operator_path(name)
    data = file.read_bytes()
    match = re.findall(rb"(\d+) passed", data)
    if not match or re.search(rb"\d+ failed", data):
        raise SystemExit(
            "Cannot record a passing result from a failed/incomplete local log"
        )
    checks[label] = {
        "passed": int(match[-1]),
        "log_sha256": hashlib.sha256(data).hexdigest(),
        "scope": "local_only",
    }
clean = not subprocess.check_output(
    ["git", "status", "--porcelain"], cwd=ROOT, text=True
).strip()
receipt = {
    "prepared_source_revision": revision(),
    "clean_checkout": clean,
    "checks": checks,
    "frontend_live_url": None,
    "backend_live_url": None,
    "deployed_checks": [],
    "hosting_status": "blocked_provider_access_and_actual_urls_unavailable",
    "demo_accounts": "private local isolated database only; not deployed credentials",
    "email_delivery": "external_unverified",
    "overall": "partial_not_fully_deployed_or_submitted",
}
out = operator_path(args.output)
if ROOT not in out.parents or "artifacts" not in out.parts:
    raise SystemExit("Output must be in ignored repository artifacts")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2))
