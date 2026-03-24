"""init schema

Revision ID: 20260324_0001
Revises:
Create Date: 2026-03-24 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260324_0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

language_enum = postgresql.ENUM('ru', 'en', 'uz', name='language_code_enum', create_type=False)
game_enum = postgresql.ENUM('mlbb', 'cs_go', name='game_code_enum', create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    language_enum.create(bind, checkfirst=True)
    game_enum.create(bind, checkfirst=True)

    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('first_name', sa.String(length=128), nullable=True),
        sa.Column('last_name', sa.String(length=128), nullable=True),
        sa.Column('language_code', language_enum, nullable=True),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    )

    op.create_table(
        'player_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', sa.BigInteger(), nullable=False),
        sa.Column('game', game_enum, nullable=False),
        sa.Column('rank', sa.String(length=64), nullable=True),
        sa.Column('role', sa.String(length=64), nullable=True),
        sa.Column('play_time', sa.String(length=64), nullable=True),
        sa.Column('about', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_player_profiles_owner_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_player_profiles')),
        sa.UniqueConstraint('owner_id', 'game', name='uq_player_profiles_owner_game'),
    )
    op.create_index(op.f('ix_player_profiles_owner_id'), 'player_profiles', ['owner_id'], unique=False)

    op.create_table(
        'user_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('likes_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('followers_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('profile_views_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('mutual_likes_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_stats_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_stats')),
        sa.UniqueConstraint('user_id', name=op.f('uq_user_stats_user_id')),
    )


def downgrade() -> None:
    op.drop_table('user_stats')
    op.drop_index(op.f('ix_player_profiles_owner_id'), table_name='player_profiles')
    op.drop_table('player_profiles')
    op.drop_table('users')

    bind = op.get_bind()
    game_enum.drop(bind, checkfirst=True)
    language_enum.drop(bind, checkfirst=True)
