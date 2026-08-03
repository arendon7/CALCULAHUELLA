"""V0.11 baseline administrada por Alembic.

La migración es idempotente para instalaciones nuevas y para bases V0.10
copiadas: crea únicamente tablas y columnas que no existan mediante metadata.
"""
from typing import Sequence, Union

from alembic import op

from app.database import Base

revision: str = "20260731_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # No se destruyen datos automáticamente en una plataforma de inventarios.
    pass
