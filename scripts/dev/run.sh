#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -x .venv/bin/python ]]; then
  echo "Falta el entorno local. Ejecuta primero: ./scripts/dev/setup.sh" >&2
  exit 1
fi

if [[ ! -f .env.local ]]; then
  cp .env.local.example .env.local
fi

set -a
# shellcheck disable=SC1091
source .env.local
set +a

exec .venv/bin/python run.py
