#!/usr/bin/env bash
# Ciclo de vida macOS V1.0. Compatible con Bash 3.2.

CTH_RELEASE_VERSION="1.0.0"
CTH_RELEASE_SLUG="v1_0_0"

cth_abs_path() {
  local path="$1"
  if [ -d "$path" ]; then
    (cd "$path" 2>/dev/null && pwd -P)
  else
    printf '%s\n' "$path"
  fi
}

cth_init_install_paths() {
  CTH_SOURCE_ROOT="$(cth_abs_path "$1")"
  CTH_INSTALL_ROOT="${CTH_INSTALL_ROOT:-$HOME/Library/Application Support/CalculaTuHuella}"
  CTH_CODE_DIR="${CTH_CODE_DIR:-$CTH_INSTALL_ROOT/current}"
  CTH_DATA_DIR="${CTH_DATA_DIR:-$CTH_INSTALL_ROOT/data}"
  CTH_BACKUP_DIR="${CTH_BACKUP_DIR:-$CTH_INSTALL_ROOT/backups}"
  CTH_RUNTIME_DIR="${CTH_RUNTIME_DIR:-$CTH_INSTALL_ROOT/runtime}"
  CTH_LOG_DIR="${CTH_LOG_DIR:-$CTH_INSTALL_ROOT/logs}"
  CTH_APPLICATIONS_DIR="${CTH_APPLICATIONS_DIR:-$HOME/Applications}"
  CTH_DESKTOP_DIR="${CTH_DESKTOP_DIR:-$HOME/Desktop}"
  CTH_APP_BUNDLE="$CTH_APPLICATIONS_DIR/Calcula tu Huella.app"
  CTH_DESKTOP_LAUNCHER="$CTH_DESKTOP_DIR/ABRIR CALCULA TU HUELLA.command"
  CTH_DB_PATH="${CTH_DB_PATH:-$CTH_DATA_DIR/calculatuhuella.db}"
  CTH_LEGACY_SEARCH_ROOTS="${CTH_LEGACY_SEARCH_ROOTS:-$HOME/Downloads:$HOME/Desktop:$HOME/Documents:$HOME/Applications}"
  export CTH_SOURCE_ROOT CTH_INSTALL_ROOT CTH_CODE_DIR CTH_DATA_DIR CTH_BACKUP_DIR
  export CTH_RUNTIME_DIR CTH_LOG_DIR CTH_APPLICATIONS_DIR CTH_DESKTOP_DIR CTH_APP_BUNDLE
  export CTH_DESKTOP_LAUNCHER CTH_DB_PATH CTH_LEGACY_SEARCH_ROOTS
}

cth_mkdirs() {
  mkdir -p "$CTH_INSTALL_ROOT" "$CTH_DATA_DIR" "$CTH_BACKUP_DIR" "$CTH_RUNTIME_DIR" "$CTH_LOG_DIR" "$CTH_APPLICATIONS_DIR"
  mkdir -p "$CTH_DATA_DIR/uploads" "$CTH_DATA_DIR/reports" "$CTH_DATA_DIR/backups" "$CTH_DATA_DIR/logs"
  mkdir -p "$CTH_DATA_DIR/import_staging" "$CTH_DATA_DIR/mail_outbox" "$CTH_DATA_DIR/certifications"
  [ -d "$CTH_DESKTOP_DIR" ] || mkdir -p "$CTH_DESKTOP_DIR"
}

cth_stop_pid_file() {
  local pid_file="$1"
  [ -f "$pid_file" ] || return 0
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
    echo "Deteniendo versión en ejecución (proceso $pid)..."
    kill "$pid" >/dev/null 2>&1 || true
    local count=0
    while kill -0 "$pid" >/dev/null 2>&1 && [ "$count" -lt 12 ]; do
      sleep 1
      count=$((count + 1))
    done
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  fi
  rm -f "$pid_file"
}

cth_stop_installed_app() {
  cth_stop_pid_file "$CTH_RUNTIME_DIR/app.pid"
  if [ -f "$CTH_CODE_DIR/.runtime/app.pid" ]; then
    cth_stop_pid_file "$CTH_CODE_DIR/.runtime/app.pid"
  fi
  rm -f "$CTH_RUNTIME_DIR/app.port" "$CTH_RUNTIME_DIR/app.url"
}

cth_is_legacy_name() {
  local name="$1"
  case "$name" in
    calcula_tu_huella_v*|calcula-tu-huella-v*|"Calcula tu Huella v"*|"Calcula tu Huella V"*) return 0 ;;
    *) return 1 ;;
  esac
}

cth_is_platform_root() {
  local path="$1"
  [ -d "$path/app" ] && [ -f "$path/run.py" ] && [ -f "$path/alembic.ini" ]
}

cth_list_legacy_dirs() {
  local old_ifs="$IFS"
  IFS=':'
  for search_root in $CTH_LEGACY_SEARCH_ROOTS; do
    [ -d "$search_root" ] || continue
    find "$search_root" -maxdepth 2 -type d \( \
      -iname 'calcula_tu_huella_v*' -o \
      -iname 'calcula-tu-huella-v*' -o \
      -iname 'Calcula tu Huella v*' \
    \) 2>/dev/null
  done
  IFS="$old_ifs"
}

cth_is_excluded_path() {
  local candidate="$(cth_abs_path "$1")"
  [ "$candidate" = "$CTH_SOURCE_ROOT" ] && return 0
  [ "$candidate" = "$(cth_abs_path "$CTH_CODE_DIR")" ] && return 0
  case "$candidate" in
    "$CTH_INSTALL_ROOT"|"$CTH_INSTALL_ROOT"/*) return 0 ;;
  esac
  return 1
}

cth_stat_mtime() {
  local path="$1"
  stat -f '%m' "$path" 2>/dev/null || stat -c '%Y' "$path" 2>/dev/null || echo 0
}

cth_find_best_legacy_db() {
  local best=""
  local best_time=0
  local db mtime candidate

  if [ -f "$CTH_DB_PATH" ]; then
    printf '%s\n' "$CTH_DB_PATH"
    return 0
  fi

  # La propia entrega puede contener una base migrable.
  for db in "$CTH_SOURCE_ROOT"/instance/calculatuhuella*.db; do
    [ -f "$db" ] || continue
    mtime="$(cth_stat_mtime "$db")"
    if [ "$mtime" -gt "$best_time" ]; then best="$db"; best_time="$mtime"; fi
  done

  cth_list_legacy_dirs | while IFS= read -r candidate; do
    [ -n "$candidate" ] || continue
    cth_is_excluded_path "$candidate" && continue
    cth_is_platform_root "$candidate" || continue
    find "$candidate/instance" -maxdepth 1 -type f -name 'calculatuhuella*.db' 2>/dev/null
  done > "$CTH_INSTALL_ROOT/.legacy_db_candidates.$$"

  if [ -f "$CTH_INSTALL_ROOT/.legacy_db_candidates.$$" ]; then
    while IFS= read -r db; do
      [ -f "$db" ] || continue
      mtime="$(cth_stat_mtime "$db")"
      if [ "$mtime" -gt "$best_time" ]; then best="$db"; best_time="$mtime"; fi
    done < "$CTH_INSTALL_ROOT/.legacy_db_candidates.$$"
    rm -f "$CTH_INSTALL_ROOT/.legacy_db_candidates.$$"
  fi

  [ -n "$best" ] && printf '%s\n' "$best"
}

cth_archive_legacy_data() {
  local candidate="$1"
  local timestamp="$2"
  local base safe archive
  base="$(basename "$candidate")"
  safe="$(printf '%s' "$base" | tr ' /' '__' | tr -cd '[:alnum:]_.-')"
  archive="$CTH_BACKUP_DIR/${safe}_${timestamp}.tar.gz"
  if [ -d "$candidate/instance" ] || [ -f "$candidate/.env" ]; then
    echo "Respaldando datos de $base..."
    (
      cd "$candidate" || exit 1
      items=""
      [ -d instance ] && items="$items instance"
      [ -f .env ] && items="$items .env"
      # shellcheck disable=SC2086
      tar -czf "$archive" $items
    ) || return 1
  fi
}

cth_merge_legacy_files() {
  local candidate="$1"
  [ -d "$candidate/instance" ] || return 0
  local subdir
  for subdir in uploads reports backups import_staging mail_outbox certifications; do
    [ -d "$candidate/instance/$subdir" ] || continue
    mkdir -p "$CTH_DATA_DIR/$subdir"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --ignore-existing "$candidate/instance/$subdir/" "$CTH_DATA_DIR/$subdir/"
    else
      cp -Rn "$candidate/instance/$subdir/." "$CTH_DATA_DIR/$subdir/" 2>/dev/null || true
    fi
  done
}

cth_copy_release_to_staging() {
  local staging="$1"
  rm -rf "$staging"
  mkdir -p "$staging"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.venv' --exclude '.runtime' --exclude 'instance' \
      --exclude '__pycache__' --exclude '*.pyc' --exclude '.pytest_cache' \
      "$CTH_SOURCE_ROOT/" "$staging/"
  else
    cp -R "$CTH_SOURCE_ROOT/." "$staging/"
    rm -rf "$staging/.venv" "$staging/.runtime" "$staging/instance" "$staging/.pytest_cache"
    find "$staging" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    find "$staging" -name '*.pyc' -delete 2>/dev/null || true
  fi
  mkdir -p "$staging/instance" "$staging/.runtime"
}

cth_activate_release() {
  local staging="$1"
  local previous="$CTH_INSTALL_ROOT/previous"
  rm -rf "$previous"
  if [ -d "$CTH_CODE_DIR" ]; then
    mv "$CTH_CODE_DIR" "$previous"
  fi
  mv "$staging" "$CTH_CODE_DIR"
}

cth_install_app_bundle() {
  rm -rf "$CTH_APP_BUNDLE"
  cp -R "$CTH_CODE_DIR/Calcula tu Huella.app" "$CTH_APP_BUNDLE"
  chmod +x "$CTH_APP_BUNDLE/Contents/MacOS/CalculaTuHuella" 2>/dev/null || true
  /usr/bin/xattr -dr com.apple.quarantine "$CTH_APP_BUNDLE" >/dev/null 2>&1 || true
}

cth_install_desktop_launcher() {
  cat > "$CTH_DESKTOP_LAUNCHER" <<EOF_LAUNCHER
#!/usr/bin/env bash
INSTALL_ROOT="\${CTH_INSTALL_ROOT:-\$HOME/Library/Application Support/CalculaTuHuella}"
SCRIPT="\$INSTALL_ROOT/current/ABRIR_CALCULA_TU_HUELLA.command"
if [ ! -f "\$SCRIPT" ]; then
  /usr/bin/osascript -e 'display alert "Calcula tu Huella" message "La aplicación no está instalada. Ejecuta nuevamente el instalador." as critical' 2>/dev/null || true
  exit 1
fi
exec /bin/bash "\$SCRIPT"
EOF_LAUNCHER
  chmod +x "$CTH_DESKTOP_LAUNCHER"
  /usr/bin/xattr -d com.apple.quarantine "$CTH_DESKTOP_LAUNCHER" >/dev/null 2>&1 || true
}

cth_move_to_trash() {
  local path="$1"
  [ -e "$path" ] || return 0
  local trash="${CTH_TRASH_DIR:-$HOME/.Trash}"
  mkdir -p "$trash"
  local base target stamp
  base="$(basename "$path")"
  stamp="$(date +%Y%m%d_%H%M%S)"
  target="$trash/${base}_${stamp}"
  local n=1
  while [ -e "$target" ]; do
    target="$trash/${base}_${stamp}_$n"
    n=$((n + 1))
  done
  mv "$path" "$target"
  echo "Versión anterior movida a la Papelera: $base"
}

cth_cleanup_legacy_versions() {
  [ "${CTH_DELETE_OLD_VERSIONS:-1}" = "1" ] || return 0
  local candidate timestamp
  timestamp="$(date +%Y%m%d_%H%M%S)"
  cth_list_legacy_dirs > "$CTH_INSTALL_ROOT/.legacy_dirs.$$"
  if [ -f "$CTH_INSTALL_ROOT/.legacy_dirs.$$" ]; then
    while IFS= read -r candidate; do
      [ -n "$candidate" ] || continue
      cth_is_excluded_path "$candidate" && continue
      cth_is_platform_root "$candidate" || continue
      cth_archive_legacy_data "$candidate" "$timestamp" || {
        echo "No se pudo respaldar $candidate; no se eliminará."
        continue
      }
      cth_merge_legacy_files "$candidate"
      cth_move_to_trash "$candidate"
    done < "$CTH_INSTALL_ROOT/.legacy_dirs.$$"
    rm -f "$CTH_INSTALL_ROOT/.legacy_dirs.$$"
  fi

  # Solo archivos ZIP con nombre inequívoco de versiones anteriores. La entrega actual V1.0.0 se conserva.
  local old_ifs="$IFS" search_root archive name
  IFS=':'
  for search_root in $CTH_LEGACY_SEARCH_ROOTS; do
    [ -d "$search_root" ] || continue
    find "$search_root" -maxdepth 1 -type f -iname 'calcula_tu_huella_v*.zip' 2>/dev/null | while IFS= read -r archive; do
      name="$(basename "$archive")"
      normalized_name="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')"
      case "$normalized_name" in
        *"$CTH_RELEASE_SLUG"*) ;;
        *) cth_move_to_trash "$archive" ;;
      esac
    done
  done
  IFS="$old_ifs"
}

cth_write_receipt() {
  cat > "$CTH_INSTALL_ROOT/installation.json" <<EOF_RECEIPT
{
  "product": "Calcula tu Huella",
  "version": "$CTH_RELEASE_VERSION",
  "installed_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "code_dir": "$CTH_CODE_DIR",
  "data_dir": "$CTH_DATA_DIR",
  "database": "$CTH_DB_PATH"
}
EOF_RECEIPT
}
