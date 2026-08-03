#!/usr/bin/env python3
"""Genera el inventario SHA-256 y la clasificación inicial de una fuente descomprimida."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

EXCLUDED_DIRS = {".pytest_cache", "__pycache__", ".venv", "venv"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}
MAC_SCRIPTS = {
    "install_mac.sh",
    "start_mac.sh",
    "stop_mac.sh",
    "repair_mac.sh",
    "backup_mac.sh",
    "restore_mac.sh",
    "audit_mac.sh",
}


def classify(path: Path, relative: str) -> tuple[str, str]:
    if any(part in EXCLUDED_DIRS for part in path.parts) or path.suffix in EXCLUDED_SUFFIXES:
        return "excluir", "Caché, bytecode, entorno o log generado"
    if relative.startswith("instance/"):
        if path.name == ".gitkeep":
            return "versionar", "Mantiene el directorio local vacío"
        return "excluir", "Persistencia local o base de datos"
    if relative.endswith((".zip", ".sha256", "_manifest.txt")):
        return "archivar_fuera_git", "Artefacto de distribución o manifiesto de entrega"
    if relative.startswith("Calcula tu Huella.app/"):
        return "mover_packaging", "Fuente de empaquetado macOS"
    if path.suffix == ".command" or path.name.endswith("_mac.sh") or path.name in MAC_SCRIPTS:
        return "mover_scripts_macos", "Script macOS; preservar permiso ejecutable"
    if relative.startswith("docs/") or path.name.startswith("VALIDACION_"):
        return "versionar_documentacion", "Documentación vigente o trazabilidad histórica"
    return "versionar", "Código, configuración o recurso del producto"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Carpeta fuente descomprimida")
    parser.add_argument("--output", type=Path, default=Path("source_inventory.csv"))
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_dir():
        raise SystemExit(f"La fuente no existe o no es una carpeta: {source}")

    rows: list[dict[str, str | int]] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        decision, reason = classify(path, relative)
        rows.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": sha256(path),
                "decision": decision,
                "reason": reason,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    tree_hash = hashlib.sha256(
        "\n".join(f"{row['path']}\t{row['sha256']}" for row in rows).encode("utf-8")
    ).hexdigest()
    summary = {
        "source": source.name,
        "total_files": len(rows),
        "total_bytes": sum(int(row["size"]) for row in rows),
        "decisions": dict(Counter(str(row["decision"]) for row in rows)),
        "tree_sha256": tree_hash,
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
