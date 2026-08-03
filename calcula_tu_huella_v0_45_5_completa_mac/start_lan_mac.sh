#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
source scripts/runtime_python.sh
cth_runtime_python "$ROOT"
PY="$CTH_RUNTIME_PYTHON"
export HOST=0.0.0.0
REQUESTED_PORT="${PORT:-8765}"
export PORT="$(cth_choose_port "$REQUESTED_PORT")"
export OPEN_BROWSER=0
if [ "$PORT" != "$REQUESTED_PORT" ]; then
  echo "El puerto $REQUESTED_PORT está ocupado. Se usará automáticamente el puerto $PORT."
fi
exec "$PY" run.py
