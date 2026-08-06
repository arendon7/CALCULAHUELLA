#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -x .venv/bin/python ]]; then
  echo "Falta el entorno local. Ejecuta primero: ./scripts/dev/setup.sh" >&2
  exit 1
fi

if [[ -f .env.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
fi

export APP_ENV=test
export SEED_DEMO=true
export OPEN_BROWSER=0
export SCHEDULER_ENABLED=false
export DATABASE_URL="sqlite:///$PROJECT_ROOT/instance/test_repository.db"
rm -f "$PROJECT_ROOT/instance/test_repository.db"
exec .venv/bin/python -m pytest "$@"
