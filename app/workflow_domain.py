from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class StageDefinition:
    code: str
    label: str
    objective: str
    exit_condition: str


@dataclass(frozen=True, slots=True)
class StatusDefinition:
    code: str
    label: str
    description: str
    terminal: bool = False


CANONICAL_STAGES: tuple[StageDefinition, ...] = (
    StageDefinition(
        "diagnose",
        "Diagnosticar",
        "Entender la organización, su contexto, las decisiones esperadas y la información disponible.",
        "Existe un diagnóstico trazable y una ruta de implementación acordada.",
    ),
    StageDefinition(
        "configure",
        "Configurar",
        "Definir límites, periodo, sedes, fuentes, responsables, criterios y metodología aplicable.",
        "El inventario está configurado y puede iniciar la recopilación controlada.",
    ),
    StageDefinition(
        "collect",
        "Recopilar",
        "Solicitar, recibir y relacionar datos de actividad con sus soportes y responsables.",
        "Los datos y evidencias requeridos fueron entregados o existe una excepción documentada.",
    ),
    StageDefinition(
        "validate_close",
        "Validar y cerrar periodos",
        "Verificar integridad, calidad, duplicados, unidades, soportes y cierre mensual.",
        "El periodo fue validado, cerrado o devuelto con hallazgos accionables.",
    ),
    StageDefinition(
        "calculate",
        "Calcular",
        "Aplicar factores, conversiones, gases, potenciales de calentamiento global y reglas metodológicas.",
        "Los resultados son reproducibles y sus insumos metodológicos están identificados.",
    ),
    StageDefinition(
        "review_approve",
        "Revisar y aprobar",
        "Resolver observaciones, segregar funciones y emitir decisiones de revisión y aprobación.",
        "El inventario fue aprobado internamente o devuelto con responsables y plazo de corrección.",
    ),
    StageDefinition(
        "report_publish",
        "Reportar y controlar publicación",
        "Generar artefactos, controlar versiones, definir nivel de uso y registrar la publicación autorizada.",
        "Existe una versión controlada, descargable y vinculada con su decisión de aprobación.",
    ),
    StageDefinition(
        "reduce_continue",
        "Reducir y continuar",
        "Convertir resultados en acciones, seguimiento, metas y preparación del siguiente periodo.",
        "Las acciones tienen responsables y el próximo ciclo quedó preparado.",
    ),
)

STAGE_BY_CODE = {stage.code: stage for stage in CANONICAL_STAGES}
STAGE_INDEX = {stage.code: index for index, stage in enumerate(CANONICAL_STAGES, start=1)}


WORK_ITEM_TYPES: dict[str, str] = {
    "data_request": "Solicitud de dato",
    "evidence_request": "Solicitud de evidencia",
    "data_correction": "Corrección de dato",
    "quality_finding": "Hallazgo de calidad",
    "monthly_close": "Cierre mensual",
    "factor_review": "Revisión de factor",
    "inventory_review": "Revisión de inventario",
    "report_approval": "Aprobación de informe",
    "reduction_action": "Acción de reducción",
    "support_follow_up": "Seguimiento de soporte",
    "integration_exception": "Excepción de integración",
    "next_period_setup": "Preparación del siguiente periodo",
}

DEFAULT_STAGE_BY_WORK_TYPE: dict[str, str] = {
    "data_request": "collect",
    "evidence_request": "collect",
    "data_correction": "validate_close",
    "quality_finding": "validate_close",
    "monthly_close": "validate_close",
    "factor_review": "calculate",
    "inventory_review": "review_approve",
    "report_approval": "report_publish",
    "reduction_action": "reduce_continue",
    "support_follow_up": "collect",
    "integration_exception": "collect",
    "next_period_setup": "reduce_continue",
}

PRIORITIES: tuple[str, ...] = ("low", "normal", "high", "critical")
PRIORITY_LABELS = {
    "low": "Baja",
    "normal": "Normal",
    "high": "Alta",
    "critical": "Crítica",
}


STATUSES: tuple[StatusDefinition, ...] = (
    StatusDefinition("draft", "Borrador", "La tarea todavía no ha sido asignada."),
    StatusDefinition("assigned", "Asignada", "Existe una persona, área o rol responsable."),
    StatusDefinition("accepted_by_assignee", "Aceptada por responsable", "El responsable confirmó que atenderá la tarea."),
    StatusDefinition("in_progress", "En preparación", "La entrega está siendo preparada."),
    StatusDefinition("blocked", "Bloqueada", "Existe un impedimento explícito que requiere resolución."),
    StatusDefinition("submitted", "Entregada", "El responsable entregó el resultado para control."),
    StatusDefinition("validating", "En validación", "Se verifica integridad, formato y criterios de aceptación."),
    StatusDefinition("under_review", "En revisión", "Un revisor evalúa suficiencia técnica y metodológica."),
    StatusDefinition("accepted_by_reviewer", "Aceptada por revisor", "La entrega fue aceptada y puede cerrarse."),
    StatusDefinition("returned", "Devuelta", "La entrega requiere correcciones concretas."),
    StatusDefinition("closed", "Cerrada", "La tarea terminó con decisión y trazabilidad completas.", terminal=True),
    StatusDefinition("cancelled", "Cancelada", "La tarea dejó de ser aplicable con motivo documentado.", terminal=True),
)

STATUS_BY_CODE = {status.code: status for status in STATUSES}


TRANSITIONS: dict[str, dict[str, str]] = {
    "draft": {"assign": "assigned", "cancel": "cancelled"},
    "assigned": {"accept_assignment": "accepted_by_assignee", "cancel": "cancelled"},
    "accepted_by_assignee": {"start": "in_progress", "cancel": "cancelled"},
    "in_progress": {"block": "blocked", "submit": "submitted", "cancel": "cancelled"},
    "blocked": {"resume": "in_progress", "cancel": "cancelled"},
    "submitted": {"start_validation": "validating", "return_for_correction": "returned"},
    "validating": {"send_to_review": "under_review", "return_for_correction": "returned"},
    "under_review": {"accept_delivery": "accepted_by_reviewer", "return_for_correction": "returned"},
    "accepted_by_reviewer": {"close": "closed", "return_for_correction": "returned"},
    "returned": {"restart_correction": "in_progress", "cancel": "cancelled"},
    "closed": {"reopen": "returned"},
    "cancelled": {},
}


ROLE_WORKFLOW_CAPABILITIES: dict[str, frozenset[str]] = {
    "Administrador": frozenset({
        "manage_workflow", "execute_workflow", "validate_workflow",
        "review_workflow", "approve_workflow", "audit_workflow",
    }),
    "Consultor": frozenset({
        "manage_workflow", "execute_workflow", "validate_workflow", "review_workflow",
    }),
    "Cliente": frozenset({"execute_workflow"}),
    "Revisor": frozenset({"validate_workflow", "review_workflow", "approve_workflow"}),
    "Verificador": frozenset({"audit_workflow"}),
}

ACTION_CAPABILITIES: dict[str, frozenset[str]] = {
    "assign": frozenset({"manage_workflow"}),
    "accept_assignment": frozenset({"execute_workflow"}),
    "start": frozenset({"execute_workflow"}),
    "block": frozenset({"execute_workflow"}),
    "resume": frozenset({"execute_workflow"}),
    "submit": frozenset({"execute_workflow"}),
    "start_validation": frozenset({"validate_workflow"}),
    "send_to_review": frozenset({"validate_workflow"}),
    "accept_delivery": frozenset({"review_workflow"}),
    "return_for_correction": frozenset({"validate_workflow", "review_workflow", "approve_workflow"}),
    "restart_correction": frozenset({"execute_workflow"}),
    "close": frozenset({"approve_workflow"}),
    "reopen": frozenset({"approve_workflow"}),
    "cancel": frozenset({"manage_workflow", "approve_workflow"}),
}

ACTIONS_REQUIRING_REASON = frozenset({"block", "return_for_correction", "reopen", "cancel"})


class WorkflowRuleError(ValueError):
    """Raised when a canonical workflow rule is not satisfied."""


def stage_number(stage_code: str) -> int:
    try:
        return STAGE_INDEX[stage_code]
    except KeyError as exc:
        raise WorkflowRuleError(f"Etapa canónica desconocida: {stage_code}") from exc


def next_stage(stage_code: str) -> StageDefinition | None:
    index = stage_number(stage_code)
    if index >= len(CANONICAL_STAGES):
        return None
    return CANONICAL_STAGES[index]


def capabilities_for_role(role: str) -> frozenset[str]:
    return ROLE_WORKFLOW_CAPABILITIES.get(role, frozenset())


def allowed_actions(status_code: str, actor_capabilities: Iterable[str]) -> tuple[str, ...]:
    if status_code not in STATUS_BY_CODE:
        raise WorkflowRuleError(f"Estado canónico desconocido: {status_code}")
    actor = set(actor_capabilities)
    return tuple(
        action
        for action in TRANSITIONS[status_code]
        if actor & set(ACTION_CAPABILITIES[action])
    )


def validate_transition(
    current_status: str,
    action: str,
    actor_capabilities: Iterable[str],
    *,
    reason: str = "",
    assignee_present: bool = False,
    acceptance_criteria_present: bool = False,
) -> str:
    """Validate a transition and return its target status.

    This function is intentionally pure. Persistence, audit events and notifications
    belong to the application service introduced in the next implementation slice.
    """
    if current_status not in STATUS_BY_CODE:
        raise WorkflowRuleError(f"Estado canónico desconocido: {current_status}")
    if action not in ACTION_CAPABILITIES:
        raise WorkflowRuleError(f"Acción canónica desconocida: {action}")
    target = TRANSITIONS[current_status].get(action)
    if not target:
        raise WorkflowRuleError(
            f"La acción {action} no está permitida desde {STATUS_BY_CODE[current_status].label}."
        )
    actor = set(actor_capabilities)
    required = set(ACTION_CAPABILITIES[action])
    if not actor & required:
        raise WorkflowRuleError("El rol activo no tiene capacidad para ejecutar esta transición.")
    if action == "assign" and not assignee_present:
        raise WorkflowRuleError("La asignación requiere una persona, área o rol responsable.")
    if action == "assign" and not acceptance_criteria_present:
        raise WorkflowRuleError("La asignación requiere criterios de aceptación verificables.")
    if action in ACTIONS_REQUIRING_REASON and not reason.strip():
        raise WorkflowRuleError("Esta transición requiere un motivo documentado.")
    return target


def validate_catalogue() -> None:
    """Fail fast if the canonical catalogue contains an internal inconsistency."""
    if len(CANONICAL_STAGES) != 8:
        raise WorkflowRuleError("El proceso canónico debe conservar exactamente ocho etapas.")
    if len(STAGE_BY_CODE) != len(CANONICAL_STAGES):
        raise WorkflowRuleError("Hay códigos de etapa duplicados.")
    if len(STATUS_BY_CODE) != len(STATUSES):
        raise WorkflowRuleError("Hay códigos de estado duplicados.")
    for source, actions in TRANSITIONS.items():
        if source not in STATUS_BY_CODE:
            raise WorkflowRuleError(f"La matriz referencia un estado de origen inexistente: {source}")
        for action, target in actions.items():
            if action not in ACTION_CAPABILITIES:
                raise WorkflowRuleError(f"La matriz referencia una acción sin política: {action}")
            if target not in STATUS_BY_CODE:
                raise WorkflowRuleError(f"La matriz referencia un estado destino inexistente: {target}")
    for work_type, stage_code in DEFAULT_STAGE_BY_WORK_TYPE.items():
        if work_type not in WORK_ITEM_TYPES or stage_code not in STAGE_BY_CODE:
            raise WorkflowRuleError(f"Asignación tipo-etapa inválida: {work_type} -> {stage_code}")


validate_catalogue()
