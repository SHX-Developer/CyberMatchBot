"""add user setting for last activity visibility

Revision ID: 20260410_0010
Revises: 20260409_0009
Create Date: 2026-04-10 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260410_0010'
down_revision: Union[str, Sequence[str], None] = '20260409_0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('show_last_activity', sa.Boolean(), server_default=sa.text('true'), nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'show_last_activity')
