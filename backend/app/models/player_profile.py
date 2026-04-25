import uuid

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, GameCode, MlbbLaneCode, ProfileStatus
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

    status: Mapped[ProfileStatus] = mapped_column(
        Enum(
            ProfileStatus,
            name='profile_status_enum',
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        server_default=text("'active'"),
    )

    # Legacy MVP fields kept for backward compatibility with existing data shape.
    rank: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    play_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extended MLBB profile fields.
    game_player_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profile_image_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    main_lane: Mapped[MlbbLaneCode | None] = mapped_column(
        Enum(
            MlbbLaneCode,
            name='mlbb_lane_enum',
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=True,
    )
    extra_lanes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mythic_stars: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Web-app extended fields (per onboarding ТЗ).
    game_nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    server_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    main_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secondary_roles: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    looking_for: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    play_style: Mapped[str | None] = mapped_column(String(32), nullable=True)
    microphone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    play_time_slots: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    screenshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner = relationship('User', back_populates='profiles')
