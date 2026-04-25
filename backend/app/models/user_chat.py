from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserChat(Base):
    __tablename__ = 'user_chats'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    participant_1_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    participant_2_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    messages = relationship('UserMessage', back_populates='chat', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('participant_1_id', 'participant_2_id', name='uq_user_chats_participants'),
        CheckConstraint('participant_1_id < participant_2_id', name='ck_user_chats_participant_order'),
        Index('ix_user_chats_participant_1_id', 'participant_1_id'),
        Index('ix_user_chats_participant_2_id', 'participant_2_id'),
        Index('ix_user_chats_last_message_at', 'last_message_at'),
    )
