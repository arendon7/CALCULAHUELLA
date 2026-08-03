"""V0.43: certificación operativa de versión y evidencia firmada."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260803_0027"
down_revision: Union[str, None] = "20260803_0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "release_certifications" in set(inspector.get_table_names()):
        return
    op.create_table(
        "release_certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("application_version", sa.String(30), nullable=False),
        sa.Column("scope", sa.String(30), nullable=False, server_default="Local"),
        sa.Column("status", sa.String(40), nullable=False, server_default="En ejecución"),
        sa.Column("production_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("certificate_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("artifact_name", sa.String(240), nullable=False, server_default=""),
        sa.Column("artifact_sha256", sa.String(64), nullable=False, server_default=""),
        sa.Column("external_artifact_key", sa.String(400), nullable=False, server_default=""),
        sa.Column("backup_name", sa.String(240), nullable=False, server_default=""),
        sa.Column("backup_sha256", sa.String(64), nullable=False, server_default=""),
        sa.Column("external_backup_key", sa.String(400), nullable=False, server_default=""),
        sa.Column("restore_drill_id", sa.Integer(), sa.ForeignKey("restore_drills.id"), nullable=True),
        sa.Column("deployment_rehearsal_id", sa.Integer(), sa.ForeignKey("deployment_rehearsals.id"), nullable=True),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("blockers_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("performed_by", sa.String(180), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_release_certifications_organization_id", "release_certifications", ["organization_id"])
    op.create_index("ix_release_certifications_application_version", "release_certifications", ["application_version"])
    op.create_index("ix_release_certifications_scope", "release_certifications", ["scope"])
    op.create_index("ix_release_certifications_status", "release_certifications", ["status"])
    op.create_index("ix_release_certifications_production_approved", "release_certifications", ["production_approved"])
    op.create_index("ix_release_certifications_certificate_hash", "release_certifications", ["certificate_hash"])
    op.create_index("ix_release_certifications_restore_drill_id", "release_certifications", ["restore_drill_id"])
    op.create_index("ix_release_certifications_deployment_rehearsal_id", "release_certifications", ["deployment_rehearsal_id"])


def downgrade() -> None:
    op.drop_table("release_certifications")
