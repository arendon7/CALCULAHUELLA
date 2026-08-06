#!/usr/bin/env bash
set -u
SOURCE_ROOT="$(cd "$(dirname "$0")" && pwd)"
source "$SOURCE_ROOT/scripts/mac_lifecycle_common.sh"
cth_init_install_paths "$SOURCE_ROOT"
cth_mkdirs

LOG="$CTH_LOG_DIR/instalacion_v0453.log"
STAMP="$(date +%Y%m%d_%H%M%S)"
STAGING="$CTH_INSTALL_ROOT/.staging_v0453_$$"
LEGACY_DB=""

clear 2>/dev/null || true
cat <<'BANNER'
============================================================
      CALCULA TU HUELLA V1.0.0 · INSTALAR O ACTUALIZAR
============================================================

Este único comando:
  1. respalda los datos existentes;
  2. instala o actualiza la plataforma completa;
  3. migra la base de datos;
  4. crea el acceso en Aplicaciones y en el Escritorio;
  5. mueve versiones anteriores a la Papelera después de validar.

Los datos quedan separados del código y no se borran al actualizar.
BANNER

cth_stop_installed_app
LEGACY_DB="$(cth_find_best_legacy_db 2>/dev/null || true)"
if [ -n "$LEGACY_DB" ]; then
  echo "Base encontrada para conservar: $LEGACY_DB"
fi

if [ -f "$CTH_DB_PATH" ]; then
  echo "Creando respaldo previo de la base instalada..."
  cp "$CTH_DB_PATH" "$CTH_BACKUP_DIR/calculatuhuella_pre_v0453_${STAMP}.db" || {
    echo "No fue posible crear el respaldo. La actualización se detendrá."
    exit 1
  }
fi

echo "Copiando la nueva versión al área de instalación..."
cth_copy_release_to_staging "$STAGING" || exit 1
cth_activate_release "$STAGING" || exit 1

rollback_install() {
  local status="$1"
  echo
  echo "La instalación no terminó correctamente. Restaurando el código anterior..."
  rm -rf "$CTH_CODE_DIR"
  if [ -d "$CTH_INSTALL_ROOT/previous" ]; then
    mv "$CTH_INSTALL_ROOT/previous" "$CTH_CODE_DIR"
  fi
  echo "Los datos y respaldos no fueron eliminados."
  echo "Registro: $LOG"
  command -v open >/dev/null 2>&1 && open -a TextEdit "$LOG" >/dev/null 2>&1 || true
  if [ -t 0 ]; then
    printf '\nPresiona Enter para cerrar...'
    read -r _unused
  fi
  exit "$status"
}

if [ "${CTH_TEST_MODE:-0}" = "1" ]; then
  echo "Modo de prueba: se omite instalación de dependencias y arranque." | tee -a "$LOG"
else
  echo "Instalando dependencias y migrando datos..."
  (
    export CTH_DATA_DIR CTH_DB_PATH CTH_RUNTIME_DIR
    export INSTANCE_DIR="$CTH_DATA_DIR"
    export DATABASE_URL="sqlite:///$CTH_DB_PATH"
    export CTH_LEGACY_DB="$LEGACY_DB"
    "$CTH_CODE_DIR/install_mac.sh"
  ) 2>&1 | tee "$LOG"
  STATUS=${PIPESTATUS[0]}
  [ "$STATUS" -eq 0 ] || rollback_install "$STATUS"
fi

cth_install_app_bundle || rollback_install 1
cth_install_desktop_launcher || rollback_install 1
cth_write_receipt

if [ "${CTH_TEST_MODE:-0}" != "1" ]; then
  echo "Validando instalación final..."
  (
    export INSTANCE_DIR="$CTH_DATA_DIR"
    export DATABASE_URL="sqlite:///$CTH_DB_PATH"
    "$CTH_CODE_DIR/.venv/bin/python" "$CTH_CODE_DIR/scripts/check_ready.py"
  ) >> "$LOG" 2>&1 || rollback_install 1
fi

# Solo después de validar se retiran versiones anteriores.
cth_cleanup_legacy_versions
rm -rf "$CTH_INSTALL_ROOT/previous"

echo
echo "INSTALACIÓN COMPLETADA"
echo "Aplicación: $CTH_APP_BUNDLE"
echo "Acceso rápido: $CTH_DESKTOP_LAUNCHER"
echo "Datos: $CTH_DATA_DIR"
echo "Respaldos: $CTH_BACKUP_DIR"

if [ "${CTH_TEST_MODE:-0}" != "1" ] && [ "${CTH_SKIP_START:-0}" != "1" ]; then
  echo
echo "Abriendo Calcula tu Huella..."
  /bin/bash "$CTH_CODE_DIR/ABRIR_CALCULA_TU_HUELLA.command" --sin-pausa
  STATUS=$?
else
  STATUS=0
fi

if [ -t 0 ] && [ "${CTH_NO_PAUSE:-0}" != "1" ]; then
  printf '\nPresiona Enter para cerrar esta ventana...'
  read -r _unused
fi
exit "$STATUS"
