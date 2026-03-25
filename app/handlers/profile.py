from html import escape
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    BTN_PROFILE,
    CB_PROFILE_BACK,
    CB_PROFILE_EDIT,
    CB_PROFILE_EDIT_AVATAR,
    CB_PROFILE_EDIT_CANCEL,
    CB_PROFILE_EDIT_FULL_NAME,
    CB_PROFILE_EDIT_USERNAME,
    CB_PROFILE_LANG_SET_PREFIX,
    CB_PROFILE_LANGUAGE,
    CB_PROFILE_STATS,
)
from app.database import LanguageCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.states import ProfileStates
from app.keyboards import (
    language_keyboard,
    profile_actions_keyboard,
    profile_edit_cancel_keyboard,
    profile_edit_keyboard,
    profile_language_keyboard,
    profile_stats_keyboard,
)
from app.locales import LocalizationManager
from app.services import UserService
from app.utils import format_datetime

router = Router(name='profile')

DEFAULT_AVATAR_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'default_avatar.png'
FULL_NAME_MAX_LENGTH = 70


async def _require_locale(message: Message, session: AsyncSession, i18n: LocalizationManager) -> tuple[int, str] | None:
    if message.from_user is None:
        return None

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return None

    return user_id, locale


def _username_text(raw_username: str | None, locale: str, i18n: LocalizationManager) -> str:
    if raw_username:
        return f'@{escape(raw_username)}'
    return i18n.t(locale, 'profile.username.missing')


def _full_name_text(raw_full_name: str | None, locale: str, i18n: LocalizationManager) -> str:
    if raw_full_name and raw_full_name.strip():
        return escape(raw_full_name.strip())
    return i18n.t(locale, 'profile.full_name.missing')


def _stats_values(payload: dict[str, object]) -> tuple[int, int, int, int]:
    stats = payload.get('stats')
    if stats is None:
        return 0, 0, 0, 0

    likes = int(getattr(stats, 'likes_count', 0) or 0)
    followers = int(getattr(stats, 'followers_count', 0) or 0)
    subscriptions = int(getattr(stats, 'subscriptions_count', 0) or 0)
    friends = int(getattr(stats, 'friends_count', 0) or 0)
    return likes, followers, subscriptions, friends


def _profile_text(
    *,
    i18n: LocalizationManager,
    locale: str,
    user_id: int,
    username: str,
    full_name: str,
    registered_at: str,
    profiles_count: int,
    likes: int,
    followers: int,
    subscriptions: int,
    friends: int,
) -> str:
    return i18n.t(
        locale,
        'profile.section.card',
        user_id=user_id,
        username=username,
        full_name=full_name,
        registered_at=registered_at,
        profiles_count=profiles_count,
        likes=likes,
        followers=followers,
        subscriptions=subscriptions,
        friends=friends,
    )


def _profile_stats_text(
    *,
    i18n: LocalizationManager,
    locale: str,
    user_id: int,
    username: str,
    full_name: str,
    registered_at: str,
    profiles_count: int,
    likes: int,
    followers: int,
    subscriptions: int,
    friends: int,
) -> str:
    return i18n.t(
        locale,
        'profile.section.stats',
        user_id=user_id,
        username=username,
        full_name=full_name,
        registered_at=registered_at,
        profiles_count=profiles_count,
        likes=likes,
        followers=followers,
        subscriptions=subscriptions,
        friends=friends,
    )


async def _send_profile_card(message: Message, user_id: int, locale: str, session: AsyncSession, i18n: LocalizationManager) -> None:
    payload = await UserService(session).get_profile_stats(user_id)
    user = payload.get('user')
    if user is None:
        return

    likes, followers, subscriptions, friends = _stats_values(payload)
    caption = _profile_text(
        i18n=i18n,
        locale=locale,
        user_id=user.id,
        username=_username_text(user.username, locale, i18n),
        full_name=_full_name_text(user.full_name, locale, i18n),
        registered_at=format_datetime(user.registered_at, locale).split(' ')[0],
        profiles_count=int(payload.get('profiles_count', 0) or 0),
        likes=likes,
        followers=followers,
        subscriptions=subscriptions,
        friends=friends,
    )

    avatar = user.avatar_file_id if user.avatar_file_id else FSInputFile(DEFAULT_AVATAR_PATH)
    await message.answer_photo(
        photo=avatar,
        caption=caption,
        reply_markup=profile_actions_keyboard(i18n, locale),
    )


async def _send_edit_menu(message: Message, locale: str, i18n: LocalizationManager) -> None:
    await message.answer(
        i18n.t(locale, 'profile.edit.title'),
        reply_markup=profile_edit_keyboard(i18n, locale),
    )


@router.message(F.text == BTN_PROFILE)
async def profile_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    await state.clear()
    if payload is None:
        return

    user_id, locale = payload
    await _send_profile_card(message, user_id, locale, session, i18n)


@router.callback_query(F.data == CB_PROFILE_BACK)
async def profile_back_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await _send_profile_card(callback.message, user_id, locale, session, i18n)


@router.callback_query(F.data == CB_PROFILE_STATS)
async def profile_stats_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    payload = await UserService(session).get_profile_stats(user_id)
    user = payload.get('user')
    if user is None:
        await callback.answer()
        return

    likes, followers, subscriptions, friends = _stats_values(payload)
    text = _profile_stats_text(
        i18n=i18n,
        locale=locale,
        user_id=user.id,
        username=_username_text(user.username, locale, i18n),
        full_name=_full_name_text(user.full_name, locale, i18n),
        registered_at=format_datetime(user.registered_at, locale).split(' ')[0],
        profiles_count=int(payload.get('profiles_count', 0) or 0),
        likes=likes,
        followers=followers,
        subscriptions=subscriptions,
        friends=friends,
    )

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(text, reply_markup=profile_stats_keyboard(i18n, locale))


@router.callback_query(F.data == CB_PROFILE_EDIT)
async def profile_edit_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await _send_edit_menu(callback.message, locale, i18n)


@router.callback_query(F.data == CB_PROFILE_EDIT_AVATAR)
async def profile_edit_avatar_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await state.set_state(ProfileStates.waiting_for_avatar)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            i18n.t(locale, 'profile.edit.avatar.prompt'),
            reply_markup=profile_edit_cancel_keyboard(i18n, locale),
        )


@router.callback_query(F.data == CB_PROFILE_EDIT_FULL_NAME)
async def profile_edit_full_name_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await state.set_state(ProfileStates.waiting_for_full_name)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            i18n.t(locale, 'profile.edit.full_name.prompt'),
            reply_markup=profile_edit_cancel_keyboard(i18n, locale),
        )


@router.callback_query(F.data == CB_PROFILE_EDIT_USERNAME)
async def profile_edit_username_info_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            i18n.t(locale, 'profile.edit.username.readonly'),
            reply_markup=profile_stats_keyboard(i18n, locale),
        )


@router.callback_query(F.data == CB_PROFILE_EDIT_CANCEL)
async def profile_edit_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await state.clear()
    await callback.answer()
    if isinstance(callback.message, Message):
        await _send_edit_menu(callback.message, locale, i18n)


@router.message(StateFilter(ProfileStates.waiting_for_avatar), F.photo)
async def profile_avatar_save_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    if payload is None:
        return

    user_id, locale = payload
    if not message.photo:
        await message.answer(
            i18n.t(locale, 'profile.edit.avatar.invalid'),
            reply_markup=profile_edit_cancel_keyboard(i18n, locale),
        )
        return

    file_id = message.photo[-1].file_id
    await UserService(session).set_avatar_file_id(user_id, file_id)
    await state.clear()

    await message.answer(i18n.t(locale, 'profile.edit.avatar.saved'))
    await _send_profile_card(message, user_id, locale, session, i18n)


@router.message(StateFilter(ProfileStates.waiting_for_avatar))
async def profile_avatar_invalid_handler(
    message: Message,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    if payload is None:
        return

    _, locale = payload
    await message.answer(
        i18n.t(locale, 'profile.edit.avatar.invalid'),
        reply_markup=profile_edit_cancel_keyboard(i18n, locale),
    )


@router.message(StateFilter(ProfileStates.waiting_for_full_name))
async def profile_full_name_save_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    if payload is None:
        return

    user_id, locale = payload
    full_name_raw = (message.text or '').strip()
    if not full_name_raw:
        await message.answer(
            i18n.t(locale, 'profile.edit.full_name.empty'),
            reply_markup=profile_edit_cancel_keyboard(i18n, locale),
        )
        return

    if len(full_name_raw) > FULL_NAME_MAX_LENGTH:
        await message.answer(
            i18n.t(locale, 'profile.edit.full_name.too_long', max_len=FULL_NAME_MAX_LENGTH),
            reply_markup=profile_edit_cancel_keyboard(i18n, locale),
        )
        return

    await UserService(session).set_full_name(user_id, full_name_raw)
    await state.clear()
    await message.answer(i18n.t(locale, 'profile.edit.full_name.saved'))
    await _send_profile_card(message, user_id, locale, session, i18n)


@router.callback_query(F.data == CB_PROFILE_LANGUAGE)
async def profile_language_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            i18n.t(locale, 'profile.language.choose'),
            reply_markup=profile_language_keyboard(i18n, locale),
        )


@router.callback_query(F.data.startswith(CB_PROFILE_LANG_SET_PREFIX))
async def profile_set_language_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    raw_code = (callback.data or '').split(':')[-1]
    try:
        new_language = LanguageCode(raw_code)
    except ValueError:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    await UserService(session).set_language(user_id, new_language)
    await callback.answer(i18n.t(new_language.value, 'language.changed'))

    if isinstance(callback.message, Message):
        await _send_profile_card(callback.message, user_id, new_language.value, session, i18n)
