#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
CODE_DIR="${CTH_CODE_DIR:-$INSTALL_ROOT/current}"
DATA_DIR="${CTH_DATA_DIR:-$INSTALL_ROOT/data}"
CHECK_ROOT="$ROOT"
[ -d "$CODE_DIR" ] && CHECK_ROOT="$CODE_DIR"
export INSTANCE_DIR="$DATA_DIR" CTH_DATA_DIR="$DATA_DIR"
source "$CHECK_ROOT/scripts/easy_mac_common.sh"
cth_easy_prepare "$CHECK_ROOT"
clear 2>/dev/null || true
echo "Calcula tu Huella V0.45 · ensayo seguro de restauración"
echo "Este proceso crea un respaldo nuevo y lo valida en un directorio aislado."
echo "La base activa nunca se reemplaza."
echo
if ! cth_easy_python_ready "$CHECK_ROOT"; then
  echo "La aplicación aún no está instalada. Ejecuta primero INSTALAR_O_ACTUALIZAR_CALCULA_TU_HUELLA.command"
  cth_easy_pause
  exit 1
fi
cd "$CHECK_ROOT" || exit 1
if "$CHECK_ROOT/.venv/bin/python" scripts/run_restore_drill.py; then
  echo
  echo "RESULTADO: ENSAYO APROBADO"
  echo "Consulta el historial completo en Operación y seguridad."
  STATUS=0
else
  echo
  echo "RESULTADO: ENSAYO NO APROBADO"
  echo "Revisa el detalle mostrado antes de usar el respaldo."
  STATUS=1
fi
cth_easy_pause
exit "$STATUS"
