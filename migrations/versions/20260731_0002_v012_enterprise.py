"""V0.12: automatizaciones, integraciones y operación multiempresa.

Crea de forma idempotente las nuevas tablas usando la metadata vigente.
No elimina ni transforma datos históricos.
"""
from typing import Sequence, Union

from alembic import op

from app.database import Base

revision: str = "20260731_0002"
down_revision: Union[str, None] = "20260731_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # No se destruyen datos automáticamente en una plataforma de inventarios.
    pass
