"""add mythic stars field to player profiles

Revision ID: 20260403_0006
Revises: 20260326_0005
Create Date: 2026-04-03 20:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260403_0006'
down_revision: Union[str, Sequence[str], None] = '20260326_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('player_profiles', sa.Column('mythic_stars', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('player_profiles', 'mythic_stars')
