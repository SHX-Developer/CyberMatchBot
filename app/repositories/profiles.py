import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode
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

    async def search_by_game(self, owner_id: int, game: GameCode) -> list[tuple[PlayerProfile, User]]:
        stmt = (
            select(PlayerProfile, User)
            .join(User, User.id == PlayerProfile.owner_id)
            .where(and_(PlayerProfile.game == game, PlayerProfile.owner_id != owner_id))
            .order_by(PlayerProfile.created_at.desc())
            .limit(50)
        )
        result = await self.session.execute(stmt)
        return list(result.all())
