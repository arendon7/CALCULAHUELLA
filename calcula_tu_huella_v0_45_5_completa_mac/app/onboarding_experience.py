from __future__ import annotations

"""Presentation helpers for a guided, action-oriented customer onboarding."""

from typing import Any, Iterable


_STEP_META: dict[str, dict[str, str]] = {
    "ORG-01": {
        "href": "/organizacion",
        "action": "Completar organización",
        "outcome": "Ficha legal, sector, contacto y sedes listas para definir el inventario.",
        "why": "El cálculo necesita saber qué entidad, sedes y operación quedan dentro del límite organizacional.",
    },
    "USR-01": {
        "href": "/usuarios",
        "action": "Configurar equipo",
        "outcome": "Responsables de carga, revisión y aprobación con permisos claros.",
        "why": "La trazabilidad depende de saber quién aporta, revisa y aprueba cada dato.",
    },
    "MET-01": {
        "href": "/inventarios/{inventory_id}",
        "action": "Definir metodología",
        "outcome": "Periodo, estándar, GWP, límites y enfoque de consolidación documentados.",
        "why": "Antes de cargar datos deben aprobarse las reglas que determinan qué se calcula y cómo.",
    },
    "DAT-01": {
        "href": "/informacion",
        "action": "Cargar datos piloto",
        "outcome": "Primer conjunto de consumos y evidencias asociado a una fuente de emisión.",
        "why": "Una carga piloto permite validar unidades, responsables y soportes antes de escalar el levantamiento.",
    },
    "CAL-01": {
        "href": "/calculos",
        "action": "Revisar cálculo",
        "outcome": "Primer resultado reproducible con actividad, factor, gases y conversión a CO₂e.",
        "why": "La revisión temprana evita replicar errores de unidad, factor o fórmula en todo el inventario.",
    },
    "REP-01": {
        "href": "/reportes",
        "action": "Generar primer informe",
        "outcome": "Informe ejecutivo inicial para validar lectura, alcance y decisiones siguientes.",
        "why": "El primer entregable confirma que los resultados pueden comunicarse de forma clara y trazable.",
    },
}

_STATUS_ORDER = {"Bloqueado": 0, "En progreso": 1, "Pendiente": 2, "Completado": 3}


def _resolve_href(template: str, inventory_id: int | None) -> str:
    return template.format(inventory_id=inventory_id or "")


def onboarding_summary(rows: Iterable[Any], *, inventory_id: int | None = None) -> dict[str, Any]:
    """Build a stable UI view-model without changing onboarding persistence."""
    raw_rows = list(rows)
    total = len(raw_rows)
    completed = sum(1 for row in raw_rows if row.status == "Completado")
    blocked = sum(1 for row in raw_rows if row.status == "Bloqueado")
    in_progress = sum(1 for row in raw_rows if row.status == "En progreso")
    score = round(completed / max(total, 1) * 100)

    steps: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows, start=1):
        meta = _STEP_META.get(row.code, {})
        steps.append(
            {
                "row": row,
                "number": index,
                "href": _resolve_href(meta.get("href", "/dashboard"), inventory_id),
                "action": meta.get("action", "Abrir actividad"),
                "outcome": meta.get("outcome", row.description),
                "why": meta.get("why", "Esta actividad hace parte de la puesta en marcha del inventario."),
                "done": row.status == "Completado",
                "blocked": row.status == "Bloqueado",
                "current": False,
            }
        )

    pending_steps = [step for step in steps if not step["done"]]
    next_step = min(
        pending_steps,
        key=lambda step: (_STATUS_ORDER.get(step["row"].status, 9), step["row"].display_order),
        default=None,
    )
    if next_step:
        next_step["current"] = True

    if score == 100:
        state = "Lista para operar"
        headline = "La puesta en marcha está completa"
        message = "El equipo ya puede operar el inventario desde el recorrido guiado y controlar cada cierre con evidencia."
    elif blocked:
        state = "Requiere desbloqueo"
        headline = "Hay una decisión que impide continuar"
        message = "Resuelve el bloqueo señalado y retoma la siguiente actividad prioritaria."
    elif in_progress:
        state = "Implementación en curso"
        headline = "Continúa desde el punto exacto"
        message = "Completa la actividad prioritaria y la plataforma actualizará automáticamente el avance general."
    else:
        state = "Lista para comenzar"
        headline = "Configura la base del primer inventario"
        message = "Avanza en orden para evitar cargas de información sin responsables, límites o reglas aprobadas."

    return {
        "score": score,
        "completed": completed,
        "total": total,
        "blocked": blocked,
        "in_progress": in_progress,
        "remaining": max(total - completed, 0),
        "steps": steps,
        "next_step": next_step,
        "state": state,
        "headline": headline,
        "message": message,
        "ready": total > 0 and completed == total,
    }
