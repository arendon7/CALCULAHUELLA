#!/usr/bin/env bash
set -euo pipefail

# Helper local. Nunca se ejecuta desde CI ni desde un release.
# Los SHAs revisados están registrados en docs/design/WEB_DESIGN_SKILL_REGISTRY.json.
command -v npx >/dev/null 2>&1 || {
  echo "ERROR: npx es requerido para instalar skills locales." >&2
  exit 1
}

echo "Instalando especialidades de diseño para el entorno local del agente..."

npx skills@latest add emilkowalski/skills \
  --skill emil-design-eng \
  --skill review-animations \
  --skill find-animation-opportunities \
  --skill prototype

npx skills@latest add https://github.com/Leonxlnx/taste-skill \
  --skill design-taste-frontend \
  --skill redesign-existing-projects \
  --skill imagegen-frontend-web

npx skills@latest add vercel-labs/agent-skills \
  --skill web-design-guidelines \
  --skill writing-guidelines

npx impeccable install

cat <<'EOF'

Bootstrap local completado.

Siguiente paso para Impeccable en un agente compatible:
  /impeccable init

OpenAI frontend-skill se mantiene registrado como referencia/advisory y no se
instala automáticamente aquí: antes de automatizarlo se debe validar la ruta de
instalación del skill curado en el cliente usado.

IMPORTANTE:
- este script no es un gate de CI;
- no actualiza automáticamente versiones ya revisadas;
- las decisiones de CALCULAHUELLA prevalecen sobre cualquier skill externo.
EOF
