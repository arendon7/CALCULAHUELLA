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
                "name": "Revisar cálculo",
                "href": "/calculos",
            },
        ),
    )

    assert action is not None
    assert action["name"] == "Completar datos y evidencias"
    assert action["href"] == "/captura-guiada"
    assert action["action"] == "Continuar captura"


def test_v218_client_hands_off_to_canonical_action_when_activity_gate_is_ready() -> None:
    base_action = {
        "name": "Resolver revisión metodológica",
        "detail": "La captura ya terminó; corresponde continuar el control técnico.",
        "owner": "Revisor metodológico",
        "acceptance": "Observaciones críticas cerradas.",
        "href": "/control",
        "action": "Abrir control",
    }

    action = resolve_dashboard_action("Cliente", [], _delivery("Listo", base_action))

    assert action == base_action
    assert action["href"] != "/captura-guiada"


def test_v218_non_client_always_keeps_canonical_action() -> None:
    base_action = {
        "name": "Completar factores",
        "href": "/calculos",
    }

    action = resolve_dashboard_action("Consultor", [object()], _delivery("Bloqueado", base_action))

    assert action == base_action
