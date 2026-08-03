#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
CODE_DIR="${CTH_CODE_DIR:-$INSTALL_ROOT/current}"
DATA_DIR="${CTH_DATA_DIR:-$INSTALL_ROOT/data}"
CHECK_ROOT="$ROOT"
[ -d "$CODE_DIR" ] && CHECK_ROOT="$CODE_DIR"
export INSTANCE_DIR="$DATA_DIR" CTH_DATA_DIR="$DATA_DIR"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$DATA_DIR/calculatuhuella.db}"
source "$CHECK_ROOT/scripts/easy_mac_common.sh"
cth_easy_prepare "$CHECK_ROOT"
clear 2>/dev/null || true
cat <<'BANNER'
============================================================
      CALCULA TU HUELLA V0.45 · CERTIFICAR VERSIÓN
============================================================
BANNER
echo "1) Validación local: respaldo, restauración y evidencia, sin aprobación productiva."
echo "2) Certificación estricta: exige PostgreSQL, almacenamiento externo, servicios y secretos."
printf "Selecciona 1 o 2 [1]: "
read -r OPTION
STRICT=""
[ "${OPTION:-1}" = "2" ] && STRICT="--strict"
if ! cth_easy_python_ready "$CHECK_ROOT"; then
  echo "La aplicación no está instalada. Ejecuta primero el instalador."
  cth_easy_pause
  exit 1
fi
cd "$CHECK_ROOT" || exit 1
"$CHECK_ROOT/.venv/bin/python" -m alembic upgrade head || {
  echo "No fue posible actualizar la base."
  cth_easy_pause
  exit 1
}
if "$CHECK_ROOT/.venv/bin/python" scripts/certify_release.py $STRICT; then
  echo
  echo "Evidencia generada correctamente. Consulta Operación y seguridad."
  STATUS=0
else
  echo
  if [ -n "$STRICT" ]; then
    echo "La certificación productiva quedó bloqueada por dependencias o controles pendientes."
  else
    echo "La validación local no pudo completarse. Revisa el resultado anterior."
  fi
  STATUS=1
fi
cth_easy_pause
exit "$STATUS"
