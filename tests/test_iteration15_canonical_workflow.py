from __future__ import annotations

import pytest

from app.access_control import ROLE_CAPABILITIES
from app.db.models.workflow import WorkItem, WorkItemDependency, WorkItemEvent, WorkItemLink
from app.workflow_domain import (
    ACTION_CAPABILITIES,
    CANONICAL_STAGES,
    DEFAULT_STAGE_BY_WORK_TYPE,
    ROLE_WORKFLOW_CAPABILITIES,
    STAGE_BY_CODE,
    STATUS_BY_CODE,
    TRANSITIONS,
    WORK_ITEM_TYPES,
    WorkflowRuleError,
    allowed_actions,
    capabilities_for_role,
    next_stage,
    validate_catalogue,
    validate_transition,
)


def test_canonical_process_has_exactly_eight_ordered_stages():
    validate_catalogue()
    assert [stage.code for stage in CANONICAL_STAGES] == [
        "diagnose",
        "configure",
        "collect",
        "validate_close",
        "calculate",
        "review_approve",
        "report_publish",
        "reduce_continue",
    ]
    assert next_stage("diagnose").code == "configure"
    assert next_stage("reduce_continue") is None


def test_every_work_type_has_a_valid_default_stage():
    assert set(DEFAULT_STAGE_BY_WORK_TYPE) == set(WORK_ITEM_TYPES)
    assert all(stage_code in STAGE_BY_CODE for stage_code in DEFAULT_STAGE_BY_WORK_TYPE.values())


def test_transition_matrix_only_references_declared_states_and_actions():
    for source_status, actions in TRANSITIONS.items():
        assert source_status in STATUS_BY_CODE
        for action, target_status in actions.items():
            assert action in ACTION_CAPABILITIES
            assert target_status in STATUS_BY_CODE


def test_assignment_requires_responsible_and_acceptance_criteria():
    capabilities = capabilities_for_role("Consultor")
    with pytest.raises(WorkflowRuleError, match="responsable"):
        validate_transition(
            "draft",
            "assign",
            capabilities,
            assignee_present=False,
            acceptance_criteria_present=True,
        )
    with pytest.raises(WorkflowRuleError, match="criterios de aceptación"):
        validate_transition(
            "draft",
            "assign",
            capabilities,
            assignee_present=True,
            acceptance_criteria_present=False,
        )
    assert validate_transition(
        "draft",
        "assign",
        capabilities,
        assignee_present=True,
        acceptance_criteria_present=True,
    ) == "assigned"


@pytest.mark.parametrize("action", ["block", "return_for_correction", "cancel", "reopen"])
def test_sensitive_transitions_require_a_documented_reason(action):
    source_by_action = {
        "block": "in_progress",
        "return_for_correction": "under_review",
        "cancel": "assigned",
        "reopen": "closed",
    }
    role_by_action = {
        "block": "Cliente",
        "return_for_correction": "Revisor",
        "cancel": "Administrador",
        "reopen": "Revisor",
    }
    with pytest.raises(WorkflowRuleError, match="motivo documentado"):
        validate_transition(
            source_by_action[action],
            action,
            capabilities_for_role(role_by_action[action]),
        )


def test_client_can_execute_but_cannot_review_or_close():
    client_capabilities = capabilities_for_role("Cliente")
    assert "accept_assignment" in allowed_actions("assigned", client_capabilities)
    assert "accept_delivery" not in allowed_actions("under_review", client_capabilities)
    assert "close" not in allowed_actions("accepted_by_reviewer", client_capabilities)


def test_reviewer_can_accept_close_and_reopen_with_reason():
    capabilities = capabilities_for_role("Revisor")
    assert validate_transition("under_review", "accept_delivery", capabilities) == "accepted_by_reviewer"
    assert validate_transition("accepted_by_reviewer", "close", capabilities) == "closed"
    assert validate_transition("closed", "reopen", capabilities, reason="Apareció nueva evidencia.") == "returned"


def test_workflow_capabilities_are_exposed_by_central_access_control():
    for role, capabilities in ROLE_WORKFLOW_CAPABILITIES.items():
        assert capabilities <= ROLE_CAPABILITIES[role]


def test_work_item_models_expose_traceability_and_dependency_tables():
    assert WorkItem.__tablename__ == "work_items"
    assert WorkItemEvent.__tablename__ == "work_item_events"
    assert WorkItemLink.__tablename__ == "work_item_links"
    assert WorkItemDependency.__tablename__ == "work_item_dependencies"

    columns = set(WorkItem.__table__.columns.keys())
    assert {
        "organization_id",
        "inventory_id",
        "stage_code",
        "work_type",
        "status_code",
        "requester_email",
        "assignee_email",
        "due_date",
        "acceptance_criteria",
        "next_action",
        "source_entity_type",
        "source_entity_id",
        "created_at",
        "submitted_at",
        "reviewed_at",
        "approved_at",
        "closed_at",
        "version",
    } <= columns
