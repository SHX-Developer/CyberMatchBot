import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode
from app.models import PlayerProfile, User
from app.repositories import ProfileRepository


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.profile_repo = ProfileRepository(session)

    async def has_any_profile(self, owner_id: int) -> bool:
        return (await self.profile_repo.count_by_owner(owner_id)) > 0

    async def create_profile_or_get_existing(self, owner_id: int, game: GameCode) -> tuple[PlayerProfile, bool]:
        existing = await self.profile_repo.get_by_owner_and_game(owner_id, game)
        if existing is not None:
            return existing, False

        created = await self.profile_repo.create_profile(owner_id, game)
        return created, True

    async def list_my_profiles(self, owner_id: int) -> list[PlayerProfile]:
        return await self.profile_repo.list_by_owner(owner_id)

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
