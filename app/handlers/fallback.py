from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.context import ensure_user_and_locale
from app.keyboards import language_keyboard, main_menu_keyboard
from app.locales import LocalizationManager

router = Router(name='fallback')


@router.message(F.text)
async def fallback_handler(message: Message, session: AsyncSession, i18n: LocalizationManager) -> None:
    if message.from_user is None:
        return

    _, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        await message.answer(
            i18n.t(i18n.default_locale, 'language.prompt_missing'),
            reply_markup=language_keyboard(),
        )
        return

    await message.answer(
        i18n.t(locale, 'start.welcome'),
        reply_markup=main_menu_keyboard(),
    )
