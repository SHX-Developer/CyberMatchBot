from aiogram.types import User as TelegramUser
from aiogram.types import ReplyKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import main_menu_keyboard
from app.locales import LocalizationManager
from app.services import ChatService, InteractionService, UserService


async def ensure_user_and_locale(telegram_user: TelegramUser, session: AsyncSession) -> tuple[int, str | None]:
    user_service = UserService(session)
    user = await user_service.ensure_user(telegram_user)
    locale = user.language_code.value if user.language_code else None
    return user.id, locale


async def unread_activity_counters(user_id: int, session: AsyncSession) -> dict[str, int]:
    users = UserService(session)
    interactions = InteractionService(session)
    seen_map = await users.activity_seen_map(user_id)
    return await interactions.unread_activity_counters(user_id, seen_at=seen_map)


def unread_activity_total(counters: dict[str, int]) -> int:
    return int(counters.get('subscribers', 0) + counters.get('liked_by', 0) + counters.get('friends', 0))


async def main_menu_keyboard_with_counters(
    *,
    user_id: int,
    locale: str,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> ReplyKeyboardMarkup:
    unread_messages = await ChatService(session).unread_messages_count(user_id)
    activity_counters = await unread_activity_counters(user_id, session)
    return main_menu_keyboard(
        i18n,
        locale,
        unread_messages=unread_messages,
        unread_activity=unread_activity_total(activity_counters),
    )
