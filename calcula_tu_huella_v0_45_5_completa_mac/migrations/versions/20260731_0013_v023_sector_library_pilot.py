"""V0.23: sector factor library and Greenatics pilot readiness."""
from typing import Sequence, Union

from alembic import op

from app.database import Base

revision: str = "20260731_0013"
down_revision: Union[str, None] = "20260731_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # Los registros metodológicos y de piloto se conservan por trazabilidad.
    pass
