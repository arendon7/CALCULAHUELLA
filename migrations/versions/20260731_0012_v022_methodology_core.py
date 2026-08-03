"""V0.22: documented methodology sources, factor provenance, selection rules and reference cases."""
from typing import Sequence, Union

from alembic import op

from app.database import Base

revision: str = "20260731_0012"
down_revision: Union[str, None] = "20260731_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # Se conserva la trazabilidad metodológica y los resultados de validación.
    pass
