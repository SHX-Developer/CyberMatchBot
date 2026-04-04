"""add search interactions tables

Revision ID: 20260325_0004
Revises: 20260325_0003
Create Date: 2026-03-25 20:10:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260325_0004'
down_revision: Union[str, Sequence[str], None] = '20260325_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

game_enum = postgresql.ENUM('mlbb', 'cs_go', name='game_code_enum', create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    game_enum.create(bind, checkfirst=True)

    op.create_table(
        'user_likes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_user_id', sa.BigInteger(), nullable=False),
        sa.Column('to_user_id', sa.BigInteger(), nullable=False),
        sa.Column('game', game_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], name=op.f('fk_user_likes_from_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], name=op.f('fk_user_likes_to_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_likes')),
        sa.UniqueConstraint('from_user_id', 'to_user_id', 'game', name='uq_user_likes_from_to_game'),
    )

    op.create_table(
        'user_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('follower_user_id', sa.BigInteger(), nullable=False),
        sa.Column('followed_user_id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['follower_user_id'],
            ['users.id'],
            name=op.f('fk_user_subscriptions_follower_user_id_users'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['followed_user_id'],
            ['users.id'],
            name=op.f('fk_user_subscriptions_followed_user_id_users'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_subscriptions')),
        sa.UniqueConstraint('follower_user_id', 'followed_user_id', name='uq_user_subscriptions_follower_followed'),
    )

    op.create_table(
        'user_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_user_id', sa.BigInteger(), nullable=False),
        sa.Column('to_user_id', sa.BigInteger(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_hidden', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['from_user_id'],
            ['users.id'],
            name=op.f('fk_user_messages_from_user_id_users'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['to_user_id'],
            ['users.id'],
            name=op.f('fk_user_messages_to_user_id_users'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_messages')),
    )


def downgrade() -> None:
    op.drop_table('user_messages')
    op.drop_table('user_subscriptions')
    op.drop_table('user_likes')
