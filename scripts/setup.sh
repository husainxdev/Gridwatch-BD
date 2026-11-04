#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/gridwatch-uv-cache}"
export npm_config_cache="${npm_config_cache:-/tmp/gridwatch-npm-cache}"
python3 scripts/init-local.py
uv sync --project backend --frozen
npm ci --prefix frontend --no-audit --no-fund
docker compose up -d --wait db mail
backend/.venv/bin/python scripts/prepare-local-schema.py --expected-database gridwatch
backend/.venv/bin/python scripts/import-location-catalog.py --expected-database gridwatch --only-if-empty
backend/.venv/bin/python scripts/import-supplied-directory.py --expected-database gridwatch
npm run build --prefix frontend
