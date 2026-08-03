"""V0.17: éxito del cliente, salud de cuenta, valor y renovación."""
from typing import Sequence, Union
from alembic import op
from app.database import Base

revision: str = "20260731_0007"
down_revision: Union[str, None] = "20260731_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # La plataforma conserva el histórico de salud, valor y renovación.
    pass
