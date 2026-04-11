from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, LanguageCode, UserGenderCode


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    avatar_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notify_likes: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    notify_subscriptions: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    notify_messages: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    show_last_activity: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    language_code: Mapped[LanguageCode | None] = mapped_column(
        Enum(
            LanguageCode,
            name='language_code_enum',
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=True,
    )
    gender: Mapped[UserGenderCode] = mapped_column(
        Enum(
            UserGenderCode,
            name='user_gender_enum',
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        server_default=text("'not_specified'"),
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    activity_seen_subscriptions_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activity_seen_subscribers_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activity_seen_likes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activity_seen_liked_by_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activity_seen_friends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profiles = relationship('PlayerProfile', back_populates='owner', cascade='all, delete-orphan')
    stats = relationship('UserStats', back_populates='user', uselist=False, cascade='all, delete-orphan')
