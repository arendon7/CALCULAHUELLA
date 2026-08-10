#!/bin/bash
set -euo pipefail

INSTALL_ROOT="$HOME/Library/Application Support/CalculaTuHuellaDemoFull"
DATA_DIR="$INSTALL_ROOT/data"
PKG_ROOT="$(cd "$(dirname "$0")" && pwd)"

/bin/bash "$PKG_ROOT/3_CERRAR_DEMO.command" || true

if [ -f "$DATA_DIR/calculatuhuella.db" ]; then
  mkdir -p "$INSTALL_ROOT/backups"
  cp "$DATA_DIR/calculatuhuella.db" "$INSTALL_ROOT/backups/calculatuhuella_antes_reset_$(date +%Y%m%d_%H%M%S).db"
fi

rm -f \
  "$DATA_DIR/calculatuhuella.db" \
  "$DATA_DIR/calculatuhuella.db-wal" \
  "$DATA_DIR/calculatuhuella.db-shm"

echo "Datos demo reiniciados. Abriendo una base limpia..."
exec /bin/bash "$PKG_ROOT/2_ABRIR_DEMO.command"
