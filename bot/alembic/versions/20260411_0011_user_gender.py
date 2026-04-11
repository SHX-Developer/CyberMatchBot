"""add user gender with default not_specified

Revision ID: 20260411_0011
Revises: 20260410_0010
Create Date: 2026-04-11 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260411_0011'
down_revision: Union[str, Sequence[str], None] = '20260410_0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_gender_enum = sa.Enum('not_specified', 'male', 'female', name='user_gender_enum')
    user_gender_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'users',
        sa.Column('gender', user_gender_enum, server_default=sa.text("'not_specified'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('users', 'gender')
    user_gender_enum = sa.Enum('not_specified', 'male', 'female', name='user_gender_enum')
    user_gender_enum.drop(op.get_bind(), checkfirst=True)
