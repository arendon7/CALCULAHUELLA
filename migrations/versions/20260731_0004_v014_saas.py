"""V0.14: onboarding, suscripciones, uso y soporte SaaS."""
from typing import Sequence, Union
from alembic import op
from app.database import Base
revision: str = "20260731_0004"
down_revision: Union[str, None] = "20260731_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

def downgrade() -> None:
    pass
