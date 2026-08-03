"""V0.16: contratos, órdenes de servicio, cartera y documentos de cobro."""
from typing import Sequence, Union
from alembic import op
from app.database import Base
revision: str = "20260731_0006"
down_revision: Union[str, None] = "20260731_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

def downgrade() -> None:
    # La plataforma no elimina automáticamente registros contractuales o de cartera.
    pass
