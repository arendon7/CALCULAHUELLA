#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
export CTH_DATA_DIR="${CTH_DATA_DIR:-$INSTALL_ROOT/data}"
export CTH_DB_PATH="${CTH_DB_PATH:-$CTH_DATA_DIR/calculatuhuella.db}"
cd "$ROOT"
echo "Reparación de la instalación local."
echo "Se reconstruirá únicamente el entorno Python; los datos persistentes no se borran."
rm -rf .venv
exec ./install_mac.sh
