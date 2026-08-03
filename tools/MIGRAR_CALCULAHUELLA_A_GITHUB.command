#!/bin/bash
set -euo pipefail

REPO="arendon7/CALCULAHUELLA"
REPO_URL="https://github.com/${REPO}.git"
BRANCH="migration/v0.45.5"
WORK="$(mktemp -d -t calculahuella-github-XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

clear
printf '\nCalcula tu Huella · migración segura a GitHub\n'
printf 'Repositorio: %s\n' "$REPO"
printf 'Rama: %s\n\n' "$BRANCH"

find_zip() {
  local candidate
  for candidate in \
    "$HOME/Downloads/calcula_tu_huella_v0_45_5_completa_mac.zip" \
    "$HOME/Downloads/calcula_tu_huella_v0_45_5_completa_mac(1).zip" \
    "$(pwd)/calcula_tu_huella_v0_45_5_completa_mac.zip"; do
    if [ -f "$candidate" ]; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  find "$HOME/Downloads" -maxdepth 1 -type f -iname '*v0_45_5*mac*.zip' -print -quit 2>/dev/null || true
}

ZIP_PATH="$(find_zip)"
if [ -z "$ZIP_PATH" ] || [ ! -f "$ZIP_PATH" ]; then
  if command -v osascript >/dev/null 2>&1; then
    ZIP_PATH="$(osascript <<'APPLESCRIPT'
try
  POSIX path of (choose file with prompt "Selecciona calcula_tu_huella_v0_45_5_completa_mac.zip" of type {"zip"})
on error
  return ""
end try
APPLESCRIPT
)"
  fi
fi

if [ -z "$ZIP_PATH" ] || [ ! -f "$ZIP_PATH" ]; then
  echo "No se encontró el ZIP de la v0.45.5. Descárgalo y vuelve a ejecutar este archivo."
  read -r -p "Presiona Enter para cerrar..." _
  exit 1
fi

echo "Fuente: $ZIP_PATH"

for cmd in git unzip rsync python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Falta la herramienta requerida: $cmd"
    echo "Instala las herramientas de línea de comandos de Xcode y vuelve a intentarlo."
    xcode-select --install >/dev/null 2>&1 || true
    read -r -p "Presiona Enter para cerrar..." _
    exit 1
  fi
done

if command -v gh >/dev/null 2>&1; then
  if ! gh auth status >/dev/null 2>&1; then
    echo "Se abrirá GitHub para autorizar el envío del código."
    gh auth login --web --git-protocol https
  fi
  gh auth setup-git >/dev/null 2>&1 || true
else
  echo "GitHub CLI no está instalado. Se intentará usar la autenticación Git existente."
  echo "Si el envío falla, instala GitHub CLI con: brew install gh"
fi

echo "Descomprimiendo la versión canónica..."
mkdir -p "$WORK/source"
unzip -q "$ZIP_PATH" -d "$WORK/source"

APP_MAIN="$(find "$WORK/source" -type f -path '*/app/main.py' -print -quit)"
if [ -z "$APP_MAIN" ]; then
  echo "El ZIP no contiene la estructura esperada app/main.py."
  exit 1
fi
SOURCE_ROOT="$(dirname "$(dirname "$APP_MAIN")")"

echo "Clonando el repositorio..."
git clone "$REPO_URL" "$WORK/repo"
cd "$WORK/repo"
git fetch origin "$BRANCH"
git checkout -B "$BRANCH" "origin/$BRANCH"

PRESERVE_README="$WORK/README.md"
cp README.md "$PRESERVE_README"

echo "Copiando código, recursos visuales, pruebas y documentación..."
rsync -a "$SOURCE_ROOT/" ./ \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='instance/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.db' \
  --exclude='*.sqlite' \
  --exclude='*.sqlite3' \
  --exclude='*.zip' \
  --exclude='*_manifest.txt' \
  --exclude='README.md' \
  --exclude='.gitignore' \
  --exclude='.gitattributes' \
  --exclude='.github/' \
  --exclude='render.yaml'

cp "$PRESERVE_README" README.md
mkdir -p docs/releases
for file in VALIDACION_V*.md; do
  [ -e "$file" ] || continue
  mv "$file" docs/releases/
done

rm -rf instance .pytest_cache
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.DS_Store' \) -delete
find . -type f \( -name '*.sh' -o -name '*.command' \) -exec chmod +x {} +
chmod +x "Calcula tu Huella.app/Contents/MacOS/CalculaTuHuella" 2>/dev/null || true

printf '\nValidando estructura...\n'
python3 -m compileall -q app scripts tests run.py
find . -type f \( -name '*.sh' -o -name '*.command' \) -print0 | xargs -0 -n1 bash -n

FORBIDDEN="$(find . -path './.git' -prune -o -type f \( -name '.env' -o -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '*.zip' \) -print)"
if [ -n "$FORBIDDEN" ]; then
  echo "Se detectaron archivos que no deben publicarse:"
  echo "$FORBIDDEN"
  exit 1
fi

git add -A
git diff --cached --check

if git diff --cached --quiet; then
  echo "No hay cambios nuevos para enviar."
else
  git commit -m "feat: importar base canónica v0.45.5"
  echo "Enviando la migración a GitHub..."
  if ! git push -u origin "$BRANCH"; then
    echo
    echo "GitHub requiere autenticación para publicar."
    echo "Instala GitHub CLI con 'brew install gh', ejecuta 'gh auth login' y vuelve a abrir este archivo."
    exit 1
  fi
fi

PR_URL="https://github.com/${REPO}/compare/main...${BRANCH}?expand=1"
if command -v gh >/dev/null 2>&1; then
  if ! gh pr view "$BRANCH" --repo "$REPO" >/dev/null 2>&1; then
    gh pr create \
      --repo "$REPO" \
      --base main \
      --head "$BRANCH" \
      --title "Migrar base canónica v0.45.5" \
      --body "Importa la v0.45.5 completa, excluye datos y secretos locales, incorpora CI y deja preparado el despliegue demostrativo desde GitHub. Relacionado con #1."
  fi
  PR_URL="$(gh pr view "$BRANCH" --repo "$REPO" --json url --jq .url 2>/dev/null || echo "$PR_URL")"
fi

printf '\nMigración enviada correctamente.\n'
printf 'Pull request: %s\n' "$PR_URL"
open "$PR_URL" >/dev/null 2>&1 || true
printf '\nPuedes cerrar esta ventana.\n'
read -r -p "Presiona Enter para finalizar..." _
