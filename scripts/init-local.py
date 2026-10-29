"""Create development-only credentials without displaying them; preserve existing files."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = [root / ".env", root / "backend/.env"]
if any(p.exists() for p in paths):
    if all(p.exists() for p in paths):
        print("Existing local configuration preserved.")
    else:
        raise SystemExit(
            "Partial configuration exists. Complete it using .env.example; no files changed."
        )
else:
    password = secrets.token_hex(24)
    values = [
        f"POSTGRES_PASSWORD={password}\n",
        f"DATABASE_URL=postgresql+psycopg://gridwatch:{password}@127.0.0.1:5432/gridwatch\nAPP_ENV=development\nDEMO_ENABLED=true\nJWT_SECRET={secrets.token_hex(48)}\nSMTP_HOST=127.0.0.1\n",
    ]
    for path, value in zip(paths, values):
        with path.open("x") as file:
            path.chmod(0o600)
            file.write(value)
    print("Local-only configuration created. Never use these settings for deployment.")
