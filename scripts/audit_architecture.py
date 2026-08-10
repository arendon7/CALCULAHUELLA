from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

BASELINE = {
    "main_lines": 4674,
    "database_lines": 2171,
    "total_routes": 344,
    "main_routes": 153,
    "orm_tables": 124,
}

ROUTE_PATTERN = re.compile(r'@(?:app|router)\.(get|post|put|patch|delete)\(\s*[fru]*[\'"]([^\'"]+)')
TABLE_PATTERN = re.compile(r'__tablename__\s*=\s*[\'"]([^\'"]+)')


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())


def route_inventory(py_files: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in py_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for method, route in ROUTE_PATTERN.findall(text):
            rows.append({
                "method": method.upper(),
                "path": route,
                "file": str(path.relative_to(ROOT)),
            })
    return rows


def orm_tables(py_files: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in py_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for table in TABLE_PATTERN.findall(text):
            rows.append({"table": table, "file": str(path.relative_to(ROOT))})
    return rows


def function_hotspots(path: Path, *, limit: int = 20) -> list[dict[str, int | str]]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    rows: list[dict[str, int | str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            rows.append({
                "name": node.name,
                "start": node.lineno,
                "end": end,
                "lines": end - node.lineno + 1,
            })
    return sorted(rows, key=lambda item: int(item["lines"]), reverse=True)[:limit]


def snapshot() -> dict[str, object]:
    py_files = sorted(APP.rglob("*.py"))
    routes = route_inventory(py_files)
    tables = orm_tables(py_files)
    route_files: dict[str, int] = {}
    for row in routes:
        route_files[row["file"]] = route_files.get(row["file"], 0) + 1

    main = APP / "main.py"
    database = APP / "database.py"
    return {
        "python_files": len(py_files),
        "python_lines": sum(line_count(path) for path in py_files),
        "main_lines": line_count(main),
        "database_lines": line_count(database),
        "total_routes": len(routes),
        "main_routes": route_files.get("app/main.py", 0),
        "orm_tables": len(tables),
        "top_route_files": sorted(route_files.items(), key=lambda item: item[1], reverse=True)[:15],
        "top_python_files": sorted(
            ((str(path.relative_to(ROOT)), line_count(path)) for path in py_files),
            key=lambda item: item[1],
            reverse=True,
        )[:15],
        "main_function_hotspots": function_hotspots(main),
    }


def regressions(data: dict[str, object]) -> list[str]:
    failures: list[str] = []
    for key, limit in BASELINE.items():
        current = int(data[key])
        if current > limit:
            failures.append(f"{key}: {current} > baseline {limit}")
    return failures


def markdown(data: dict[str, object]) -> str:
    rows = [
        "# Arquitectura · snapshot",
        "",
        f"- Archivos Python: {data['python_files']}",
        f"- Líneas Python: {data['python_lines']}",
        f"- `app/main.py`: {data['main_lines']} líneas · {data['main_routes']} rutas",
        f"- `app/database.py`: {data['database_lines']} líneas",
        f"- Rutas HTTP: {data['total_routes']}",
        f"- Tablas ORM: {data['orm_tables']}",
        "",
        "## Archivos con más rutas",
        "",
    ]
    for path, count in data["top_route_files"]:
        rows.append(f"- `{path}`: {count}")
    rows.extend(["", "## Hotspots de `main.py`", ""])
    for item in data["main_function_hotspots"]:
        rows.append(f"- `{item['name']}`: {item['lines']} líneas (L{item['start']}-L{item['end']})")
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit architectural concentration without changing product semantics.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--enforce", action="store_true", help="Fail if V1.5.5 architectural debt grows.")
    args = parser.parse_args()

    data = snapshot()
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else markdown(data), end="")

    if args.enforce:
        failures = regressions(data)
        if failures:
            print("\nArchitectural debt regression detected:")
            for failure in failures:
                print(f"- {failure}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
