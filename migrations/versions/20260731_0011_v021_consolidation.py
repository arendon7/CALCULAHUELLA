"""V0.21: consolidation findings, release gates and role journey validations."""
from typing import Sequence, Union

from alembic import op

from app.database import Base

revision: str = "20260731_0011"
down_revision: Union[str, None] = "20260731_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # Se conserva el histórico de alistamiento y validación de V1.0.
    pass
