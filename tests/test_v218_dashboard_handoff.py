from __future__ import annotations

from app.dashboard_web import resolve_dashboard_action


def _delivery(activity_status: str, base_action: dict | None = None) -> dict:
    return {
        "next_action": base_action,
        "gates": [
            {
                "code": "activity",
                "status": activity_status,
            }
        ],
    }


def test_v218_client_with_open_request_stays_on_information_work() -> None:
    action = resolve_dashboard_action(
        "Cliente",
        [object()],
        _delivery(
            "Listo",
            {
                "code": "calculation",
                "name": "Revisar cálculo",
                "href": "/calculos",
            },
        ),
    )

    assert action is not None
    assert action["name"] == "Atender solicitudes de información"
    assert action["href"] == "/informacion#solicitudes"
    assert action["owner"] == "Responsable de información"


def test_v218_client_with_incomplete_activity_data_stays_on_capture() -> None:
    action = resolve_dashboard_action(
        "Cliente",
        [],
        _delivery(
            "En progreso",
            {
                "code": "calculation",
                "name": "Revisar cálculo",
                "href": "/calculos",
            },
        ),
    )

    assert action is not None
    assert action["name"] == "Completar datos y evidencias"
    assert action["href"] == "/captura-guiada"
    assert action["action"] == "Continuar captura"


def test_v218_client_keeps_canonical_evidence_work_after_activity_is_ready() -> None:
    base_action = {
        "code": "evidence",
        "name": "Vincular soportes",
        "detail": "Falta cobertura documental.",
        "owner": "Responsables de información",
        "acceptance": "Cobertura documental mínima de 80%.",
        "href": "/captura-guiada",
        "action": "Vincular soportes",
    }

    action = resolve_dashboard_action("Cliente", [], _delivery("Listo", base_action))

    assert action == base_action


def test_v218_client_gets_explicit_handoff_when_next_gate_belongs_to_technical_role() -> None:
    base_action = {
        "code": "review",
        "name": "Resolver revisión metodológica",
        "detail": "La captura ya terminó; corresponde continuar el control técnico.",
        "owner": "Revisor metodológico",
        "acceptance": "Observaciones críticas cerradas.",
        "href": "/control",
        "action": "Abrir control",
    }

    action = resolve_dashboard_action("Cliente", [], _delivery("Listo", base_action))

    assert action is not None
    assert action["code"] == "handoff"
    assert action["name"] == "Datos entregados · relevo en curso"
    assert "Resolver revisión metodológica" in action["detail"]
    assert "revisor metodológico" in action["detail"]
    assert action["owner"] == "Revisor metodológico"
    assert action["href"] == "/recorrido-inventario"
    assert action["action"] == "Ver estado del proceso"
    assert action["handoff"] is True


def test_v218_client_without_pending_gate_has_no_forced_capture_or_handoff() -> None:
    action = resolve_dashboard_action("Cliente", [], _delivery("Listo", None))

    assert action is None


def test_v218_non_client_always_keeps_canonical_action() -> None:
    base_action = {
        "code": "calculation",
        "name": "Completar factores",
        "href": "/calculos",
    }

    action = resolve_dashboard_action("Consultor", [object()], _delivery("Bloqueado", base_action))

    assert action == base_action
