"""V0.13: gobierno metodológico, cumplimiento y control documental."""
from typing import Sequence, Union
from alembic import op
from app.database import Base
revision: str = "20260731_0003"
down_revision: Union[str, None] = "20260731_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

def downgrade() -> None:
    pass
