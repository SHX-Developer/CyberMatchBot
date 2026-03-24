import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.filters import LocalizedTextFilter
from app.keyboards import (
    add_other_game_keyboard,
    create_profile_keyboard,
    existing_profile_keyboard,
    game_select_keyboard,
    language_keyboard,
    profile_actions_keyboard,
)
from app.locales import LocalizationManager
from app.services import ProfileService
from app.utils import format_datetime, game_label

router = Router(name='profiles')


async def _send_my_profiles(
    message: Message,
    *,
    user_id: int,
    locale: str,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    profile_service = ProfileService(session)
    profiles = await profile_service.list_my_profiles(user_id)

    if not profiles:
        await message.answer(
            i18n.t(locale, 'profiles.empty'),
            reply_markup=create_profile_keyboard(i18n, locale),
        )
        return

    await message.answer(i18n.t(locale, 'profiles.header'))
    for profile in profiles:
        await message.answer(
            i18n.t(
                locale,
                'profiles.item',
                game=game_label(i18n, locale, profile.game),
                created_at=format_datetime(profile.created_at, locale),
                updated_at=format_datetime(profile.updated_at, locale),
            ),
            reply_markup=profile_actions_keyboard(i18n, locale, profile.id),
        )

    await message.answer(
        i18n.t(locale, 'action.add_profile_other_game'),
        reply_markup=add_other_game_keyboard(i18n, locale),
    )


@router.message(LocalizedTextFilter('menu.my_profiles'))
async def my_profiles_handler(message: Message, session: AsyncSession, i18n: LocalizationManager) -> None:
    if message.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return

    await _send_my_profiles(message, user_id=user_id, locale=locale, session=session, i18n=i18n)


@router.callback_query(F.data == 'profile:add')
async def add_profile_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.answer(
                i18n.t(i18n.default_locale, 'language.select'),
                reply_markup=language_keyboard(),
            )
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            i18n.t(locale, 'game.choose'),
            reply_markup=game_select_keyboard(i18n, locale, 'profile:create'),
        )


@router.callback_query(F.data.startswith('profile:create:'))
async def create_profile_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
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
    profile, created = await profile_service.create_profile_or_get_existing(user_id, game)
    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    if created:
        await callback.message.answer(
            i18n.t(locale, 'profile.created', game=game_label(i18n, locale, game)),
        )
        await _send_my_profiles(callback.message, user_id=user_id, locale=locale, session=session, i18n=i18n)
        return

    await callback.message.answer(
        i18n.t(locale, 'profile.exists', game=game_label(i18n, locale, profile.game)),
        reply_markup=existing_profile_keyboard(i18n, locale, profile.game),
    )


@router.callback_query(F.data.startswith('profile:update_game:'))
async def update_profile_game_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
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
    updated = await profile_service.reset_by_owner_and_game(user_id, game)

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if not updated:
        await callback.message.answer(i18n.t(locale, 'error.not_found'))
        return

    await callback.message.answer(i18n.t(locale, 'profile.reset_done'))
    await _send_my_profiles(callback.message, user_id=user_id, locale=locale, session=session, i18n=i18n)


@router.callback_query(F.data.startswith('profile:reset:'))
async def reset_profile_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    data = callback.data or ''
    profile_id_raw = data.split(':')[-1]

    try:
        profile_id = uuid.UUID(profile_id_raw)
    except ValueError:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    profile_service = ProfileService(session)
    updated = await profile_service.reset_owned_profile(user_id, profile_id)

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if not updated:
        await callback.message.answer(i18n.t(locale, 'error.not_found'))
        return

    await callback.message.answer(i18n.t(locale, 'profile.reset_done'))
    await _send_my_profiles(callback.message, user_id=user_id, locale=locale, session=session, i18n=i18n)


@router.callback_query(F.data.startswith('profile:delete:'))
async def delete_profile_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    data = callback.data or ''
    profile_id_raw = data.split(':')[-1]

    try:
        profile_id = uuid.UUID(profile_id_raw)
    except ValueError:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    profile_service = ProfileService(session)
    deleted = await profile_service.delete_owned_profile(user_id, profile_id)

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if not deleted:
        await callback.message.answer(i18n.t(locale, 'error.not_found'))
        return

    await callback.message.answer(i18n.t(locale, 'profile.deleted'))
    await _send_my_profiles(callback.message, user_id=user_id, locale=locale, session=session, i18n=i18n)
