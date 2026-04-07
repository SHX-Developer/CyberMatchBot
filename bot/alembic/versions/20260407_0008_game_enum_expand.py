"""expand game enum with genshin and pubg

Revision ID: 20260407_0008
Revises: 20260404_0007
Create Date: 2026-04-07 00:00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260407_0008'
down_revision: Union[str, Sequence[str], None] = '20260404_0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE game_code_enum ADD VALUE IF NOT EXISTS 'genshin_impact'")
    op.execute("ALTER TYPE game_code_enum ADD VALUE IF NOT EXISTS 'pubg_mobile'")


def downgrade() -> None:
    # PostgreSQL does not support easy removal of enum values in downgrade.
    pass
