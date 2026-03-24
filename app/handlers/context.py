from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import UserService


async def ensure_user_and_locale(telegram_user: TelegramUser, session: AsyncSession) -> tuple[int, str | None]:
    user_service = UserService(session)
    user = await user_service.ensure_user(telegram_user)
    locale = user.language_code.value if user.language_code else None
    return user.id, locale
