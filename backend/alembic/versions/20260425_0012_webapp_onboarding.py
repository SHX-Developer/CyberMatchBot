"""webapp onboarding: nickname, birth_date, is_registered, profile fields

Revision ID: 20260425_0012
Revises: 20260411_0011
Create Date: 2026-04-25 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '20260425_0012'
down_revision: Union[str, Sequence[str], None] = '20260411_0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Расширяем user_gender_enum значением 'hidden'.
    op.execute("ALTER TYPE user_gender_enum ADD VALUE IF NOT EXISTS 'hidden'")

    # 2. Новые поля users.
    op.add_column('users', sa.Column('nickname', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('telegram_photo_url', sa.String(length=512), nullable=True))
    op.add_column('users', sa.Column('birth_date', sa.Date(), nullable=True))
    op.add_column(
        'users',
        sa.Column(
            'is_registered',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
    )
    op.create_unique_constraint('uq_users_nickname', 'users', ['nickname'])
    op.create_index('ix_users_nickname_lower', 'users', [sa.text('lower(nickname)')], unique=True)

    # 3. Создаём profile_status_enum.
    profile_status_enum = postgresql.ENUM(
        'draft', 'active', 'paused', 'moderation', 'rejected',
        name='profile_status_enum',
        create_type=False,
    )
    profile_status_enum.create(bind, checkfirst=True)

    # 4. Расширяем player_profiles новыми полями.
    op.add_column(
        'player_profiles',
        sa.Column(
            'status',
            sa.Enum('draft', 'active', 'paused', 'moderation', 'rejected', name='profile_status_enum'),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
    )
    op.add_column('player_profiles', sa.Column('game_nickname', sa.String(length=64), nullable=True))
    op.add_column('player_profiles', sa.Column('server_id', sa.String(length=32), nullable=True))
    op.add_column('player_profiles', sa.Column('region', sa.String(length=32), nullable=True))
    op.add_column('player_profiles', sa.Column('main_role', sa.String(length=64), nullable=True))
    op.add_column('player_profiles', sa.Column('secondary_roles', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('player_profiles', sa.Column('looking_for', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('player_profiles', sa.Column('play_style', sa.String(length=32), nullable=True))
    op.add_column('player_profiles', sa.Column('microphone', sa.String(length=16), nullable=True))
    op.add_column('player_profiles', sa.Column('play_time_slots', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('player_profiles', sa.Column('screenshot_url', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('player_profiles', 'screenshot_url')
    op.drop_column('player_profiles', 'play_time_slots')
    op.drop_column('player_profiles', 'microphone')
    op.drop_column('player_profiles', 'play_style')
    op.drop_column('player_profiles', 'looking_for')
    op.drop_column('player_profiles', 'secondary_roles')
    op.drop_column('player_profiles', 'main_role')
    op.drop_column('player_profiles', 'region')
    op.drop_column('player_profiles', 'server_id')
    op.drop_column('player_profiles', 'game_nickname')
    op.drop_column('player_profiles', 'status')

    bind = op.get_bind()
    profile_status_enum = postgresql.ENUM(name='profile_status_enum', create_type=False)
    profile_status_enum.drop(bind, checkfirst=True)

    op.drop_index('ix_users_nickname_lower', table_name='users')
    op.drop_constraint('uq_users_nickname', 'users', type_='unique')
    op.drop_column('users', 'is_registered')
    op.drop_column('users', 'birth_date')
    op.drop_column('users', 'telegram_photo_url')
    op.drop_column('users', 'nickname')
    # user_gender_enum 'hidden' value не удаляем — Postgres не поддерживает удаление значений enum без recreate.
