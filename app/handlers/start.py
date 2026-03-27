from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import LanguageCode
from app.handlers.context import ensure_user_and_locale
from app.keyboards import language_keyboard, main_menu_keyboard
from app.locales import LocalizationManager
from app.services import UserService

router = Router(name='start')


async def _sync_avatar_from_telegram(user_id: int, message: Message, user_service: UserService) -> None:
    try:
        photos = await message.bot.get_user_profile_photos(user_id=user_id, limit=1)
    except Exception:
        return
    avatar_file_id: str | None = None
    if photos.photos:
        avatar_file_id = photos.photos[0][-1].file_id
    await user_service.set_avatar_file_id(user_id, avatar_file_id)


@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    user_service = UserService(session)
    await _sync_avatar_from_telegram(user_id, message, user_service)
    await state.clear()

    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return

    await message.answer(
        i18n.t(locale, 'start.welcome'),
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data.startswith('lang:set:'))
async def set_language_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    data = callback.data or ''
    language_raw = data.split(':')[-1]
    try:
        language = LanguageCode(language_raw)
    except ValueError:
        await callback.answer(i18n.t(i18n.default_locale, 'error.unknown'), show_alert=True)
        return

    user_service = UserService(session)
    await user_service.ensure_user(callback.from_user)
    await user_service.set_language(callback.from_user.id, language)

    locale = language.value
    await callback.answer(i18n.t(locale, 'language.changed'))

    if callback.message:
        await callback.message.answer(
            i18n.t(locale, 'start.welcome'),
            reply_markup=main_menu_keyboard(),
        )
