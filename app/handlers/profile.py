from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.context import ensure_user_and_locale
from app.handlers.filters import LocalizedTextFilter
from app.keyboards import language_keyboard, profile_settings_keyboard, settings_keyboard
from app.locales import LocalizationManager
from app.services import UserService
from app.utils import format_datetime

router = Router(name='profile')

LANGUAGE_LABELS = {
    'ru': 'Русский',
    'en': 'English',
    'uz': "O'zbekcha",
}


@router.message(LocalizedTextFilter('menu.profile'))
async def profile_handler(message: Message, session: AsyncSession, i18n: LocalizationManager) -> None:
    if message.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return

    user_service = UserService(session)
    payload = await user_service.get_profile_stats(user_id)

    user = payload['user']
    stats = payload['stats']
    profiles_count = payload['profiles_count']

    if user is None:
        return

    username = f'@{user.username}' if user.username else i18n.t(locale, 'value.not_set')
    language_code = user.language_code.value if user.language_code else i18n.default_locale
    language_name = LANGUAGE_LABELS.get(language_code, language_code)

    likes = stats.likes_count if stats else 0
    followers = stats.followers_count if stats else 0
    views = stats.profile_views_count if stats else 0
    mutual_likes = stats.mutual_likes_count if stats else 0

    await message.answer(
        i18n.t(
            locale,
            'profile.header',
            user_id=user.id,
            username=username,
            language=language_name,
            registered_at=format_datetime(user.registered_at, locale),
            profiles_count=profiles_count,
            likes=likes,
            followers=followers,
            views=views,
            mutual_likes=mutual_likes,
        ),
        reply_markup=profile_settings_keyboard(i18n, locale),
    )


@router.callback_query(F.data == 'settings:open')
async def settings_open_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            i18n.t(locale, 'settings.header'),
            reply_markup=settings_keyboard(i18n, locale),
        )


@router.callback_query(F.data == 'settings:language')
async def settings_language_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            i18n.t(locale, 'settings.choose_language'),
            reply_markup=language_keyboard(),
        )
