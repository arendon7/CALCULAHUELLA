#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
CODE_DIR="${CTH_CODE_DIR:-$INSTALL_ROOT/current}"
DATA_DIR="${CTH_DATA_DIR:-$INSTALL_ROOT/data}"
CHECK_ROOT="$ROOT"; [ -d "$CODE_DIR" ] && CHECK_ROOT="$CODE_DIR"
export INSTANCE_DIR="$DATA_DIR"
source "$CHECK_ROOT/scripts/easy_mac_common.sh"
cth_easy_prepare "$CHECK_ROOT"
clear 2>/dev/null || true
echo "Calcula tu Huella V0.45 · migración SQLite → PostgreSQL de ensayo"
if ! cth_easy_python_ready "$CHECK_ROOT"; then echo "Instala primero la aplicación."; cth_easy_pause; exit 1; fi
printf "Pega la URL PostgreSQL de destino: "
read -r TARGET
if [ -z "$TARGET" ]; then echo "URL vacía."; cth_easy_pause; exit 1; fi
SOURCE="sqlite:///$DATA_DIR/calculatuhuella.db"
cd "$CHECK_ROOT" || exit 1
"$CHECK_ROOT/.venv/bin/python" scripts/migrate_sqlite_to_postgresql.py --source "$SOURCE" --target "$TARGET" --plan || { cth_easy_pause; exit 1; }
echo
printf "Escribe MIGRAR para copiar los datos a una base VACÍA: "
read -r CONFIRM
if [ "$CONFIRM" != "MIGRAR" ]; then echo "Cancelado."; cth_easy_pause; exit 0; fi
"$CHECK_ROOT/.venv/bin/python" scripts/migrate_sqlite_to_postgresql.py --source "$SOURCE" --target "$TARGET" --confirm MIGRAR
STATUS=$?
cth_easy_pause
exit "$STATUS"
