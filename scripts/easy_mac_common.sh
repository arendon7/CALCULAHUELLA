#!/usr/bin/env bash

cth_easy_root() {
  cd "$(dirname "$1")" >/dev/null 2>&1 && pwd
}

cth_easy_instance_dir() {
  local root="$1"
  printf '%s\n' "${CTH_DATA_DIR:-${INSTANCE_DIR:-$root/instance}}"
}

cth_easy_runtime_dir() {
  local root="$1"
  printf '%s\n' "${CTH_RUNTIME_DIR:-$root/.runtime}"
}

cth_easy_prepare() {
  local root="$1"
  local instance runtime
  instance="$(cth_easy_instance_dir "$root")"
  runtime="$(cth_easy_runtime_dir "$root")"
  mkdir -p "$runtime" "$instance/logs" "$instance/backups" "$instance/uploads" "$instance/reports" "$instance/certifications" "$instance/import_staging" "$instance/mail_outbox"
  /usr/bin/xattr -dr com.apple.quarantine "$root" >/dev/null 2>&1 || true
  find "$root" -type f \( -name "*.sh" -o -name "*.command" \) -exec chmod +x {} \; >/dev/null 2>&1 || true
}

cth_easy_pause() {
  if [ -t 0 ]; then
    printf "\nPresiona Enter para cerrar esta ventana..."
    read -r _cth_unused
  fi
}

cth_easy_python_ready() {
  local root="$1"
  local py="$root/.venv/bin/python"
  [ -x "$py" ] || return 1
  "$py" - <<'PY' >/dev/null 2>&1
import sys
if sys.version_info < (3, 11):
    raise SystemExit(1)
import alembic, fastapi, jinja2, openpyxl, pydantic, reportlab, sqlalchemy, uvicorn
PY
}

cth_easy_open_url() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  fi
}

cth_easy_running_pid() {
  local root="$1"
  local runtime pid_file pid
  runtime="$(cth_easy_runtime_dir "$root")"
  pid_file="$runtime/app.pid"
  [ -f "$pid_file" ] || return 1
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  kill -0 "$pid" >/dev/null 2>&1 || return 1
  printf '%s\n' "$pid"
}
