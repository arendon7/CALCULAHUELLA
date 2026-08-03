"""V0.36: expand domain-oriented web architecture."""
from typing import Sequence, Union

revision: str = "20260803_0024"
down_revision: Union[str, None] = "20260803_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Code-level modularization only. Existing tables and historical records remain unchanged.
    pass


def downgrade() -> None:
    # Route ownership can be reverted without deleting data.
    pass
