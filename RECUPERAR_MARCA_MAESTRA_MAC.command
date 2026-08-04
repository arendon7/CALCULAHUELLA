#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

SEARCH_ROOTS=(
  "$HOME/Downloads"
  "$HOME/Desktop"
  "$HOME/Documents"
  "$ROOT"
)

KNOWN_PACKAGES=(
  "calcula_tu_huella_front_consolidado_v0_37.zip"
  "calcula_tu_huella_marca_maestra_v1.zip"
)

REQUIRED_ASSETS=(
  "logo-oficial.png"
  "logo-oficial-blanco.png"
  "favicon-64.png"
  "favicon-256.png"
)

HTML_NAMES=(
  "v0_44_experiencia.html"
  "experiencia_interna.html"
)

mkdir -p "$ROOT/instance"
REPORT="$ROOT/instance/brand-recovery-mac.json"

printf '\nCalcula tu Huella · Recuperación segura de Marca Maestra\n'
printf 'Repositorio: %s\n\n' "$ROOT"

find_named_file() {
  local name="$1"
  local root
  for root in "${SEARCH_ROOTS[@]}"; do
    [[ -d "$root" ]] || continue
    find "$root" -maxdepth 6 -type f -name "$name" -print 2>/dev/null | head -n 1
  done | head -n 1
}

find_complete_asset_folder() {
  local candidate root asset ok
  for root in "${SEARCH_ROOTS[@]}"; do
    [[ -d "$root" ]] || continue
    while IFS= read -r candidate; do
      ok=1
      for asset in "${REQUIRED_ASSETS[@]}"; do
        [[ -f "$candidate/$asset" ]] || ok=0
      done
      if [[ "$ok" -eq 1 ]]; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done < <(find "$root" -maxdepth 7 -type d -path '*/static/img/brand' -print 2>/dev/null)
  done
  return 1
}

PACKAGE=""
for name in "${KNOWN_PACKAGES[@]}"; do
  PACKAGE="$(find_named_file "$name" || true)"
  [[ -n "$PACKAGE" ]] && break
done

if [[ -z "$PACKAGE" ]]; then
  PACKAGE="$(find_complete_asset_folder || true)"
fi

if [[ -n "$PACKAGE" ]]; then
  printf 'Fuente completa encontrada:\n%s\n\n' "$PACKAGE"
  "$PYTHON" scripts/brand/audit_historical_sources.py "$PACKAGE" \
    --output "$REPORT" --require-exact-package
  "$PYTHON" scripts/brand/import_master_package.py "$PACKAGE" --apply
  "$PYTHON" scripts/brand/verify_master_assets.py --require-master
  printf '\nMarca Maestra exacta instalada y validada.\n'
  printf 'Reporte: %s\n' "$REPORT"
  exit 0
fi

HTML_SOURCES=()
for name in "${HTML_NAMES[@]}"; do
  candidate="$(find_named_file "$name" || true)"
  [[ -n "$candidate" ]] && HTML_SOURCES+=("$candidate")
done

if [[ "${#HTML_SOURCES[@]}" -ge 2 ]]; then
  printf 'No apareció el paquete completo, pero se encontraron dos HTML históricos.\n'
  printf 'Se recuperará únicamente el logo principal; no se derivarán otros activos.\n\n'
  "$PYTHON" scripts/brand/audit_historical_sources.py "${HTML_SOURCES[@]}" --output "$REPORT"
  "$PYTHON" scripts/brand/extract_embedded_master.py "${HTML_SOURCES[@]}" --apply
  printf '\nLogo principal recuperado. Siguen pendientes la variante blanca y los dos favicons.\n'
  printf 'Reporte: %s\n' "$REPORT"
  exit 0
fi

printf 'No se encontró una fuente completa y verificable.\n'
printf 'Nombres prioritarios buscados:\n'
printf '  - %s\n' "${KNOWN_PACKAGES[@]}"
printf '\nNo se modificó ningún archivo del repositorio.\n'
printf 'No se utilizaron los SVG legacy ni los tableros de docs/visual como fuente del logo.\n'
exit 2
