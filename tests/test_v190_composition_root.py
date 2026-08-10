from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
EXPECTED_SYSTEM_ROUTES = {
    ("GET", "/modulos"),
    ("GET", "/api/health"),
    ("GET", "/api/ready"),
}


def _main_http_routes() -> set[tuple[str, str]]:
    source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    routes: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if not isinstance(decorator.func.value, ast.Name) or decorator.func.value.id != "app":
                continue
            method = decorator.func.attr.lower()
            if method not in HTTP_METHODS or not decorator.args:
                continue
            arg = decorator.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                routes.add((method.upper(), arg.value))
    return routes


def test_v190_main_is_composition_root_with_only_system_http_routes():
    assert _main_http_routes() == EXPECTED_SYSTEM_ROUTES


def test_v190_dead_lead_complexity_helper_is_absent():
    main_source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert "_lead_complexity" not in main_source
