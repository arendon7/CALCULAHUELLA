"""V0.37: persistence models, repositories and services by domain."""
from typing import Sequence, Union

revision: str = "20260803_0025"
down_revision: Union[str, None] = "20260803_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Code-level persistence modularization. The public database facade and
    # every existing table remain compatible; no destructive schema action.
    pass


def downgrade() -> None:
    # Model modules can be recombined without deleting historical records.
    pass
