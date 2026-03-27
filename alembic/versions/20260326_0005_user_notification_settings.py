"""add user notification settings

Revision ID: 20260326_0005
Revises: 20260325_0004
Create Date: 2026-03-26 21:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260326_0005'
down_revision: Union[str, Sequence[str], None] = '20260325_0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('notify_likes', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('users', sa.Column('notify_subscriptions', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('users', sa.Column('notify_messages', sa.Boolean(), server_default=sa.text('true'), nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'notify_messages')
    op.drop_column('users', 'notify_subscriptions')
    op.drop_column('users', 'notify_likes')

