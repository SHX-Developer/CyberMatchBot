"""add mlbb profile fields

Revision ID: 20260325_0002
Revises: 20260324_0001
Create Date: 2026-03-25 01:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260325_0002'
down_revision: Union[str, Sequence[str], None] = '20260324_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

mlbb_lane_enum = postgresql.ENUM(
    'gold_lane',
    'mid_lane',
    'exp_lane',
    'jungler',
    'roamer',
    'all_lanes',
    name='mlbb_lane_enum',
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    mlbb_lane_enum.create(bind, checkfirst=True)

    op.add_column('player_profiles', sa.Column('game_player_id', sa.String(length=64), nullable=True))
    op.add_column('player_profiles', sa.Column('profile_image_file_id', sa.String(length=255), nullable=True))
    op.add_column('player_profiles', sa.Column('main_lane', mlbb_lane_enum, nullable=True))
    op.add_column('player_profiles', sa.Column('extra_lanes', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('player_profiles', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('player_profiles', 'description')
    op.drop_column('player_profiles', 'extra_lanes')
    op.drop_column('player_profiles', 'main_lane')
    op.drop_column('player_profiles', 'profile_image_file_id')
    op.drop_column('player_profiles', 'game_player_id')

    bind = op.get_bind()
    mlbb_lane_enum.drop(bind, checkfirst=True)
