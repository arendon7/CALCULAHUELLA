#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="python3"
if [ -x ".venv/bin/python" ]; then PYTHON_BIN=".venv/bin/python"; fi
echo "Calcula tu Huella V1.0.0 · validación de versión final"
"$PYTHON_BIN" scripts/validate_release_candidate.py
echo
echo "Para ejecutar toda la regresión: $PYTHON_BIN -m pytest -q"
