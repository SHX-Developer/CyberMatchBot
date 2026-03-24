from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import LanguageCode
from app.models import User, UserStats


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def create_or_update(self, *, user_id: int, username: str | None, first_name: str | None, last_name: str | None) -> User:
        user = await self.get_by_id(user_id)
        if user is None:
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            self.session.add(user)
            self.session.add(UserStats(user=user))
            await self.session.flush()
            return user

        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        await self.session.flush()
        return user

    async def set_language(self, user_id: int, language_code: LanguageCode) -> User | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.language_code = language_code
        await self.session.flush()
        return user

    async def get_stats(self, user_id: int) -> UserStats | None:
        stmt = select(UserStats).where(UserStats.user_id == user_id)
        return await self.session.scalar(stmt)
