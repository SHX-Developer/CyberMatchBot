from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, GameCode


class UserLike(Base):
    __tablename__ = 'user_likes'
    __table_args__ = (UniqueConstraint('from_user_id', 'to_user_id', 'game', name='uq_user_likes_from_to_game'),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    to_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    game: Mapped[GameCode] = mapped_column(
        Enum(
            GameCode,
            name='game_code_enum',
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
