from __future__ import annotations

import os
import subprocess
import sys
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Float, Integer, MetaData, String, Table, Column, create_engine, inspect, text
from sqlalchemy.sql.sqltypes import Numeric


REVISION_BEFORE = "20260824_0041"
REVISION_AFTER = "20260825_0042"
TARGETS: dict[str, dict[str, tuple[int, int]]] = {
    "service_plans": {"monthly_fee": (20, 2), "annual_fee": (20, 2)},
    "organization_subscriptions": {"custom_monthly_fee": (20, 6)},
    "billing_invoices": {
        "amount": (20, 2),
        "net_amount": (20, 2),
        "tax_rate_snapshot": (9, 4),
        "tax_amount": (20, 2),
        "total_amount": (20, 2),
    },
    "commercial_proposals": {
        "implementation_fee": (20, 2),
        "recurring_fee": (20, 2),
        "discount_amount": (20, 2),
        "tax_rate": (9, 4),
        "first_year_total": (20, 2),
    },
    "payment_transactions": {"amount": (20, 2)},
    "service_contracts": {"contract_value": (20, 2)},
    "renewal_opportunities": {"forecast_amount": (20, 2)},
}


def _require_isolated_execution() -> str:
    if os.getenv("V2607_MIGRATION_CONTRACT") != "1":
        raise SystemExit("Refusing destructive fixture without V2607_MIGRATION_CONTRACT=1")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    return database_url


def _fixture_metadata() -> MetaData:
    metadata = MetaData()
    Table(
        "service_plans", metadata,
        Column("id", Integer, primary_key=True),
        Column("monthly_fee", Float, nullable=False),
        Column("annual_fee", Float, nullable=False),
    )
    Table(
        "organization_subscriptions", metadata,
        Column("id", Integer, primary_key=True),
        Column("custom_monthly_fee", Float, nullable=True),
    )
    Table(
        "billing_invoices", metadata,
        Column("id", Integer, primary_key=True),
        Column("amount", Float, nullable=False),
        Column("net_amount", Float, nullable=True),
        Column("tax_rate_snapshot", Float, nullable=True),
        Column("tax_amount", Float, nullable=True),
        Column("total_amount", Float, nullable=True),
    )
    Table(
        "commercial_proposals", metadata,
        Column("id", Integer, primary_key=True),
        Column("implementation_fee", Float, nullable=False),
        Column("recurring_fee", Float, nullable=False),
        Column("discount_amount", Float, nullable=False),
        Column("tax_rate", Float, nullable=False),
        Column("first_year_total", Float, nullable=False),
        Column("acceptance_hash", String(64), nullable=False, default=""),
    )
    Table(
        "payment_transactions", metadata,
        Column("id", Integer, primary_key=True),
        Column("amount", Float, nullable=False),
    )
    Table(
        "service_contracts", metadata,
        Column("id", Integer, primary_key=True),
        Column("contract_value", Float, nullable=False),
        Column("signature_hash", String(64), nullable=False, default=""),
        Column("signature_payload", String, nullable=True),
    )
    Table(
        "renewal_opportunities", metadata,
        Column("id", Integer, primary_key=True),
        Column("forecast_amount", Float, nullable=False),
    )
    Table(
        "alembic_version", metadata,
        Column("version_num", String(32), primary_key=True),
    )
    return metadata


def _reset_fixture(engine: sa.Engine, metadata: MetaData) -> None:
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            for table_name in list(TARGETS) + ["alembic_version"]:
                connection.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
        else:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            metadata.drop_all(connection, checkfirst=True)
    metadata.create_all(engine)


def _seed_fixture(engine: sa.Engine, metadata: MetaData) -> None:
    with engine.begin() as connection:
        connection.execute(metadata.tables["service_plans"].insert(), {
            "id": 1,
            "monthly_fee": 0.1 + 0.2,
            "annual_fee": 100.006,
        })
        connection.execute(metadata.tables["organization_subscriptions"].insert(), {
            "id": 1,
            "custom_monthly_fee": 8.333333333,
        })
        connection.execute(metadata.tables["billing_invoices"].insert(), {
            "id": 1,
            "amount": 0.1 + 0.2,
            "net_amount": 100.006,
            "tax_rate_snapshot": 19.123456,
            "tax_amount": 19.124,
            "total_amount": 119.13,
        })
        connection.execute(metadata.tables["commercial_proposals"].insert(), {
            "id": 1,
            "implementation_fee": 100.006,
            "recurring_fee": 50.004,
            "discount_amount": 0.004,
            "tax_rate": 19.123456,
            "first_year_total": 150.006,
            "acceptance_hash": "a" * 64,
        })
        connection.execute(metadata.tables["payment_transactions"].insert(), {
            "id": 1,
            "amount": 119.129999999999995,
        })
        connection.execute(metadata.tables["service_contracts"].insert(), {
            "id": 1,
            "contract_value": 1234.506,
            "signature_hash": "b" * 64,
            "signature_payload": '{"snapshot":"preserve-bytes"}',
        })
        connection.execute(metadata.tables["renewal_opportunities"].insert(), {
            "id": 1,
            "forecast_amount": 999.994,
        })
        connection.execute(metadata.tables["alembic_version"].insert(), {
            "version_num": REVISION_BEFORE,
        })


def _assert_schema(engine: sa.Engine) -> None:
    inspector = inspect(engine)
    for table_name, targets in TARGETS.items():
        columns = {item["name"]: item["type"] for item in inspector.get_columns(table_name)}
        for column_name, (precision, scale) in targets.items():
            column_type = columns[column_name]
            assert isinstance(column_type, Numeric), (table_name, column_name, column_type)
            assert column_type.precision == precision, (table_name, column_name, column_type)
            assert column_type.scale == scale, (table_name, column_name, column_type)


def _assert_values(engine: sa.Engine) -> None:
    reflected = MetaData()
    reflected.reflect(engine, only=list(TARGETS))
    with engine.connect() as connection:
        plan = connection.execute(sa.select(reflected.tables["service_plans"])).mappings().one()
        subscription = connection.execute(sa.select(reflected.tables["organization_subscriptions"])).mappings().one()
        invoice = connection.execute(sa.select(reflected.tables["billing_invoices"])).mappings().one()
        proposal = connection.execute(sa.select(reflected.tables["commercial_proposals"])).mappings().one()
        payment = connection.execute(sa.select(reflected.tables["payment_transactions"])).mappings().one()
        contract = connection.execute(sa.select(reflected.tables["service_contracts"])).mappings().one()
        renewal = connection.execute(sa.select(reflected.tables["renewal_opportunities"])).mappings().one()

        assert plan["monthly_fee"] == Decimal("0.30")
        assert plan["annual_fee"] == Decimal("100.01")
        assert subscription["custom_monthly_fee"] == Decimal("8.333333")
        assert invoice["amount"] == Decimal("0.30")
        assert invoice["net_amount"] == Decimal("100.01")
        assert invoice["tax_rate_snapshot"] == Decimal("19.1235")
        assert proposal["implementation_fee"] == Decimal("100.01")
        assert proposal["tax_rate"] == Decimal("19.1235")
        assert payment["amount"] == Decimal("119.13")
        assert contract["contract_value"] == Decimal("1234.51")
        assert renewal["forecast_amount"] == Decimal("999.99")

        # 0042 changes numeric representation only: cryptographic evidence is bytes-stable.
        assert proposal["acceptance_hash"] == "a" * 64
        assert contract["signature_hash"] == "b" * 64
        assert contract["signature_payload"] == '{"snapshot":"preserve-bytes"}'

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision == REVISION_AFTER


def main() -> None:
    database_url = _require_isolated_execution()
    engine = create_engine(database_url)
    metadata = _fixture_metadata()
    _reset_fixture(engine, metadata)
    _seed_fixture(engine, metadata)

    env = os.environ.copy()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env=env,
    )

    engine.dispose()
    engine = create_engine(database_url)
    _assert_schema(engine)
    _assert_values(engine)
    print(f"V2.60.7 monetary migration contract PASS [{engine.dialect.name}]")


if __name__ == "__main__":
    main()
