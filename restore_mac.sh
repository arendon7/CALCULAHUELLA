#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
DATA_DIR="${CTH_DATA_DIR:-${INSTANCE_DIR:-$INSTALL_ROOT/data}}"
DB_PATH="${CTH_DB_PATH:-$DATA_DIR/calculatuhuella.db}"
cd "$ROOT"
if [ "$#" -ne 1 ]; then echo "Uso: ./restore_mac.sh ruta/al/respaldo.zip"; exit 1; fi
source scripts/runtime_python.sh
cth_runtime_python "$ROOT"
export INSTANCE_DIR="$DATA_DIR" DATABASE_URL="sqlite:///$DB_PATH"
exec "$CTH_RUNTIME_PYTHON" scripts/restore_sqlite.py "$1" --confirm
