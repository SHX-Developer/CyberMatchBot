import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode, MlbbLaneCode
from app.models import PlayerProfile, User
from app.repositories import ProfileRepository


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.profile_repo = ProfileRepository(session)

    async def has_any_profile(self, owner_id: int) -> bool:
        return (await self.profile_repo.count_by_owner(owner_id)) > 0

    async def get_profile_for_game(self, owner_id: int, game: GameCode) -> PlayerProfile | None:
        return await self.profile_repo.get_by_owner_and_game(owner_id, game)

    async def get_profiles_indexed_by_game(self, owner_id: int) -> dict[GameCode, PlayerProfile]:
        profiles = await self.profile_repo.list_by_owner(owner_id)
        return {profile.game: profile for profile in profiles}

    async def create_profile_or_get_existing(self, owner_id: int, game: GameCode) -> tuple[PlayerProfile, bool]:
        existing = await self.profile_repo.get_by_owner_and_game(owner_id, game)
        if existing is not None:
            return existing, False

        created = await self.profile_repo.create_profile(owner_id, game)
        return created, True

    async def list_my_profiles(self, owner_id: int) -> list[PlayerProfile]:
        return await self.profile_repo.list_by_owner(owner_id)

    async def save_mlbb_profile(
        self,
        *,
        owner_id: int,
        game_player_id: str,
        profile_image_file_id: str,
        rank: str | None,
        role: str | None,
        server: str | None,
        main_lane: MlbbLaneCode,
        extra_lanes: list[MlbbLaneCode],
        description: str,
    ) -> PlayerProfile:
        profile, _ = await self.create_profile_or_get_existing(owner_id, GameCode.MLBB)
        return await self.profile_repo.save_mlbb_data(
            profile,
            game_player_id=game_player_id,
            profile_image_file_id=profile_image_file_id,
            rank=rank,
            role=role,
            server=server,
            main_lane=main_lane,
            extra_lanes=extra_lanes,
            description=description,
        )

    async def delete_owned_profile(self, owner_id: int, profile_id: uuid.UUID) -> bool:
        profile = await self.profile_repo.get_owned_profile(owner_id, profile_id)
        if profile is None:
            return False
        await self.profile_repo.delete_profile(profile)
        return True

    async def reset_owned_profile(self, owner_id: int, profile_id: uuid.UUID) -> bool:
        profile = await self.profile_repo.get_owned_profile(owner_id, profile_id)
        if profile is None:
            return False
        await self.profile_repo.reset_profile(profile)
        return True

    async def reset_by_owner_and_game(self, owner_id: int, game: GameCode) -> bool:
        profile = await self.profile_repo.get_by_owner_and_game(owner_id, game)
        if profile is None:
            return False
        await self.profile_repo.reset_profile(profile)
        return True

    async def search_profiles(self, owner_id: int, game: GameCode) -> list[tuple[PlayerProfile, User]]:
        return await self.profile_repo.search_by_game(owner_id, game)

    async def mlbb_id_exists(self, game_player_id: str, *, exclude_owner_id: int | None = None) -> bool:
        return await self.profile_repo.mlbb_id_exists(game_player_id, exclude_owner_id=exclude_owner_id)

    async def update_mlbb_profile_fields(self, owner_id: int, **fields) -> PlayerProfile | None:
        profile = await self.profile_repo.get_by_owner_and_game(owner_id, GameCode.MLBB)
        if profile is None:
            return None
        return await self.profile_repo.update_profile_fields(profile, **fields)
