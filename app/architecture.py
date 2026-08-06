from __future__ import annotations

from pathlib import Path
from typing import Any
import ast


DOMAIN_MODULES: tuple[dict[str, Any], ...] = (
    {
        "code": "organizations",
        "name": "Organización y sedes",
        "module": "app/organizations_web.py",
        "prefixes": ("/organizacion", "/sedes"),
    },
    {
        "code": "information",
        "name": "Datos, solicitudes y evidencias",
        "module": "app/information_web.py",
        "prefixes": ("/informacion", "/evidencias"),
    },
    {
        "code": "guided_capture",
        "name": "Captura guiada y plan sectorial",
        "module": "app/capture_web.py",
        "prefixes": ("/captura-guiada", "/api/captura-guiada"),
    },
    {
        "code": "review",
        "name": "Revisión y cierre del inventario",
        "module": "app/review_web.py",
        "prefixes": ("/control",),
    },
    {
        "code": "users",
        "name": "Usuarios y membresías",
        "module": "app/users_web.py",
        "prefixes": ("/usuarios",),
    },
    {
        "code": "inventories",
        "name": "Inventarios y fuentes",
        "module": "app/inventories_web.py",
        "prefixes": ("/inventarios", "/inventario", "/fuentes"),
    },
    {
        "code": "reports",
        "name": "Informes y artefactos",
        "module": "app/reports_web.py",
        "prefixes": ("/reportes",),
    },
    {
        "code": "delivery",
        "name": "Entrega profesional",
        "module": "app/delivery_web.py",
        "prefixes": ("/entrega-profesional", "/api/entrega-profesional"),
    },
    {
        "code": "service_operations",
        "name": "Operación del servicio",
        "module": "app/service_operations_web.py",
        "prefixes": ("/operacion-servicio", "/api/operacion-servicio"),
    },
    {
        "code": "operations",
        "name": "Operación y continuidad",
        "module": "app/operations_web.py",
        "prefixes": ("/operacion",),
    },
    {
        "code": "integrations",
        "name": "Integraciones y API de datos",
        "module": "app/integrations_web.py",
        "prefixes": ("/integraciones", "/api/v1"),
    },
    {
        "code": "product_intelligence",
        "name": "Perfil, diagnóstico y alcance",
        "module": "app/product_intelligence_web.py",
        "prefixes": ("/inteligencia-producto", "/diagnostico"),
    },
    {
        "code": "demo_environment",
        "name": "Entorno demostrativo certificado",
        "module": "app/demo_web.py",
        "prefixes": ("/entorno-demo",),
    },
    {
        "code": "land_removals",
        "name": "Tierras, remociones y carbono biogénico",
        "module": "app/land_removals_web.py",
        "prefixes": ("/metodologia/tierras-remociones", "/api/metodologia/tierras-remociones"),
    },
    {
        "code": "product_project_assurance",
        "name": "Producto, mitigación y aseguramiento",
        "module": "app/product_project_assurance_web.py",
        "prefixes": ("/huella-producto", "/proyectos-mitigacion", "/aseguramiento"),
    },
)


PERSISTENCE_MODEL_MODULES: tuple[str, ...] = (
    "app/db/models/core.py",
    "app/db/models/operations.py",
    "app/db/models/inventory.py",
    "app/db/models/supply_chain.py",
    "app/db/models/land.py",
    "app/db/models/product_project_assurance.py",
    "app/db/models/methodology.py",
    "app/db/models/commercial.py",
    "app/db/models/product_intelligence.py",
    "app/db/models/climate.py",
    "app/db/models/governance.py",
    "app/db/models/pilot.py",
)

PERSISTENCE_REPOSITORIES: tuple[str, ...] = (
    "app/repositories/organizations.py",
    "app/repositories/inventories.py",
    "app/repositories/reports.py",
    "app/repositories/operations.py",
    "app/repositories/product_intelligence.py",
)

PERSISTENCE_SERVICES: tuple[str, ...] = (
    "app/services/organizations.py",
    "app/services/inventories.py",
    "app/services/reports.py",
    "app/services/operations.py",
    "app/services/product_intelligence.py",
)


def persistence_architecture_summary(project_dir: Path) -> dict[str, Any]:
    database_path = project_dir / "app" / "database.py"
    model_modules: list[dict[str, Any]] = []
    model_class_count = 0
    for relative_path in PERSISTENCE_MODEL_MODULES:
        path = project_dir / relative_path
        class_count = 0
        lines = 0
        if path.exists():
            source = path.read_text(encoding="utf-8")
            lines = len(source.splitlines())
            class_count = sum(
                1 for node in ast.parse(source).body
                if isinstance(node, ast.ClassDef)
            )
        model_class_count += class_count
        model_modules.append({
            "module": relative_path,
            "exists": path.exists(),
            "lines": lines,
            "class_count": class_count,
        })

    def module_metrics(paths: tuple[str, ...]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for relative_path in paths:
            path = project_dir / relative_path
            result.append({
                "module": relative_path,
                "exists": path.exists(),
                "lines": len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0,
            })
        return result

    repositories = module_metrics(PERSISTENCE_REPOSITORIES)
    services = module_metrics(PERSISTENCE_SERVICES)
    database_lines = len(database_path.read_text(encoding="utf-8").splitlines()) if database_path.exists() else 0
    return {
        "database_lines": database_lines,
        "model_module_count": len(model_modules),
        "model_class_count": model_class_count,
        "model_modules": model_modules,
        "repositories": repositories,
        "services": services,
        "repository_count": len(repositories),
        "service_count": len(services),
        "split_ok": (
            database_lines < 2200
            and model_class_count >= 109
            and all(item["exists"] and item["class_count"] > 0 for item in model_modules)
            and all(item["exists"] for item in repositories + services)
        ),
    }


def _route_path(route: object) -> str:
    return str(getattr(route, "path", ""))


def _route_methods(route: object) -> tuple[str, ...]:
    methods = getattr(route, "methods", None) or ()
    return tuple(sorted(str(method) for method in methods))


def _endpoint_module(route: object) -> str:
    endpoint = getattr(route, "endpoint", None)
    return str(getattr(endpoint, "__module__", ""))


def domain_architecture_summary(app: object, project_dir: Path) -> dict[str, Any]:
    """Return auditable route ownership and controller-size metrics.

    The report is intentionally static and deterministic. It does not claim that
    every business service has been extracted; it only records the domains that
    have an explicit web module and verifies route parity at runtime.
    """
    route_objects = list(getattr(app, "routes", []))
    routes = [path for path in (_route_path(route) for route in route_objects) if path]
    signatures = [
        (path, method)
        for route in route_objects
        for path in [_route_path(route)]
        if path
        for method in (_route_methods(route) or ("",))
    ]
    duplicate_paths = sorted({
        f"{method} {path}".strip()
        for path, method in signatures
        if signatures.count((path, method)) > 1
    })
    domains: list[dict[str, Any]] = []
    owned_paths: set[str] = set()

    for item in DOMAIN_MODULES:
        expected_module = "app." + Path(str(item["module"])).stem
        domain_paths = sorted({
            _route_path(route)
            for route in route_objects
            if _route_path(route) and _endpoint_module(route) == expected_module
        })
        owned_paths.update(domain_paths)
        module_path = project_dir / str(item["module"])
        domains.append({
            **item,
            "route_count": len(domain_paths),
            "routes": domain_paths,
            "module_exists": module_path.exists(),
            "module_lines": len(module_path.read_text().splitlines()) if module_path.exists() else 0,
        })

    main_path = project_dir / "app" / "main.py"
    main_lines = len(main_path.read_text().splitlines()) if main_path.exists() else 0
    extracted_lines = sum(int(item["module_lines"]) for item in domains)
    persistence = persistence_architecture_summary(project_dir)
    return {
        "domains": domains,
        "domain_count": len(domains),
        "owned_route_count": len(owned_paths),
        "total_route_count": len(set(routes)),
        "main_lines": main_lines,
        "extracted_module_lines": extracted_lines,
        "duplicate_paths": duplicate_paths,
        "persistence": persistence,
        "route_parity_ok": not duplicate_paths and all(item["module_exists"] and item["route_count"] > 0 for item in domains),
        "architecture_split_ok": (
            not duplicate_paths
            and all(item["module_exists"] and item["route_count"] > 0 for item in domains)
            and persistence["split_ok"]
        ),
    }
