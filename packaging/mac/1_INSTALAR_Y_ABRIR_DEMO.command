#!/bin/bash
set -euo pipefail

PKG_ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_ROOT="$HOME/Library/Application Support/CalculaTuHuellaDemoFull"
CODE_DIR="$INSTALL_ROOT/current"
DATA_DIR="$INSTALL_ROOT/data"
RUNTIME_DIR="$INSTALL_ROOT/runtime"
LOG_DIR="$DATA_DIR/logs"
ARCH="$(uname -m)"

case "$ARCH" in
  arm64) PACK_ARCH="arm64" ;;
  x86_64) PACK_ARCH="x86_64" ;;
  *) echo "Arquitectura macOS no soportada: $ARCH"; read -r; exit 1 ;;
esac

echo "Verificando integridad del paquete..."
test -f "$PKG_ROOT/MANIFEST_SHA256.txt" || { echo "Falta MANIFEST_SHA256.txt."; read -r; exit 1; }
(
  cd "$PKG_ROOT"
  /usr/bin/shasum -a 256 -c MANIFEST_SHA256.txt >/dev/null
) || { echo "La integridad del paquete no es válida."; read -r; exit 1; }

mkdir -p "$INSTALL_ROOT" "$DATA_DIR" "$RUNTIME_DIR" "$LOG_DIR"
if [ -d "$CODE_DIR" ]; then
  STAMP="$(date +%Y%m%d_%H%M%S)"
  mv "$CODE_DIR" "$INSTALL_ROOT/previous_$STAMP"
fi
mkdir -p "$CODE_DIR"

echo "Copiando código completo..."
/usr/bin/rsync -a "$PKG_ROOT/source/" "$CODE_DIR/"

echo "Copiando Python portable y dependencias offline para $PACK_ARCH..."
rm -rf "$RUNTIME_DIR/python" "$RUNTIME_DIR/vendor" "$RUNTIME_DIR/wheelhouse"
/usr/bin/rsync -a "$PKG_ROOT/runtime/$PACK_ARCH/python/" "$RUNTIME_DIR/python/"
/usr/bin/rsync -a "$PKG_ROOT/wheelhouse/$PACK_ARCH/" "$RUNTIME_DIR/wheelhouse/"
cp "$PKG_ROOT/BUILD_PROVENANCE.json" "$INSTALL_ROOT/BUILD_PROVENANCE.json"

PY="$RUNTIME_DIR/python/bin/python3"
chmod +x "$PY" || true
test -x "$PY" || { echo "Python portable no es ejecutable."; read -r; exit 1; }

echo "Instalando dependencias verificadas desde el propio paquete (sin internet)..."
"$PY" -m ensurepip --upgrade >/dev/null 2>&1 || true
"$PY" -m pip install \
  --no-index \
  --require-hashes \
  --find-links "$RUNTIME_DIR/wheelhouse" \
  --target "$RUNTIME_DIR/vendor" \
  -r "$CODE_DIR/requirements-lock.txt"

export PYTHONPATH="$RUNTIME_DIR/vendor:$CODE_DIR"
export INSTANCE_DIR="$DATA_DIR"
export DATABASE_URL="sqlite:///$DATA_DIR/calculatuhuella.db"
export APP_ENV=local
export SEED_DEMO=true
export SCHEDULER_ENABLED=0
export STRUCTURED_LOGGING=0
export TRUSTED_HOSTS="localhost,127.0.0.1,testserver"

cd "$CODE_DIR"
echo "Aplicando migraciones..."
"$PY" -m alembic upgrade head

echo "Verificando instalación..."
"$PY" scripts/check_ready.py || true

cat > "$INSTALL_ROOT/ABRIR.command" <<EOF
#!/bin/bash
exec /bin/bash "$PKG_ROOT/2_ABRIR_DEMO.command"
EOF
chmod +x "$INSTALL_ROOT/ABRIR.command"

echo
echo "Instalación completada. Abriendo demo..."
exec /bin/bash "$PKG_ROOT/2_ABRIR_DEMO.command"
