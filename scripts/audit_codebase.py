from __future__ import annotations

import sys as _sys
from pathlib import Path as _BootstrapPath

_PROJECT_ROOT = _BootstrapPath(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))


import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.consolidation import codebase_metrics  # noqa: E402

metrics = codebase_metrics(ROOT)
payload = {"generated_at": datetime.now(UTC).isoformat(), **metrics}
output_json = ROOT / "docs" / "AUDITORIA_CODIGO_GENERADA.json"
output_md = ROOT / "docs" / "AUDITORIA_CODIGO_GENERADA.md"
output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
lines = [
    "# Auditoría estática generada",
    "",
    f"Fecha UTC: `{payload['generated_at']}`",
    "",
    "## Métricas",
    "",
    f"- Archivos Python: **{metrics['python_files']}**",
    f"- Plantillas HTML: **{metrics['templates']}**",
    f"- Rutas HTTP detectadas: **{metrics['routes']}**",
    f"- Pruebas detectadas: **{metrics['tests']}**",
    f"- Líneas Python: **{metrics['total_lines']}**",
    "",
    "## Archivos más grandes",
    "",
    "| Archivo | Líneas |",
    "|---|---:|",
]
for item in metrics["largest_files"]:
    lines.append(f"| `{item['path']}` | {item['lines']} |")
lines.extend([
    "",
    "## Interpretación",
    "",
    "Estas cifras describen tamaño y concentración, no calidad. Los archivos de mayor tamaño deben revisarse para decidir si conviene extraer routers, servicios, repositorios o modelos por dominio.",
])
output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(output_md)
print(output_json)
