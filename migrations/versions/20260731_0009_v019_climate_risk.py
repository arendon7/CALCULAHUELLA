"""V0.19: riesgos climáticos, controles y hoja de ruta de transición."""
from typing import Sequence, Union
from alembic import op
from app.database import Base

revision: str = "20260731_0009"
down_revision: Union[str, None] = "20260731_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # Se conserva el registro para no perder evaluación ni trazabilidad climática.
    pass
