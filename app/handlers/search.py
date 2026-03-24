from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.filters import LocalizedTextFilter
from app.keyboards import create_profile_keyboard, game_select_keyboard, language_keyboard
from app.locales import LocalizationManager
from app.services import ProfileService
from app.utils import format_datetime, game_label

router = Router(name='search')


@router.message(LocalizedTextFilter('menu.find_teammate'))
async def find_teammate_handler(message: Message, session: AsyncSession, i18n: LocalizationManager) -> None:
    if message.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return

    profile_service = ProfileService(session)
    if not await profile_service.has_any_profile(user_id):
        await message.answer(
            i18n.t(locale, 'warning.create_profile_first'),
            reply_markup=create_profile_keyboard(i18n, locale),
        )
        return

    await message.answer(
        i18n.t(locale, 'search.choose_game'),
        reply_markup=game_select_keyboard(i18n, locale, 'search:game'),
    )


@router.callback_query(F.data.startswith('search:game:'))
async def search_by_game_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    data = callback.data or ''
    game_raw = data.split(':')[-1]
    try:
        game = GameCode(game_raw)
    except ValueError:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    profile_service = ProfileService(session)
    found = await profile_service.search_profiles(user_id, game)

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if not found:
        await callback.message.answer(i18n.t(locale, 'search.empty'))
        return

    await callback.message.answer(i18n.t(locale, 'search.header'))
    game_name = game_label(i18n, locale, game)

    for profile, user in found:
        if user.username:
            text = i18n.t(
                locale,
                'search.item',
                username=user.username,
                game=game_name,
                created_at=format_datetime(profile.created_at, locale),
            )
        else:
            display_name = user.first_name or user.last_name or i18n.t(locale, 'value.not_set')
            text = i18n.t(
                locale,
                'search.item_no_username',
                name=escape(display_name),
                game=game_name,
                created_at=format_datetime(profile.created_at, locale),
            )
        await callback.message.answer(text)
