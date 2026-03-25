"""add user profile editable fields and counters

Revision ID: 20260325_0003
Revises: 20260325_0002
Create Date: 2026-03-25 13:30:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260325_0003'
down_revision: Union[str, Sequence[str], None] = '20260325_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('full_name', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('avatar_file_id', sa.String(length=255), nullable=True))

    op.add_column('user_stats', sa.Column('subscriptions_count', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('user_stats', sa.Column('friends_count', sa.Integer(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    op.drop_column('user_stats', 'friends_count')
    op.drop_column('user_stats', 'subscriptions_count')
    op.drop_column('users', 'avatar_file_id')
    op.drop_column('users', 'full_name')
