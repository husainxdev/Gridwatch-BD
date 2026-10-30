"""Local consistency checks only; not provider account/schema/billing validation."""

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
provider = json.loads((root / "deploy/provider-settings.json").read_text())
web = json.loads((root / "frontend/vercel.json").read_text())
package = json.loads((root / "frontend/package.json").read_text())
assert (
    provider["frontend"]["provider"] == "Vercel"
    and provider["backend"]["provider"] == "Render"
)
assert (
    web["framework"] == "nextjs"
    and web["installCommand"] == "npm ci"
    and web["buildCommand"] == "npm run build"
)
assert provider["backend"]["workers"] == provider["backend"]["instances"] == 1
assert provider["backend"]["auto_deploy"] is False
assert (
    provider["frontend"]["public_origin"] is None
    and provider["backend"]["public_origin"] is None
)
assert "reload" not in provider["backend"]["start_command"]
assert package["dependencies"]["next"] == "16.4.3"
assert (root / "backend/uv.lock").exists() and (
    root / "frontend/package-lock.json"
).exists()
print(
    "Local release settings consistent; provider account, plan and deployment remain unverified."
)
