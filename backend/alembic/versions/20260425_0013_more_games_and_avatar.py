"""more games (magic_chess, honkai_star_rail, zenless_zone_zero) and user avatar_data_url

Revision ID: 20260425_0013
Revises: 20260425_0012
Create Date: 2026-04-25 12:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260425_0013'
down_revision: Union[str, Sequence[str], None] = '20260425_0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Расширяем game_code_enum.
    op.execute("ALTER TYPE game_code_enum ADD VALUE IF NOT EXISTS 'magic_chess'")
    op.execute("ALTER TYPE game_code_enum ADD VALUE IF NOT EXISTS 'honkai_star_rail'")
    op.execute("ALTER TYPE game_code_enum ADD VALUE IF NOT EXISTS 'zenless_zone_zero'")

    # Аватар пользователя (data URL, base64 PNG/JPG).
    op.add_column('users', sa.Column('avatar_data_url', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_data_url')
    # значения enum в Postgres удалить нельзя без recreate — оставляем
