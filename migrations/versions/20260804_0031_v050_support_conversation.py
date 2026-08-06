"""V0.50 conversaciones operativas y contexto de requerimientos.

Revision ID: 20260804_0031
Revises: 20260804_0030
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa

revision = "20260804_0031"
down_revision = "20260804_0030"
branch_labels = None
depends_on = None


def _column_names(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "support_tickets" in tables:
        existing = _column_names(inspector, "support_tickets")
        additions = [
            ("inventory_id", sa.Integer(), True),
            ("source_id", sa.Integer(), True),
            ("activity_data_id", sa.Integer(), True),
            ("public_reference", sa.String(length=40), False),
            ("request_type", sa.String(length=60), False),
            ("desired_outcome", sa.Text(), False),
            ("due_date", sa.Date(), True),
            ("response_due_at", sa.DateTime(), True),
            ("last_message_at", sa.DateTime(), True),
        ]
        with op.batch_alter_table("support_tickets") as batch:
            for name, column_type, nullable in additions:
                if name in existing:
                    continue
                kwargs = {"nullable": nullable}
                if name in {"public_reference", "desired_outcome"}:
                    kwargs["server_default"] = ""
                if name == "request_type":
                    kwargs["server_default"] = "Consulta"
                batch.add_column(sa.Column(name, column_type, **kwargs))
            if "inventory_id" not in existing:
                batch.create_foreign_key("fk_support_ticket_inventory", "inventories", ["inventory_id"], ["id"])
            if "source_id" not in existing:
                batch.create_foreign_key("fk_support_ticket_source", "emission_sources", ["source_id"], ["id"])
            if "activity_data_id" not in existing:
                batch.create_foreign_key("fk_support_ticket_activity", "activity_data", ["activity_data_id"], ["id"])
        refreshed = sa.inspect(bind)
        indexes = {index["name"] for index in refreshed.get_indexes("support_tickets")}
        for name, columns in (
            ("ix_support_tickets_inventory_id", ["inventory_id"]),
            ("ix_support_tickets_source_id", ["source_id"]),
            ("ix_support_tickets_activity_data_id", ["activity_data_id"]),
            ("ix_support_tickets_public_reference", ["public_reference"]),
            ("ix_support_tickets_response_due_at", ["response_due_at"]),
            ("ix_support_tickets_last_message_at", ["last_message_at"]),
        ):
            if name not in indexes:
                op.create_index(name, "support_tickets", columns)

    inspector = sa.inspect(bind)
    if "activity_factor_selections" in inspector.get_table_names():
        existing_factor_columns = _column_names(inspector, "activity_factor_selections")
        with op.batch_alter_table("activity_factor_selections") as batch:
            if "review_notes" not in existing_factor_columns:
                batch.add_column(sa.Column("review_notes", sa.Text(), nullable=False, server_default=""))
            if "decision_snapshot" not in existing_factor_columns:
                batch.add_column(sa.Column("decision_snapshot", sa.Text(), nullable=False, server_default="{}"))
            if "applied_at" not in existing_factor_columns:
                batch.add_column(sa.Column("applied_at", sa.DateTime(), nullable=True))

    inspector = sa.inspect(bind)
    if "support_messages" not in inspector.get_table_names():
        op.create_table(
            "support_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("support_tickets.id"), nullable=False),
            sa.Column("author_email", sa.String(length=180), nullable=False),
            sa.Column("author_role", sa.String(length=40), nullable=False, server_default="Cliente"),
            sa.Column("message_type", sa.String(length=50), nullable=False, server_default="Mensaje"),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("visible_to_client", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_support_messages_ticket_id", "support_messages", ["ticket_id"])
        op.create_index("ix_support_messages_created_at", "support_messages", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "support_messages" in inspector.get_table_names():
        op.drop_table("support_messages")
    if "activity_factor_selections" in inspector.get_table_names():
        existing_factor_columns = _column_names(inspector, "activity_factor_selections")
        with op.batch_alter_table("activity_factor_selections") as batch:
            for name in ("applied_at", "decision_snapshot", "review_notes"):
                if name in existing_factor_columns:
                    batch.drop_column(name)
    if "support_tickets" in inspector.get_table_names():
        existing = _column_names(inspector, "support_tickets")
        with op.batch_alter_table("support_tickets") as batch:
            for name in (
                "last_message_at", "response_due_at", "due_date", "desired_outcome", "request_type",
                "public_reference", "activity_data_id", "source_id", "inventory_id",
            ):
                if name in existing:
                    batch.drop_column(name)
