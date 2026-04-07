import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode, MlbbLaneCode
from app.models import PlayerProfile, User


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_by_owner(self, owner_id: int) -> int:
        stmt = select(func.count(PlayerProfile.id)).where(PlayerProfile.owner_id == owner_id)
        return int((await self.session.scalar(stmt)) or 0)

    async def list_by_owner(self, owner_id: int) -> list[PlayerProfile]:
        stmt = (
            select(PlayerProfile)
            .where(PlayerProfile.owner_id == owner_id)
            .order_by(PlayerProfile.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_by_owner_and_game(self, owner_id: int, game: GameCode) -> PlayerProfile | None:
        stmt = select(PlayerProfile).where(
            and_(PlayerProfile.owner_id == owner_id, PlayerProfile.game == game)
        )
        return await self.session.scalar(stmt)

    async def create_profile(self, owner_id: int, game: GameCode) -> PlayerProfile:
        profile = PlayerProfile(owner_id=owner_id, game=game)
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def reset_profile(self, profile: PlayerProfile) -> PlayerProfile:
        profile.rank = None
        profile.role = None
        profile.play_time = None
        profile.about = None
        profile.game_player_id = None
        profile.profile_image_file_id = None
        profile.main_lane = None
        profile.extra_lanes = None
        profile.description = None
        profile.mythic_stars = None
        await self.session.flush()
        return profile

    async def save_mlbb_data(
        self,
        profile: PlayerProfile,
        *,
        game_player_id: str,
        profile_image_file_id: str,
        rank: str | None,
        role: str | None,
        server: str | None,
        main_lane: MlbbLaneCode,
        extra_lanes: list[MlbbLaneCode],
        description: str,
        mythic_stars: int | None = None,
    ) -> PlayerProfile:
        profile.game_player_id = game_player_id
        profile.profile_image_file_id = profile_image_file_id
        profile.rank = rank
        profile.role = role
        profile.play_time = server
        profile.main_lane = main_lane
        profile.extra_lanes = [lane.value for lane in extra_lanes]
        profile.description = description
        profile.about = description
        profile.mythic_stars = mythic_stars
        await self.session.flush()
        return profile

    async def save_generic_profile_data(
        self,
        profile: PlayerProfile,
        *,
        game_player_id: str,
        profile_image_file_id: str,
        rank: str | None,
        role: str | None,
        server: str | None,
        description: str,
    ) -> PlayerProfile:
        profile.game_player_id = game_player_id
        profile.profile_image_file_id = profile_image_file_id
        profile.rank = rank
        profile.role = role
        profile.play_time = server
        profile.description = description
        profile.about = description
        profile.main_lane = None
        profile.extra_lanes = None
        profile.mythic_stars = None
        await self.session.flush()
        return profile

    async def get_owned_profile(self, owner_id: int, profile_id: uuid.UUID) -> PlayerProfile | None:
        stmt = select(PlayerProfile).where(
            and_(PlayerProfile.id == profile_id, PlayerProfile.owner_id == owner_id)
        )
        return await self.session.scalar(stmt)

    async def delete_profile(self, profile: PlayerProfile) -> None:
        await self.session.delete(profile)
        await self.session.flush()

    async def update_profile_fields(self, profile: PlayerProfile, **fields) -> PlayerProfile:
        for field, value in fields.items():
            setattr(profile, field, value)
        await self.session.flush()
        return profile

    async def search_by_game(self, owner_id: int, game: GameCode) -> list[tuple[PlayerProfile, User]]:
        stmt = (
            select(PlayerProfile, User)
            .join(User, User.id == PlayerProfile.owner_id)
            .where(and_(PlayerProfile.game == game, PlayerProfile.owner_id != owner_id))
            .order_by(PlayerProfile.updated_at.desc())
            .limit(50)
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def mlbb_id_exists(self, game_player_id: str, *, exclude_owner_id: int | None = None) -> bool:
        return await self.game_id_exists(
            game=GameCode.MLBB,
            game_player_id=game_player_id,
            exclude_owner_id=exclude_owner_id,
        )

    async def game_id_exists(
        self,
        *,
        game: GameCode,
        game_player_id: str,
        exclude_owner_id: int | None = None,
    ) -> bool:
        conditions = [
            PlayerProfile.game == game,
            PlayerProfile.game_player_id == game_player_id,
        ]
        if exclude_owner_id is not None:
            conditions.append(PlayerProfile.owner_id != exclude_owner_id)
        stmt = select(PlayerProfile.id).where(and_(*conditions)).limit(1)
        return (await self.session.scalar(stmt)) is not None
