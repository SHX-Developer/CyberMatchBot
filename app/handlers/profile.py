from html import escape
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
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


def _username_value(raw_username: str | None, locale: str, i18n: LocalizationManager) -> str:
    if raw_username:
        return f'@{escape(raw_username)}'
    return i18n.t(locale, 'profile.username.missing')


def _full_name_value(raw_full_name: str | None, locale: str, i18n: LocalizationManager) -> str:
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


def _avatar_source(user) -> str | FSInputFile:
    avatar_file_id = getattr(user, 'avatar_file_id', None)
    if avatar_file_id:
        return avatar_file_id
    return FSInputFile(DEFAULT_AVATAR_PATH)


async def _avatar_source_by_user_id(user_id: int, session: AsyncSession) -> str | FSInputFile:
    payload = await UserService(session).get_profile_stats(user_id)
    user = payload.get('user')
    if user is None:
        return FSInputFile(DEFAULT_AVATAR_PATH)
    return _avatar_source(user)


def _profile_caption(*, i18n: LocalizationManager, locale: str, payload: dict[str, object]) -> str | None:
    user = payload.get('user')
    if user is None:
        return None

    likes, followers, subscriptions, friends = _stats_values(payload)
    return i18n.t(
        locale,
        'profile.section.card',
        user_id=user.id,
        username=_username_value(user.username, locale, i18n),
        full_name=_full_name_value(user.full_name, locale, i18n),
        registered_at=format_datetime(user.registered_at, locale).split(' ')[0],
        profiles_count=int(payload.get('profiles_count', 0) or 0),
        likes=likes,
        followers=followers,
        subscriptions=subscriptions,
        friends=friends,
    )


def _stats_caption(*, i18n: LocalizationManager, locale: str, payload: dict[str, object]) -> str | None:
    user = payload.get('user')
    if user is None:
        return None

    username_title = _username_value(user.username, locale, i18n) if user.username else ''
    title = i18n.t(locale, 'profile.stats.title')
    if username_title:
        title = i18n.t(locale, 'profile.stats.title.with_username', username=username_title)

    likes, followers, subscriptions, friends = _stats_values(payload)
    return i18n.t(
        locale,
        'profile.section.stats.only',
        title=title,
        profiles_count=int(payload.get('profiles_count', 0) or 0),
        likes=likes,
        followers=followers,
        subscriptions=subscriptions,
        friends=friends,
    )


async def _remember_message(state: FSMContext, message: Message) -> None:
    await state.update_data(profile_message_chat_id=message.chat.id, profile_message_id=message.message_id)


async def _remember_prompt_message(state: FSMContext, message: Message) -> None:
    await state.update_data(prompt_message_chat_id=message.chat.id, prompt_message_id=message.message_id)


async def _message_ref(state: FSMContext) -> tuple[int, int] | None:
    data = await state.get_data()
    chat_id = data.get('profile_message_chat_id')
    message_id = data.get('profile_message_id')
    if not isinstance(chat_id, int) or not isinstance(message_id, int):
        return None
    return chat_id, message_id


async def _prompt_message_ref(state: FSMContext) -> tuple[int, int] | None:
    data = await state.get_data()
    chat_id = data.get('prompt_message_chat_id')
    message_id = data.get('prompt_message_id')
    if not isinstance(chat_id, int) or not isinstance(message_id, int):
        return None
    return chat_id, message_id


async def _delete_prompt_message(message: Message, state: FSMContext) -> None:
    ref = await _prompt_message_ref(state)
    if ref is None:
        return
    chat_id, message_id = ref
    try:
        await message.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass


async def _edit_profile_message(
    *,
    bot_message: Message,
    photo: str | FSInputFile,
    caption: str | None,
    reply_markup,
) -> None:
    media = InputMediaPhoto(
        media=photo,
        caption=caption,
        parse_mode='HTML' if caption else None,
    )
    try:
        await bot_message.edit_media(media=media, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if 'message is not modified' not in str(exc):
            raise


async def _edit_profile_message_by_ref(
    *,
    message: Message,
    state: FSMContext,
    photo: str | FSInputFile,
    caption: str | None,
    reply_markup,
) -> None:
    ref = await _message_ref(state)
    if ref is None:
        return

    chat_id, message_id = ref
    media = InputMediaPhoto(
        media=photo,
        caption=caption,
        parse_mode='HTML' if caption else None,
    )
    try:
        await message.bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=media,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as exc:
        if 'message is not modified' not in str(exc):
            raise


async def _render_profile(
    *,
    display_message: Message,
    state: FSMContext,
    user_id: int,
    locale: str,
    session: AsyncSession,
    i18n: LocalizationManager,
    use_edit: bool,
) -> None:
    payload = await UserService(session).get_profile_stats(user_id)
    caption = _profile_caption(i18n=i18n, locale=locale, payload=payload)
    if caption is None:
        return
    user = payload.get('user')
    if user is None:
        return
    photo = _avatar_source(user)

    if use_edit:
        await _edit_profile_message(
            bot_message=display_message,
            photo=photo,
            caption=caption,
            reply_markup=profile_actions_keyboard(i18n, locale),
        )
        await _remember_message(state, display_message)
        return

    sent = await display_message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=profile_actions_keyboard(i18n, locale),
    )
    await _remember_message(state, sent)


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
    await _render_profile(
        display_message=message,
        state=state,
        user_id=user_id,
        locale=locale,
        session=session,
        i18n=i18n,
        use_edit=False,
    )


@router.callback_query(F.data == CB_PROFILE_BACK)
async def profile_back_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    await _render_profile(
        display_message=callback.message,
        state=state,
        user_id=user_id,
        locale=locale,
        session=session,
        i18n=i18n,
        use_edit=True,
    )


@router.callback_query(F.data == CB_PROFILE_STATS)
async def profile_stats_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    payload = await UserService(session).get_profile_stats(user_id)
    caption = _stats_caption(i18n=i18n, locale=locale, payload=payload)
    if caption is None:
        await callback.answer()
        return

    await callback.answer()
    photo = await _avatar_source_by_user_id(user_id, session)
    await _edit_profile_message(
        bot_message=callback.message,
        photo=photo,
        caption=caption,
        reply_markup=profile_stats_keyboard(i18n, locale),
    )
    await _remember_message(state, callback.message)


@router.callback_query(F.data == CB_PROFILE_EDIT)
async def profile_edit_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    photo = await _avatar_source_by_user_id(callback.from_user.id, session)
    await _edit_profile_message(
        bot_message=callback.message,
        photo=photo,
        caption=i18n.t(locale, 'profile.edit.title'),
        reply_markup=profile_edit_keyboard(i18n, locale),
    )
    await _remember_message(state, callback.message)


@router.callback_query(F.data == CB_PROFILE_EDIT_AVATAR)
async def profile_edit_avatar_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await state.set_state(ProfileStates.waiting_for_avatar)
    await callback.answer()
    prompt = await callback.message.answer(
        i18n.t(locale, 'profile.edit.avatar.prompt'),
        reply_markup=profile_edit_cancel_keyboard(i18n, locale),
    )
    await _remember_prompt_message(state, prompt)
    await _remember_message(state, callback.message)


@router.callback_query(F.data == CB_PROFILE_EDIT_FULL_NAME)
async def profile_edit_full_name_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await state.set_state(ProfileStates.waiting_for_full_name)
    await callback.answer()
    prompt = await callback.message.answer(
        i18n.t(locale, 'profile.edit.full_name.prompt'),
        reply_markup=profile_edit_cancel_keyboard(i18n, locale),
    )
    await _remember_prompt_message(state, prompt)
    await _remember_message(state, callback.message)


@router.callback_query(F.data == CB_PROFILE_EDIT_USERNAME)
async def profile_refresh_username_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer(i18n.t(locale, 'profile.username.refreshed'))
    await _render_profile(
        display_message=callback.message,
        state=state,
        user_id=user_id,
        locale=locale,
        session=session,
        i18n=i18n,
        use_edit=True,
    )


@router.callback_query(F.data == CB_PROFILE_EDIT_CANCEL)
async def profile_edit_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


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
        await message.answer(i18n.t(locale, 'profile.edit.avatar.invalid'))
        return

    await UserService(session).set_avatar_file_id(user_id, message.photo[-1].file_id)
    await _delete_prompt_message(message, state)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await _edit_profile_message_by_ref(
        message=message,
        state=state,
        photo=await _avatar_source_by_user_id(user_id, session),
        caption=_profile_caption(
            i18n=i18n,
            locale=locale,
            payload=await UserService(session).get_profile_stats(user_id),
        ),
        reply_markup=profile_actions_keyboard(i18n, locale),
    )
    await state.clear()


@router.message(StateFilter(ProfileStates.waiting_for_avatar))
async def profile_avatar_invalid_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    if payload is None:
        return

    _, locale = payload
    await message.answer(i18n.t(locale, 'profile.edit.avatar.invalid'))


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
        await message.answer(i18n.t(locale, 'profile.edit.full_name.empty'))
        return

    if len(full_name_raw) > FULL_NAME_MAX_LENGTH:
        await message.answer(i18n.t(locale, 'profile.edit.full_name.too_long', max_len=FULL_NAME_MAX_LENGTH))
        return

    await UserService(session).set_full_name(user_id, full_name_raw)
    await _delete_prompt_message(message, state)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await _edit_profile_message_by_ref(
        message=message,
        state=state,
        photo=await _avatar_source_by_user_id(user_id, session),
        caption=_profile_caption(
            i18n=i18n,
            locale=locale,
            payload=await UserService(session).get_profile_stats(user_id),
        ),
        reply_markup=profile_actions_keyboard(i18n, locale),
    )
    await state.clear()


@router.callback_query(F.data == CB_PROFILE_LANGUAGE)
async def profile_language_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    photo = await _avatar_source_by_user_id(callback.from_user.id, session)
    await _edit_profile_message(
        bot_message=callback.message,
        photo=photo,
        caption=None,
        reply_markup=profile_language_keyboard(i18n, locale),
    )
    await _remember_message(state, callback.message)


@router.callback_query(F.data.startswith(CB_PROFILE_LANG_SET_PREFIX))
async def profile_set_language_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
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
    await _render_profile(
        display_message=callback.message,
        state=state,
        user_id=user_id,
        locale=new_language.value,
        session=session,
        i18n=i18n,
        use_edit=True,
    )
