"""add persistent private chat system

Revision ID: 20260404_0007
Revises: 20260403_0006
Create Date: 2026-04-04 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260404_0007'
down_revision: Union[str, Sequence[str], None] = '20260403_0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('participant_1_id', sa.BigInteger(), nullable=False),
        sa.Column('participant_2_id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('participant_1_id < participant_2_id', name='ck_user_chats_participant_order'),
        sa.ForeignKeyConstraint(['participant_1_id'], ['users.id'], name=op.f('fk_user_chats_participant_1_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_2_id'], ['users.id'], name=op.f('fk_user_chats_participant_2_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_chats')),
        sa.UniqueConstraint('participant_1_id', 'participant_2_id', name='uq_user_chats_participants'),
    )
    op.create_index('ix_user_chats_participant_1_id', 'user_chats', ['participant_1_id'], unique=False)
    op.create_index('ix_user_chats_participant_2_id', 'user_chats', ['participant_2_id'], unique=False)
    op.create_index('ix_user_chats_last_message_at', 'user_chats', ['last_message_at'], unique=False)

    op.add_column('user_messages', sa.Column('chat_id', sa.Integer(), nullable=True))
    op.add_column('user_messages', sa.Column('message_type', sa.String(length=16), server_default='text', nullable=False))
    op.add_column('user_messages', sa.Column('is_read', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    op.execute(
        """
        INSERT INTO user_chats (participant_1_id, participant_2_id, created_at, last_message_at)
        SELECT
            LEAST(from_user_id, to_user_id) AS participant_1_id,
            GREATEST(from_user_id, to_user_id) AS participant_2_id,
            MIN(created_at) AS created_at,
            MAX(created_at) AS last_message_at
        FROM user_messages
        GROUP BY LEAST(from_user_id, to_user_id), GREATEST(from_user_id, to_user_id)
        ON CONFLICT (participant_1_id, participant_2_id) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE user_messages AS m
        SET chat_id = c.id
        FROM user_chats AS c
        WHERE
            c.participant_1_id = LEAST(m.from_user_id, m.to_user_id)
            AND c.participant_2_id = GREATEST(m.from_user_id, m.to_user_id)
        """
    )

    op.alter_column('user_messages', 'chat_id', nullable=False)
    op.create_foreign_key(
        op.f('fk_user_messages_chat_id_user_chats'),
        'user_messages',
        'user_chats',
        ['chat_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index('ix_user_messages_chat_id_created_at', 'user_messages', ['chat_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_messages_chat_id_created_at', table_name='user_messages')
    op.drop_constraint(op.f('fk_user_messages_chat_id_user_chats'), 'user_messages', type_='foreignkey')
    op.drop_column('user_messages', 'is_read')
    op.drop_column('user_messages', 'message_type')
    op.drop_column('user_messages', 'chat_id')

    op.drop_index('ix_user_chats_last_message_at', table_name='user_chats')
    op.drop_index('ix_user_chats_participant_2_id', table_name='user_chats')
    op.drop_index('ix_user_chats_participant_1_id', table_name='user_chats')
    op.drop_table('user_chats')
