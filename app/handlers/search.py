from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.filters import LocalizedTextFilter
from app.keyboards import game_select_keyboard, language_keyboard, open_my_profiles_keyboard
from app.locales import LocalizationManager
from app.services import ProfileService
from app.utils import format_datetime, format_mlbb_profile_card, game_label

router = Router(name='search')


@router.message(LocalizedTextFilter('menu.find_teammate'))
async def find_teammate_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    await state.clear()
    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return

    profile_service = ProfileService(session)
    if not await profile_service.has_any_profile(user_id):
        await message.answer(
            i18n.t(locale, 'search.need_profile'),
            reply_markup=open_my_profiles_keyboard(i18n, locale),
        )
        return

    await message.answer(
        i18n.t(locale, 'game.choose.search'),
        reply_markup=game_select_keyboard(i18n, locale, 'search:game', one_per_row=True),
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

    await callback.message.answer(i18n.t(locale, 'search.results.title', game=game_label(i18n, locale, game)))

    for profile, user in found:
        if user.username:
            player_name = f"@{escape(user.username)}"
        else:
            if user.first_name or user.last_name:
                player_name = escape(user.first_name or user.last_name or '')
            else:
                player_name = i18n.t(locale, 'value.not_set')

        if game == GameCode.MLBB:
            caption = format_mlbb_profile_card(
                i18n,
                locale,
                profile,
                title_key='search.card.mlbb',
                player_name=player_name,
            )
            if profile.profile_image_file_id:
                await callback.message.answer_photo(photo=profile.profile_image_file_id, caption=caption)
            else:
                await callback.message.answer(caption)
            continue

        await callback.message.answer(
            i18n.t(
                locale,
                'search.card.generic',
                player_name=player_name,
                game=game_label(i18n, locale, profile.game),
                updated_at=format_datetime(profile.updated_at, locale),
            )
        )
