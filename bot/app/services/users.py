from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import LanguageCode
from app.models import User, UserStats
from app.repositories import InteractionRepository, ProfileRepository, UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.user_repo = UserRepository(session)
        self.profile_repo = ProfileRepository(session)
        self.interaction_repo = InteractionRepository(session)

    async def ensure_user(self, telegram_user: TelegramUser) -> User:
        return await self.user_repo.create_or_update(
            user_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )

    async def get_user(self, user_id: int) -> User | None:
        return await self.user_repo.get_by_id(user_id)

    async def set_language(self, user_id: int, language_code: LanguageCode) -> User | None:
        return await self.user_repo.set_language(user_id, language_code)

    async def get_locale(self, user_id: int) -> str | None:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.language_code:
            return None
        return user.language_code.value

    async def get_profile_stats(self, user_id: int) -> dict[str, int | User | UserStats | None]:
        user = await self.user_repo.get_by_id(user_id)
        stats = await self.user_repo.get_stats(user_id)
        profiles_count = await self.profile_repo.count_by_owner(user_id)
        counters = await self.interaction_repo.profile_counters(user_id)

        return {
            'user': user,
            'stats': stats,
            'profiles_count': profiles_count,
            'likes_count': counters['likes_count'],
            'followers_count': counters['followers_count'],
            'subscriptions_count': counters['subscriptions_count'],
            'friends_count': counters['friends_count'],
        }

    async def set_avatar_file_id(self, user_id: int, avatar_file_id: str | None) -> User | None:
        return await self.user_repo.set_avatar_file_id(user_id, avatar_file_id)

    async def set_full_name(self, user_id: int, full_name: str) -> User | None:
        return await self.user_repo.set_full_name(user_id, full_name)

    async def nickname_exists(self, nickname: str, *, exclude_user_id: int | None = None) -> bool:
        return await self.user_repo.nickname_exists(nickname, exclude_user_id=exclude_user_id)

    async def find_by_nickname_or_username(self, value: str) -> User | None:
        return await self.user_repo.find_by_nickname_or_username(value)

    async def notification_settings(self, user_id: int) -> dict[str, bool]:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            return {
                'likes': True,
                'subscriptions': True,
                'messages': True,
            }
        return {
            'likes': bool(getattr(user, 'notify_likes', True)),
            'subscriptions': bool(getattr(user, 'notify_subscriptions', True)),
            'messages': bool(getattr(user, 'notify_messages', True)),
        }

    async def toggle_notification(self, user_id: int, kind: str) -> bool | None:
        mapping = {
            'likes': 'notify_likes',
            'subscriptions': 'notify_subscriptions',
            'messages': 'notify_messages',
        }
        field = mapping.get(kind)
        if field is None:
            return None
        return await self.user_repo.toggle_notification(user_id, field)
