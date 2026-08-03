"""V0.35: domain-oriented web architecture and release metadata."""
from typing import Sequence, Union

revision: str = "20260803_0023"
down_revision: Union[str, None] = "20260802_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No schema change is required. Application initialization updates release
    # metadata and preserves every inventory, calculation and artifact.
    pass


def downgrade() -> None:
    # Domain extraction is a code-level change and historical data is retained.
    pass
