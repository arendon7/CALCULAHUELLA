"""V0.56 operación del servicio e invitaciones seguras.

Revision ID: 20260805_0032
Revises: 20260804_0031
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa

revision = "20260805_0032"
down_revision = "20260804_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "user_invitations" in inspector.get_table_names():
        return
    op.create_table(
        "user_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("invited_name", sa.String(length=140), nullable=False, server_default=""),
        sa.Column("role", sa.String(length=40), nullable=False, server_default="Cliente"),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="Pendiente"),
        sa.Column("invited_by", sa.String(length=180), nullable=False, server_default="sistema"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_user_invitation_token_hash"),
    )
    op.create_index("ix_user_invitations_organization_id", "user_invitations", ["organization_id"])
    op.create_index("ix_user_invitations_email", "user_invitations", ["email"])
    op.create_index("ix_user_invitations_token_hash", "user_invitations", ["token_hash"])
    op.create_index("ix_user_invitations_status", "user_invitations", ["status"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "user_invitations" in inspector.get_table_names():
        op.drop_table("user_invitations")
