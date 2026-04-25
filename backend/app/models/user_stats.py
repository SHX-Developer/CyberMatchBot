from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class UserStats(TimestampMixin, Base):
    __tablename__ = 'user_stats'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), unique=True)

    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subscriptions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    friends_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profile_views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profile_visits_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mutual_likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user = relationship('User', back_populates='stats')
