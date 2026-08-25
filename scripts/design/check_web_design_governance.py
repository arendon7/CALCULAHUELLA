#!/usr/bin/env python3
"""Gate determinista del sistema operativo de diseño web de Calcula tu Huella."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "design" / "WEB_DESIGN_SKILL_REGISTRY.json"
SKILL = ROOT / ".agents" / "skills" / "cth-web-design" / "SKILL.md"
OPERATING_SYSTEM = ROOT / "docs" / "design" / "WEB_DESIGN_OPERATING_SYSTEM_V2_1.md"

REQUIRED_SOURCES = {
    "emil-design-engineering",
    "impeccable",
    "taste-skill",
    "openai-frontend-skill",
    "vercel-web-design-guidelines",
}
REQUIRED_ROUTING = {"public_marketing", "product_ui", "motion", "content", "final_qa"}
REQUIRED_GATES = {
    "domain_truth_lock",
    "brand_truth_lock",
    "information_architecture",
    "content_quality",
    "accessibility",
    "responsive",
    "motion",
    "browser_e2e",
    "visual_evidence",
    "performance",
    "human_approval",
}
EXPECTED_BRAND = {
    "decision_version": "1.4.2",
    "logo_primary_sha256": "04a9b2557c1aff819eef52364dbe88677044299a6c868a7318703fdccffa638e",
    "symbol_sha256": "c43e33c89860aac5d7f582009b7d53e7902aa7704c9484fefcb1e2a2f99ce3e8",
    "redraw_allowed": False,
}


def fail(errors: list[str]) -> int:
    for error in errors:
        print(f"DESIGN GOVERNANCE ERROR: {error}", file=sys.stderr)
    return 1


def main() -> int:
    errors: list[str] = []
    for path in (REGISTRY, SKILL, OPERATING_SYSTEM):
        if not path.is_file():
            errors.append(f"falta {path.relative_to(ROOT)}")
    if errors:
        return fail(errors)

    try:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return fail([f"registry inválido: {exc}"])

    if registry.get("schema") != "cth-web-design-skill-registry-1.0":
        errors.append("schema de registry inesperado")
    if registry.get("upstream_policy", {}).get("automatic_updates") is not False:
        errors.append("los skills externos no pueden autoactualizarse")

    sources = registry.get("sources")
    if not isinstance(sources, list):
        errors.append("sources debe ser una lista")
        sources = []
    source_ids = {item.get("id") for item in sources if isinstance(item, dict)}
    missing_sources = REQUIRED_SOURCES - source_ids
    if missing_sources:
        errors.append(f"faltan fuentes: {sorted(missing_sources)}")
    for item in sources:
        if not isinstance(item, dict):
            errors.append("source inválida")
            continue
        commit = item.get("reviewed_commit", "")
        if not re.fullmatch(r"[0-9a-f]{40}", str(commit)):
            errors.append(f"commit no fijado para {item.get('id', '<sin-id>')}")

    routing = registry.get("routing")
    if not isinstance(routing, dict):
        errors.append("routing debe ser un objeto")
        routing = {}
    missing_routing = REQUIRED_ROUTING - set(routing)
    if missing_routing:
        errors.append(f"faltan perfiles de routing: {sorted(missing_routing)}")

    product = routing.get("product_ui", {})
    product_primary = set(product.get("primary", [])) if isinstance(product, dict) else set()
    product_restricted = set(product.get("restricted", [])) if isinstance(product, dict) else set()
    if "design-taste-frontend" in product_primary:
        errors.append("Taste no puede ser primario en product_ui")
    if "design-taste-frontend" not in product_restricted:
        errors.append("product_ui debe restringir Taste como controlador primario")

    gates = set(registry.get("required_gates", []))
    missing_gates = REQUIRED_GATES - gates
    if missing_gates:
        errors.append(f"faltan gates: {sorted(missing_gates)}")

    locks = registry.get("locks", {})
    if not isinstance(locks, dict):
        errors.append("locks debe ser un objeto")
        locks = {}
    domain_lock = str(locks.get("domain_truth_lock", "")).lower()
    for term in ("gwp", "fórmulas", "metodología"):
        if term not in domain_lock:
            errors.append(f"domain truth lock no protege {term}")
    if locks.get("brand_truth_lock") != EXPECTED_BRAND:
        errors.append("brand truth lock no coincide con V1.4.2")
    if not locks.get("functional_truth_lock"):
        errors.append("falta functional truth lock")

    skill_text = SKILL.read_text(encoding="utf-8")
    if "Product Approved != Production Approved" not in skill_text:
        errors.append("el skill no conserva la separación Product/Production Approved")
    if "make brand-require-canonical" not in skill_text:
        errors.append("el skill no exige el gate canónico de marca")

    if errors:
        return fail(errors)

    print(
        "WEB DESIGN GOVERNANCE PASS · "
        f"{len(source_ids)} fuentes fijadas · {len(routing)} perfiles · {len(gates)} gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
