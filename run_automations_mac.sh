#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
DATA_DIR="${CTH_DATA_DIR:-${INSTANCE_DIR:-$INSTALL_ROOT/data}}"
DB_PATH="${CTH_DB_PATH:-$DATA_DIR/calculatuhuella.db}"
cd "$ROOT"
source scripts/runtime_python.sh
cth_runtime_python "$ROOT"
export INSTANCE_DIR="$DATA_DIR" DATABASE_URL="sqlite:///$DB_PATH"
export APP_ENV="${APP_ENV:-local}" SEED_DEMO="${SEED_DEMO:-true}"
exec "$CTH_RUNTIME_PYTHON" scripts/run_automations.py
