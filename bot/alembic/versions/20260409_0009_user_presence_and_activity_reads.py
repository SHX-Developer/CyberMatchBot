"""add user presence timestamps and activity read markers

Revision ID: 20260409_0009
Revises: 20260407_0008
Create Date: 2026-04-09 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260409_0009'
down_revision: Union[str, Sequence[str], None] = '20260407_0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('users', sa.Column('activity_seen_subscriptions_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('activity_seen_subscribers_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('activity_seen_likes_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('activity_seen_liked_by_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('activity_seen_friends_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user_stats', sa.Column('profile_visits_count', sa.Integer(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    op.drop_column('user_stats', 'profile_visits_count')
    op.drop_column('users', 'activity_seen_friends_at')
    op.drop_column('users', 'activity_seen_liked_by_at')
    op.drop_column('users', 'activity_seen_likes_at')
    op.drop_column('users', 'activity_seen_subscribers_at')
    op.drop_column('users', 'activity_seen_subscriptions_at')
    op.drop_column('users', 'last_seen_at')

