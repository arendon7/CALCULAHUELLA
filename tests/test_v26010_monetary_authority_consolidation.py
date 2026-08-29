from __future__ import annotations

import ast
from pathlib import Path

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateTable
from sqlalchemy.sql.sqltypes import Float

from app.db.monetary_types import ExactNumeric
from app.db.models import (
    BillingInvoice,
    CommercialProposal,
    CustomerSuccessProfile,
    OrganizationSubscription,
    PaymentTransaction,
    RenewalOpportunity,
    ServiceContract,
    ServicePlan,
    UsageCounter,
    ValueMilestone,
)


ROOT = Path(__file__).resolve().parents[1]
COMMERCIAL_SOURCE = ROOT / "app" / "db" / "models" / "commercial.py"
REVENUE_SOURCE = ROOT / "app" / "db" / "models" / "revenue.py"


def _class_assignments(path: Path) -> dict[str, dict[str, ast.AnnAssign]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result: dict[str, dict[str, ast.AnnAssign]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        fields: dict[str, ast.AnnAssign] = {}
        for child in node.body:
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                fields[child.target.id] = child
        result[node.name] = fields
    return result


def _mapped_factory(assignment: ast.AnnAssign) -> str | None:
    value = assignment.value
    if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name) or value.func.id != "mapped_column":
        return None
    if not value.args or not isinstance(value.args[0], ast.Call):
        return None
    factory = value.args[0].func
    return factory.id if isinstance(factory, ast.Name) else None


def test_v26010_economic_columns_are_declared_exactly_at_model_source() -> None:
    classes = _class_assignments(COMMERCIAL_SOURCE)
    expected = {
        "ServicePlan": {
            "monthly_fee": "money_type",
            "annual_fee": "money_type",
        },
        "OrganizationSubscription": {
            "custom_monthly_fee": "normalized_money_type",
        },
        "BillingInvoice": {
            "amount": "money_type",
            "net_amount": "money_type",
            "tax_rate_snapshot": "rate_type",
            "tax_amount": "money_type",
            "total_amount": "money_type",
        },
        "CommercialProposal": {
            "implementation_fee": "money_type",
            "recurring_fee": "money_type",
            "discount_amount": "money_type",
            "tax_rate": "rate_type",
            "first_year_total": "money_type",
        },
        "PaymentTransaction": {"amount": "money_type"},
        "ServiceContract": {"contract_value": "money_type"},
        "RenewalOpportunity": {"forecast_amount": "money_type"},
    }
    for class_name, fields in expected.items():
        declared = classes[class_name]
        for field_name, factory in fields.items():
            assert field_name in declared, (class_name, field_name)
            assert _mapped_factory(declared[field_name]) == factory, (class_name, field_name, factory)


def test_v26010_v2606_semantic_columns_are_declarative_not_runtime_injected() -> None:
    classes = _class_assignments(COMMERCIAL_SOURCE)
    assert {
        "charge_type",
        "amount_semantics",
        "net_amount",
        "tax_rate_snapshot",
        "tax_amount",
        "total_amount",
        "source_reference",
        "classification_note",
        "semantics_created_at",
    }.issubset(classes["BillingInvoice"])
    assert {
        "signature_version",
        "signature_payload",
        "signature_snapshot_created_at",
    }.issubset(classes["ServiceContract"])

    revenue_tree = ast.parse(REVENUE_SOURCE.read_text(encoding="utf-8"))
    for node in revenue_tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                assert not isinstance(target, ast.Attribute), ast.unparse(target)
    revenue_source = REVENUE_SOURCE.read_text(encoding="utf-8")
    assert "_set_exact_type" not in revenue_source
    assert "mapped_column(" not in revenue_source


def test_v26010_runtime_columns_use_shared_exact_type_authority() -> None:
    money_columns = {
        ServicePlan: ("monthly_fee", "annual_fee"),
        BillingInvoice: ("amount", "net_amount", "tax_amount", "total_amount"),
        CommercialProposal: (
            "implementation_fee",
            "recurring_fee",
            "discount_amount",
            "first_year_total",
        ),
        PaymentTransaction: ("amount",),
        ServiceContract: ("contract_value",),
        RenewalOpportunity: ("forecast_amount",),
    }
    for model, names in money_columns.items():
        for name in names:
            column_type = model.__table__.c[name].type
            assert isinstance(column_type, ExactNumeric), (model.__name__, name, column_type)
            assert (column_type.precision, column_type.scale) == (20, 2)

    normalized = OrganizationSubscription.__table__.c.custom_monthly_fee.type
    assert isinstance(normalized, ExactNumeric)
    assert (normalized.precision, normalized.scale) == (20, 6)

    for model, name in ((CommercialProposal, "tax_rate"), (BillingInvoice, "tax_rate_snapshot")):
        rate = model.__table__.c[name].type
        assert isinstance(rate, ExactNumeric)
        assert (rate.precision, rate.scale) == (9, 4)


def test_v26010_non_economic_float_scope_remains_unchanged() -> None:
    assert isinstance(UsageCounter.__table__.c.value.type, Float)
    assert isinstance(CustomerSuccessProfile.__table__.c.satisfaction_score.type, Float)
    assert isinstance(ValueMilestone.__table__.c.expected_value.type, Float)
    assert isinstance(ValueMilestone.__table__.c.realized_value.type, Float)


def test_v26010_create_table_ddl_is_numeric_before_revenue_policy_layer() -> None:
    for dialect in (sqlite.dialect(), postgresql.dialect()):
        plan_ddl = str(CreateTable(ServicePlan.__table__).compile(dialect=dialect)).upper()
        proposal_ddl = str(CreateTable(CommercialProposal.__table__).compile(dialect=dialect)).upper()
        invoice_ddl = str(CreateTable(BillingInvoice.__table__).compile(dialect=dialect)).upper()
        contract_ddl = str(CreateTable(ServiceContract.__table__).compile(dialect=dialect)).upper()

        assert "MONTHLY_FEE NUMERIC(20, 2)" in plan_ddl
        assert "CUSTOM_MONTHLY_FEE" not in plan_ddl
        assert "IMPLEMENTATION_FEE NUMERIC(20, 2)" in proposal_ddl
        assert "TAX_RATE NUMERIC(9, 4)" in proposal_ddl
        assert "NET_AMOUNT NUMERIC(20, 2)" in invoice_ddl
        assert "TAX_RATE_SNAPSHOT NUMERIC(9, 4)" in invoice_ddl
        assert "CONTRACT_VALUE NUMERIC(20, 2)" in contract_ddl
        assert "SIGNATURE_PAYLOAD" in contract_ddl
