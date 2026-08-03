"""V0.18: analítica de impacto, benchmarking e intensidades."""
from typing import Sequence, Union
from alembic import op
from app.database import Base

revision: str = "20260731_0008"
down_revision: Union[str, None] = "20260731_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

def downgrade() -> None:
    # Se preservan referencias y snapshots para mantener trazabilidad histórica.
    pass
