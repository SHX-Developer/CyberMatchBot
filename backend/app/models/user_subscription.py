from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserSubscription(Base):
    __tablename__ = 'user_subscriptions'
    __table_args__ = (
        UniqueConstraint('follower_user_id', 'followed_user_id', name='uq_user_subscriptions_follower_followed'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    follower_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    followed_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
