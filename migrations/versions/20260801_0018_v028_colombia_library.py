"""V0.28: controlled Colombian methodology library and sector calculators."""
from typing import Sequence, Union

revision: str = "20260801_0018"
down_revision: Union[str, None] = "20260801_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # V0.28 uses the existing methodology tables. Records are seeded idempotently by init_db().
    pass


def downgrade() -> None:
    # Methodology records are retained to preserve auditability and historical calculations.
    pass
