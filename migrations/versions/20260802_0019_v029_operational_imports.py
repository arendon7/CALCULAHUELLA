"""V0.29: reusable operational imports, mapping profiles and row traceability."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0019"
down_revision: Union[str, None] = "20260801_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def _index_names(inspector, table: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "operational_import_profiles" not in tables:
        op.create_table(
            "operational_import_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventories.id"), nullable=True),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("source_format", sa.String(length=20), nullable=False, server_default="XLSX"),
            sa.Column("sheet_name", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("delimiter", sa.String(length=10), nullable=False, server_default=","),
            sa.Column("header_row", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("mapping_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("defaults_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.String(length=180), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("organization_id", "name", name="uq_operational_import_profile_org_name"),
        )
        op.create_index("ix_operational_import_profiles_organization_id", "operational_import_profiles", ["organization_id"], unique=False)
        op.create_index("ix_operational_import_profiles_inventory_id", "operational_import_profiles", ["inventory_id"], unique=False)

    inspector = sa.inspect(bind)
    batch_columns = _column_names(inspector, "data_import_batches")
    with op.batch_alter_table("data_import_batches") as batch:
        if "inventory_id" not in batch_columns:
            batch.add_column(sa.Column("inventory_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_data_import_batches_inventory_id", "inventories", ["inventory_id"], ["id"])
        if "import_profile_id" not in batch_columns:
            batch.add_column(sa.Column("import_profile_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_data_import_batches_import_profile_id", "operational_import_profiles", ["import_profile_id"], ["id"])
        if "source_format" not in batch_columns:
            batch.add_column(sa.Column("source_format", sa.String(length=20), nullable=False, server_default="XLSX"))
        if "source_sheet" not in batch_columns:
            batch.add_column(sa.Column("source_sheet", sa.String(length=120), nullable=False, server_default=""))
        if "mapping_json" not in batch_columns:
            batch.add_column(sa.Column("mapping_json", sa.Text(), nullable=False, server_default="{}"))
        if "original_headers_json" not in batch_columns:
            batch.add_column(sa.Column("original_headers_json", sa.Text(), nullable=False, server_default="[]"))

    inspector = sa.inspect(bind)
    batch_indexes = _index_names(inspector, "data_import_batches")
    if "ix_data_import_batches_inventory_id" not in batch_indexes:
        op.create_index("ix_data_import_batches_inventory_id", "data_import_batches", ["inventory_id"], unique=False)
    if "ix_data_import_batches_import_profile_id" not in batch_indexes:
        op.create_index("ix_data_import_batches_import_profile_id", "data_import_batches", ["import_profile_id"], unique=False)

    inspector = sa.inspect(bind)
    row_columns = _column_names(inspector, "data_import_rows")
    with op.batch_alter_table("data_import_rows") as batch:
        if "raw_payload_json" not in row_columns:
            batch.add_column(sa.Column("raw_payload_json", sa.Text(), nullable=False, server_default="{}"))
        if "row_fingerprint" not in row_columns:
            batch.add_column(sa.Column("row_fingerprint", sa.String(length=64), nullable=False, server_default=""))
        if "duplicate_of_activity_id" not in row_columns:
            batch.add_column(sa.Column("duplicate_of_activity_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_data_import_rows_duplicate_activity", "activity_data", ["duplicate_of_activity_id"], ["id"])

    inspector = sa.inspect(bind)
    row_indexes = _index_names(inspector, "data_import_rows")
    if "ix_data_import_rows_row_fingerprint" not in row_indexes:
        op.create_index("ix_data_import_rows_row_fingerprint", "data_import_rows", ["row_fingerprint"], unique=False)
    if "ix_data_import_rows_duplicate_of_activity_id" not in row_indexes:
        op.create_index("ix_data_import_rows_duplicate_of_activity_id", "data_import_rows", ["duplicate_of_activity_id"], unique=False)


def downgrade() -> None:
    # Import mappings and traceability are retained intentionally.
    pass
