#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/gridwatch-uv-cache}"
export npm_config_cache="${npm_config_cache:-/tmp/gridwatch-npm-cache}"
python3 scripts/init-local.py
uv sync --project backend --frozen
npm ci --prefix frontend --no-audit --no-fund
docker compose up -d --wait db mail
(cd backend && .venv/bin/alembic upgrade head && .venv/bin/python -m app.seed)
npm run build --prefix frontend
