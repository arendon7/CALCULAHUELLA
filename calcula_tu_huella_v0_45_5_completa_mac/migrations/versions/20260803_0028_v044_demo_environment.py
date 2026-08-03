"""V0.44 certified demonstration environment.

Revision ID: 20260803_0028
Revises: 20260803_0027
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa

revision = "20260803_0028"
down_revision = "20260803_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "demo_environment_certifications" in set(inspector.get_table_names()):
        return
    op.create_table(
        "demo_environment_certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("application_version", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="En ejecución"),
        sa.Column("certificate_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("artifact_name", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("checks_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("performed_by", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_demo_cert_org", "demo_environment_certifications", ["organization_id"])
    op.create_index("ix_demo_cert_version", "demo_environment_certifications", ["application_version"])
    op.create_index("ix_demo_cert_status", "demo_environment_certifications", ["status"])
    op.create_index("ix_demo_cert_hash", "demo_environment_certifications", ["certificate_hash"])


def downgrade() -> None:
    op.drop_index("ix_demo_cert_hash", table_name="demo_environment_certifications")
    op.drop_index("ix_demo_cert_status", table_name="demo_environment_certifications")
    op.drop_index("ix_demo_cert_version", table_name="demo_environment_certifications")
    op.drop_index("ix_demo_cert_org", table_name="demo_environment_certifications")
    op.drop_table("demo_environment_certifications")
