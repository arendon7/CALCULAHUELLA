#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

EXCLUDED_DIRS = {
    ".git", ".github", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "htmlcov", "node_modules", "__MACOSX",
}
EXCLUDED_RUNTIME_DIRS = {"backups", "logs", "uploads", "reports", "certifications", "import_staging", "mail_outbox"}
EXCLUDED_NAMES = {
    ".DS_Store", ".coverage",
    "source_inventory_v0461.csv", "REPOSITORY_TREE_SUMMARY_V0461.json",
    "source_inventory_v0470.csv", "REPOSITORY_TREE_SUMMARY_V0470.json",
    "source_inventory_v0480.csv", "REPOSITORY_TREE_SUMMARY_V0480.json",
    "source_inventory_v0490.csv", "REPOSITORY_TREE_SUMMARY_V0490.json",
    "source_inventory_v0500.csv", "REPOSITORY_TREE_SUMMARY_V0500.json",
    "source_inventory_v0510.csv", "REPOSITORY_TREE_SUMMARY_V0510.json",
    "source_inventory_v0520.csv", "REPOSITORY_TREE_SUMMARY_V0520.json",
    "source_inventory_v0530.csv", "REPOSITORY_TREE_SUMMARY_V0530.json",
    "source_inventory_v0540.csv", "REPOSITORY_TREE_SUMMARY_V0540.json",
    "source_inventory_v0550.csv", "REPOSITORY_TREE_SUMMARY_V0550.json",
    "source_inventory_v0560.csv", "REPOSITORY_TREE_SUMMARY_V0560.json",
    "source_inventory_v0570.csv", "REPOSITORY_TREE_SUMMARY_V0570.json",
    "source_inventory_v100final0.csv", "REPOSITORY_TREE_SUMMARY_V100FINAL.json",
    "MANIFIESTO_V0_47_0.txt", "MANIFIESTO_V0_48_0.txt", "MANIFIESTO_V0_49_0.txt", "MANIFIESTO_V0_50_0.txt", "MANIFIESTO_V0_51_0.txt", "MANIFIESTO_V0_52_0.txt", "MANIFIESTO_V0_53_0.txt", "MANIFIESTO_V0_54_0.txt", "MANIFIESTO_V0_55_0.txt", "MANIFIESTO_V0_56_0.txt", "MANIFIESTO_V0_57_0.txt",
}
FORBIDDEN_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".pem", ".key", ".p12", ".pfx", ".pyc"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".xlsx", ".zip"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def included_files(root: Path) -> list[Path]:
    output: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.name in EXCLUDED_NAMES:
            continue
        if relative.parts and relative.parts[0] == "instance":
            continue
        if any(part in EXCLUDED_RUNTIME_DIRS for part in relative.parts):
            continue
        output.append(path)
    return sorted(output, key=lambda item: item.relative_to(root).as_posix())


def forbidden_reason(root: Path, path: Path) -> str | None:
    relative = path.relative_to(root)
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return f"extensión sensible {path.suffix}"
    if path.name in {".env", ".env.local"}:
        return "configuración local o secreto"
    if relative.parts and relative.parts[0] in EXCLUDED_RUNTIME_DIRS:
        return "dato de ejecución"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera inventario reproducible del paquete local")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = included_files(root)
    rows: list[dict[str, object]] = []
    forbidden: list[dict[str, str]] = []
    tree_digest = hashlib.sha256()
    binary_files: list[str] = []

    for path in files:
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        digest = sha256(path)
        rows.append({"path": relative, "size": size, "sha256": digest})
        tree_digest.update(relative.encode("utf-8") + b"\0")
        tree_digest.update(str(size).encode("ascii") + b"\0")
        tree_digest.update(digest.encode("ascii") + b"\n")
        if path.suffix.lower() in BINARY_SUFFIXES:
            binary_files.append(relative)
        reason = forbidden_reason(root, path)
        if reason:
            forbidden.append({"path": relative, "reason": reason})

    csv_path = Path(args.csv)
    summary_path = Path(args.summary)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "size", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "release": "1.0.0",
        "total_files": len(rows),
        "total_bytes": sum(int(row["size"]) for row in rows),
        "tree_sha256": tree_digest.hexdigest(),
        "binary_files": binary_files,
        "forbidden_files": forbidden,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.strict and forbidden:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
