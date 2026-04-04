from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserMessage(Base):
    __tablename__ = 'user_messages'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('user_chats.id', ondelete='CASCADE'), nullable=False)
    from_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    to_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(16), server_default='text', nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, server_default='false', nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, server_default='false', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chat = relationship('UserChat', back_populates='messages')

    __table_args__ = (
        Index('ix_user_messages_chat_id_created_at', 'chat_id', 'created_at'),
    )
