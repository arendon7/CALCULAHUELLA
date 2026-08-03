#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1
source "$ROOT/scripts/easy_mac_common.sh"
source "$ROOT/scripts/runtime_python.sh"
cth_easy_prepare "$ROOT"
clear
echo "Calcula tu Huella V0.45 · diagnóstico de seguridad"
echo
if ! cth_easy_python_ready "$ROOT"; then
  echo "La aplicación todavía no está instalada. Abre primero Calcula tu Huella.app."
  cth_easy_pause
  exit 1
fi
cth_runtime_python "$ROOT" || { cth_easy_pause; exit 1; }
export APP_ENV=local SEED_DEMO=true
"$CTH_RUNTIME_PYTHON" -m alembic upgrade head
"$CTH_RUNTIME_PYTHON" scripts/security_check.py
STATUS=$?
echo
if [ "$STATUS" -eq 0 ]; then
  echo "Resultado: controles internos operativos."
else
  echo "Resultado: se detectaron requisitos pendientes."
fi
cth_easy_pause
exit "$STATUS"
