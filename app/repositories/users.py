from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import LanguageCode
from app.models import User, UserStats


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _compose_full_name(first_name: str | None, last_name: str | None) -> str | None:
        parts = [part.strip() for part in (first_name, last_name) if part and part.strip()]
        return ' '.join(parts) if parts else None

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def create_or_update(self, *, user_id: int, username: str | None, first_name: str | None, last_name: str | None) -> User:
        user = await self.get_by_id(user_id)
        if user is None:
            user = User(
                id=user_id,
                username=username,
                full_name=None,
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

    async def set_avatar_file_id(self, user_id: int, avatar_file_id: str | None) -> User | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None
        user.avatar_file_id = avatar_file_id
        await self.session.flush()
        return user

    async def set_full_name(self, user_id: int, full_name: str) -> User | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None
        user.full_name = full_name
        await self.session.flush()
        return user

    async def nickname_exists(self, nickname: str, *, exclude_user_id: int | None = None) -> bool:
        nickname_normalized = nickname.strip().lower()
        stmt = select(User.id).where(func.lower(User.full_name) == nickname_normalized)
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        stmt = stmt.limit(1)
        return (await self.session.scalar(stmt)) is not None

    async def toggle_notification(self, user_id: int, field: str) -> bool | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None
        if field not in {'notify_likes', 'notify_subscriptions', 'notify_messages'}:
            return None
        current = bool(getattr(user, field, True))
        setattr(user, field, not current)
        await self.session.flush()
        return bool(getattr(user, field))
