"""Reconciliar work items para bases históricas y bases V2.0 nuevas.

Revision ID: 20260812_0040
Revises: 20260810_0039
Create Date: 2026-08-12

Las bases creadas desde la rama V2.0 ya reciben estas tablas en 20260806_0037.
La base PostgreSQL histórica, en cambio, llegó a 20260806_0038 por una cadena
anterior donde 0037 ampliaba password_hash y por tanto no creó work_items.
Este upgrade es deliberadamente idempotente: crea únicamente lo que falte.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260812_0040"
down_revision = "20260810_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "work_items" not in tables:
        op.create_table(
            "work_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=True),
            sa.Column("stage_code", sa.String(40), nullable=False, server_default="collect"),
            sa.Column("work_type", sa.String(60), nullable=False, server_default="data_request"),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status_code", sa.String(40), nullable=False, server_default="draft"),
            sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
            sa.Column("requester_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("requester_email", sa.String(180), nullable=False, server_default=""),
            sa.Column("assignee_user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=True),
            sa.Column("assignee_email", sa.String(180), nullable=False, server_default=""),
            sa.Column("assignee_role", sa.String(60), nullable=False, server_default=""),
            sa.Column("assignee_area", sa.String(120), nullable=False, server_default=""),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("acceptance_criteria", sa.Text(), nullable=False, server_default=""),
            sa.Column("next_action", sa.Text(), nullable=False, server_default=""),
            sa.Column("blocking_reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("source_entity_type", sa.String(80), nullable=False, server_default=""),
            sa.Column("source_entity_id", sa.Integer(), nullable=True),
            sa.Column("source_route", sa.String(260), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(180), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("accepted_at", sa.DateTime(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("ix_work_items_organization_id", "work_items", ["organization_id"])
        op.create_index("ix_work_items_inventory_id", "work_items", ["inventory_id"])
        op.create_index("ix_work_items_stage_code", "work_items", ["stage_code"])
        op.create_index("ix_work_items_work_type", "work_items", ["work_type"])
        op.create_index("ix_work_items_status_code", "work_items", ["status_code"])
        op.create_index("ix_work_items_priority", "work_items", ["priority"])
        op.create_index("ix_work_items_assignee_email", "work_items", ["assignee_email"])
        op.create_index("ix_work_items_due_date", "work_items", ["due_date"])

    tables = set(inspect(bind).get_table_names())
    if "work_item_events" not in tables:
        op.create_table(
            "work_item_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("work_items.id"), nullable=False),
            sa.Column("event_code", sa.String(60), nullable=False),
            sa.Column("from_status_code", sa.String(40), nullable=False, server_default=""),
            sa.Column("to_status_code", sa.String(40), nullable=False, server_default=""),
            sa.Column("actor_email", sa.String(180), nullable=False, server_default=""),
            sa.Column("actor_role", sa.String(60), nullable=False, server_default=""),
            sa.Column("comment", sa.Text(), nullable=False, server_default=""),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_work_item_events_work_item_id", "work_item_events", ["work_item_id"])
        op.create_index("ix_work_item_events_event_code", "work_item_events", ["event_code"])
        op.create_index("ix_work_item_events_created_at", "work_item_events", ["created_at"])

    tables = set(inspect(bind).get_table_names())
    if "work_item_links" not in tables:
        op.create_table(
            "work_item_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("work_items.id"), nullable=False),
            sa.Column("entity_type", sa.String(80), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("relationship_type", sa.String(60), nullable=False, server_default="related"),
            sa.Column("label", sa.String(180), nullable=False, server_default=""),
            sa.Column("route", sa.String(260), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "work_item_id", "entity_type", "entity_id", "relationship_type",
                name="uq_work_item_link_entity_relation",
            ),
        )
        op.create_index("ix_work_item_links_work_item_id", "work_item_links", ["work_item_id"])
        op.create_index("ix_work_item_links_entity_type", "work_item_links", ["entity_type"])

    tables = set(inspect(bind).get_table_names())
    if "work_item_dependencies" not in tables:
        op.create_table(
            "work_item_dependencies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("work_items.id"), nullable=False),
            sa.Column("depends_on_work_item_id", sa.Integer(), sa.ForeignKey("work_items.id"), nullable=False),
            sa.Column("dependency_type", sa.String(40), nullable=False, server_default="finish_to_start"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("work_item_id", "depends_on_work_item_id", name="uq_work_item_dependency"),
        )
        op.create_index("ix_work_item_dependencies_work_item_id", "work_item_dependencies", ["work_item_id"])
        op.create_index(
            "ix_work_item_dependencies_depends_on_work_item_id",
            "work_item_dependencies",
            ["depends_on_work_item_id"],
        )


def downgrade() -> None:
    # 20260806_0037 ya define estas tablas en la línea V2.0. Eliminarlas aquí
    # dejaría el esquema por debajo del contrato de la revision padre.
    return
