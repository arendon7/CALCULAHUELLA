#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
DATA_DIR="${CTH_DATA_DIR:-${INSTANCE_DIR:-$ROOT/instance}}"
DB_PATH="${CTH_DB_PATH:-$DATA_DIR/calculatuhuella.db}"
export CTH_DATA_DIR="$DATA_DIR" INSTANCE_DIR="$DATA_DIR" DATABASE_URL="sqlite:///$DB_PATH"
cd "$ROOT"
source scripts/runtime_python.sh
cth_runtime_python "$ROOT"
PY="$CTH_RUNTIME_PYTHON"
export APP_ENV=local SEED_DEMO=true HOST=127.0.0.1
REQUESTED_PORT="${PORT:-8765}"
export PORT="$(cth_choose_port "$REQUESTED_PORT")"
export OPEN_BROWSER="${OPEN_BROWSER:-1}"
export TRUSTED_HOSTS="${TRUSTED_HOSTS:-localhost,127.0.0.1,testserver}"
"$PY" -m alembic upgrade head
exec "$PY" run.py
