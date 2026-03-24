import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, GameCode
from app.models.mixins import TimestampMixin


class PlayerProfile(TimestampMixin, Base):
    __tablename__ = 'player_profiles'
    __table_args__ = (UniqueConstraint('owner_id', 'game', name='uq_player_profiles_owner_game'),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), index=True)
    game: Mapped[GameCode] = mapped_column(
        Enum(
            GameCode,
            name='game_code_enum',
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )

    rank: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    play_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner = relationship('User', back_populates='profiles')
