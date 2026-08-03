#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
source scripts/runtime_python.sh
cth_runtime_python "$ROOT"
exec "$CTH_RUNTIME_PYTHON" scripts/audit_codebase.py
