from html import escape
import os
from pathlib import Path
import re
import tempfile
import uuid

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    BTN_PROFILE_TEXTS,
    PROFILE_IMAGE_FILE_ID,
    PROFILE_EDIT_IMAGE_FILE_ID,
    PROFILE_LANGUAGE_IMAGE_FILE_ID,
    PROFILE_LAST_ACTIVITY_IMAGE_FILE_ID,
    PROFILE_NOTIFICATIONS_IMAGE_FILE_ID,
    PROFILE_SETTINGS_IMAGE_FILE_ID,
    PROFILE_STATS_IMAGE_FILE_ID,
    CB_PROFILE_BACK,
    CB_PROFILE_EDIT,
    CB_PROFILE_EDIT_AVATAR,
    CB_PROFILE_EDIT_CANCEL,
    CB_PROFILE_EDIT_FULL_NAME,
    CB_PROFILE_EDIT_USERNAME,
    CB_PROFILE_LANG_SET_PREFIX,
    CB_PROFILE_LANGUAGE,
    CB_PROFILE_LAST_ACTIVITY,
    CB_PROFILE_LAST_ACTIVITY_DISABLE,
    CB_PROFILE_LAST_ACTIVITY_ENABLE,
    CB_PROFILE_NOTIFICATIONS,
    CB_PROFILE_SETTINGS,
    CB_PROFILE_NOTIF_LIKES,
    CB_PROFILE_NOTIF_MESSAGES,
    CB_PROFILE_NOTIF_SUBS,
    CB_PROFILE_STATS,
    CB_PROFILE_STATS_REFRESH,
)
from app.database import LanguageCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.states import ProfileStates
from app.keyboards import (
    language_keyboard,
    profile_actions_keyboard,
    profile_edit_cancel_keyboard,
    profile_edit_keyboard,
    profile_last_activity_keyboard,
    profile_language_keyboard,
    profile_notifications_keyboard,
    profile_settings_keyboard,
    profile_stats_keyboard,
)
from app.locales import LocalizationManager
from app.services import UserService
from app.utils import format_datetime

router = Router(name='profile')

DEFAULT_AVATAR_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'default_avatar.png'
ASSETS_DIR = Path(__file__).resolve().parent.parent / 'assets'
PROFILE_STATS_IMAGE_PATH = ASSETS_DIR / 'statistics.png'
PROFILE_NOTIFICATIONS_IMAGE_PATH = ASSETS_DIR / 'notifications.png'
PROFILE_LANGUAGE_IMAGE_PATH = ASSETS_DIR / 'language.png'
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
    likes_raw = payload.get('likes_count')
    followers_raw = payload.get('followers_count')
    subscriptions_raw = payload.get('subscriptions_count')
    friends_raw = payload.get('friends_count')
    if all(isinstance(value, int) for value in (likes_raw, followers_raw, subscriptions_raw, friends_raw)):
        return int(likes_raw), int(followers_raw), int(subscriptions_raw), int(friends_raw)

    stats = payload.get('stats')
    if stats is None:
        return 0, 0, 0, 0

    likes = int(getattr(stats, 'likes_count', 0) or 0)
    followers = int(getattr(stats, 'followers_count', 0) or 0)
    subscriptions = int(getattr(stats, 'subscriptions_count', 0) or 0)
    friends = int(getattr(stats, 'friends_count', 0) or 0)
    return likes, followers, subscriptions, friends


def _views_values(payload: dict[str, object]) -> tuple[int, int]:
    card_views_raw = payload.get('profile_views_count')
    profile_visits_raw = payload.get('profile_visits_count')
    if isinstance(card_views_raw, int) and isinstance(profile_visits_raw, int):
        return int(card_views_raw), int(profile_visits_raw)
    stats = payload.get('stats')
    if stats is None:
        return 0, 0
    card_views = int(getattr(stats, 'profile_views_count', 0) or 0)
    profile_visits = int(getattr(stats, 'profile_visits_count', 0) or 0)
    return card_views, profile_visits


def _avatar_source(user) -> str | FSInputFile:
    avatar_file_id = getattr(user, 'avatar_file_id', None)
    if avatar_file_id:
        return avatar_file_id
    return PROFILE_IMAGE_FILE_ID


async def _avatar_source_by_user_id(user_id: int, session: AsyncSession) -> str | FSInputFile:
    payload = await UserService(session).get_profile_stats(user_id)
    user = payload.get('user')
    if user is None:
        return PROFILE_IMAGE_FILE_ID
    return _avatar_source(user)


def _image_or_default(path: Path) -> FSInputFile:
    return FSInputFile(path if path.exists() else DEFAULT_AVATAR_PATH)


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
        profiles_count=int(payload.get('profiles_count', 0) or 0),
        likes=likes,
        followers=followers,
        subscriptions=subscriptions,
        friends=friends,
        registered_at=format_datetime(user.registered_at, locale).split(' ')[0],
    )


def _stats_caption(*, i18n: LocalizationManager, locale: str, payload: dict[str, object]) -> str | None:
    user = payload.get('user')
    if user is None:
        return None

    likes, followers, subscriptions, friends = _stats_values(payload)
    profile_views, profile_visits = _views_values(payload)
    title = i18n.t(locale, 'profile.stats.title.with_username', username=_full_name_value(user.full_name, locale, i18n))
    return i18n.t(
        locale,
        'profile.section.stats.only',
        title=title,
        profiles_count=int(payload.get('profiles_count', 0) or 0),
        likes=likes,
        followers=followers,
        subscriptions=subscriptions,
        friends=friends,
        profile_views=profile_views,
        profile_visits=profile_visits,
    )


def _build_stats_chart_image(*, payload: dict[str, object], locale: str, i18n: LocalizationManager) -> str | FSInputFile:
    os.environ.setdefault('MPLCONFIGDIR', tempfile.gettempdir())
    os.environ.setdefault('XDG_CACHE_HOME', tempfile.gettempdir())
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        return PROFILE_STATS_IMAGE_FILE_ID

    profiles_count = int(payload.get('profiles_count', 0) or 0)
    likes, followers, subscriptions, friends = _stats_values(payload)
    profile_views, profile_visits = _views_values(payload)

    def _plain_label(key: str) -> str:
        raw = i18n.t(locale, key)
        cleaned = re.sub(r'^[^\wа-яА-Я]+', '', raw).strip()
        return cleaned or raw

    labels = [
        _plain_label('label.likes'),
        _plain_label('label.followers'),
        _plain_label('label.subscriptions'),
        _plain_label('label.friends'),
        _plain_label('label.profile_views'),
        _plain_label('label.profile_visits'),
        _plain_label('label.profiles_count'),
    ]
    values = [likes, followers, subscriptions, friends, profile_views, profile_visits, profiles_count]
    palette = ['#f43f5e', '#f59e0b', '#22c55e', '#06b6d4', '#eab308', '#8b5cf6', '#3b82f6']

    fig = plt.figure(figsize=(11, 6), facecolor='#0b1220')
    grid = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0], wspace=0.2)
    ax_bars = fig.add_subplot(grid[0, 0], facecolor='#111827')
    ax_pie = fig.add_subplot(grid[0, 1], facecolor='#111827')

    positions = range(len(labels))
    ax_bars.barh(positions, values, color=palette, edgecolor='#0b1220', linewidth=1.0)
    ax_bars.set_yticks(list(positions), labels)
    ax_bars.invert_yaxis()
    ax_bars.tick_params(axis='x', colors='#e2e8f0')
    ax_bars.tick_params(axis='y', colors='#e2e8f0')
    ax_bars.grid(axis='x', linestyle='--', alpha=0.2, color='#94a3b8')
    for spine in ax_bars.spines.values():
        spine.set_color('#1f2937')
    for idx, value in enumerate(values):
        ax_bars.text(max(value, 0) + 0.2, idx, str(value), va='center', ha='left', color='#f8fafc', fontsize=10)
    ax_bars.set_title(i18n.t(locale, 'profile.stats.chart.distribution'), color='#f8fafc', fontsize=13, pad=12)

    safe_values = values if any(v > 0 for v in values) else [1 for _ in values]
    ax_pie.pie(
        safe_values,
        labels=None,
        colors=palette,
        startangle=120,
        wedgeprops={'width': 0.45, 'edgecolor': '#0b1220'},
        autopct=lambda pct: f'{pct:.0f}%' if pct >= 6 else '',
        pctdistance=0.8,
        textprops={'color': '#e2e8f0', 'fontsize': 9},
    )
    ax_pie.set_title(i18n.t(locale, 'profile.stats.chart.share'), color='#f8fafc', fontsize=13, pad=12)

    fig.suptitle(i18n.t(locale, 'profile.stats.chart.title'), color='#f8fafc', fontsize=16, fontweight='bold')
    fig.text(
        0.5,
        0.02,
        i18n.t(locale, 'profile.stats.chart.subtitle'),
        ha='center',
        color='#93c5fd',
        fontsize=10,
    )

    output_path = Path(tempfile.gettempdir()) / f'cybermate_stats_{uuid.uuid4().hex}.png'
    fig.savefig(output_path, dpi=170, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    return FSInputFile(output_path)


async def _sync_avatar_from_telegram(*, user_id: int, message: Message, session: AsyncSession) -> None:
    try:
        photos = await message.bot.get_user_profile_photos(user_id=user_id, limit=1)
    except Exception:
        return
    if not photos.photos:
        return
    avatar_file_id = photos.photos[0][-1].file_id
    await UserService(session).set_avatar_file_id(user_id, avatar_file_id)


def _message_image_file_id(message: Message) -> str | None:
    if message.photo:
        return message.photo[-1].file_id
    document = message.document
    if document is not None and (document.mime_type or '').startswith('image/'):
        return document.file_id
    return None


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
    await _sync_avatar_from_telegram(user_id=user_id, message=display_message, session=session)
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


async def _render_profile_settings(
    *,
    message: Message,
    state: FSMContext,
    locale: str,
    i18n: LocalizationManager,
) -> None:
    await _edit_profile_message(
        bot_message=message,
        photo=PROFILE_SETTINGS_IMAGE_FILE_ID,
        caption=i18n.t(locale, 'profile.settings.title'),
        reply_markup=profile_settings_keyboard(i18n, locale),
    )
    await _remember_message(state, message)


async def _render_last_activity_settings(
    *,
    message: Message,
    state: FSMContext,
    locale: str,
    i18n: LocalizationManager,
    enabled: bool,
) -> None:
    status_key = 'state.on' if enabled else 'state.off'
    caption = i18n.t(
        locale,
        'profile.last_activity.title',
        status=i18n.t(locale, status_key),
    )
    await _edit_profile_message(
        bot_message=message,
        photo=PROFILE_LAST_ACTIVITY_IMAGE_FILE_ID,
        caption=caption,
        reply_markup=profile_last_activity_keyboard(i18n, locale, enabled=enabled),
    )
    await _remember_message(state, message)


@router.message(F.text.in_(BTN_PROFILE_TEXTS))
@router.message(Command('profile'))
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

    await _sync_avatar_from_telegram(user_id=user_id, message=callback.message, session=session)
    payload = await UserService(session).get_profile_stats(user_id)
    caption = _stats_caption(i18n=i18n, locale=locale, payload=payload)
    if caption is None:
        await callback.answer()
        return

    await callback.answer()
    photo = _build_stats_chart_image(payload=payload, locale=locale, i18n=i18n)
    await _edit_profile_message(
        bot_message=callback.message,
        photo=photo,
        caption=caption,
        reply_markup=profile_stats_keyboard(i18n, locale),
    )
    await _remember_message(state, callback.message)


@router.callback_query(F.data == CB_PROFILE_STATS_REFRESH)
async def profile_stats_refresh_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    await profile_stats_handler(callback, state, session, i18n)


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
    photo = PROFILE_EDIT_IMAGE_FILE_ID
    await _edit_profile_message(
        bot_message=callback.message,
        photo=photo,
        caption=i18n.t(locale, 'profile.edit.title'),
        reply_markup=profile_edit_keyboard(i18n, locale),
    )
    await _remember_message(state, callback.message)


@router.callback_query(F.data == CB_PROFILE_SETTINGS)
async def profile_settings_handler(
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
    await _render_profile_settings(
        message=callback.message,
        state=state,
        locale=locale,
        i18n=i18n,
    )


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
        '✏️ Введи новый ник:',
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

    await callback.answer('Окей, отменил 👌', show_alert=False)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.message(StateFilter(ProfileStates.waiting_for_avatar), F.photo | F.document)
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
    file_id = _message_image_file_id(message)
    if file_id is None:
        await message.answer(i18n.t(locale, 'profile.edit.avatar.invalid'))
        return

    await UserService(session).set_avatar_file_id(user_id, file_id)
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

    normalized_full_name = full_name_raw.lower()
    await UserService(session).set_full_name(user_id, normalized_full_name)
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
    photo = PROFILE_LANGUAGE_IMAGE_FILE_ID
    await _edit_profile_message(
        bot_message=callback.message,
        photo=photo,
        caption=i18n.t(locale, 'profile.language.choose'),
        reply_markup=profile_language_keyboard(i18n, locale),
    )
    await _remember_message(state, callback.message)


@router.callback_query(F.data == CB_PROFILE_NOTIFICATIONS)
async def profile_notifications_handler(
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
    photo = PROFILE_NOTIFICATIONS_IMAGE_FILE_ID
    settings = await UserService(session).notification_settings(callback.from_user.id)
    await _edit_profile_message(
        bot_message=callback.message,
        photo=photo,
        caption=i18n.t(locale, 'profile.notifications.title'),
        reply_markup=profile_notifications_keyboard(i18n, locale, settings),
    )
    await _remember_message(state, callback.message)


@router.callback_query(F.data.in_({CB_PROFILE_NOTIF_LIKES, CB_PROFILE_NOTIF_SUBS, CB_PROFILE_NOTIF_MESSAGES}))
async def profile_notifications_toggle_handler(
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

    kind_map = {
        CB_PROFILE_NOTIF_LIKES: 'likes',
        CB_PROFILE_NOTIF_SUBS: 'subscriptions',
        CB_PROFILE_NOTIF_MESSAGES: 'messages',
    }
    kind = kind_map.get(callback.data or '')
    if kind is None:
        await callback.answer(i18n.t(locale, 'error.update_failed'), show_alert=True)
        return

    current = await UserService(session).toggle_notification(callback.from_user.id, kind)
    if current is None:
        await callback.answer(i18n.t(locale, 'error.update_failed'), show_alert=True)
        return

    await callback.answer(i18n.t(locale, 'profile.notifications.state.on' if current else 'profile.notifications.state.off'))
    settings = await UserService(session).notification_settings(callback.from_user.id)
    await _edit_profile_message(
        bot_message=callback.message,
        photo=PROFILE_NOTIFICATIONS_IMAGE_FILE_ID,
        caption=i18n.t(locale, 'profile.notifications.title'),
        reply_markup=profile_notifications_keyboard(i18n, locale, settings),
    )
    await _remember_message(state, callback.message)


@router.callback_query(F.data == CB_PROFILE_LAST_ACTIVITY)
async def profile_last_activity_handler(
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
    enabled = await UserService(session).last_activity_visible(callback.from_user.id)
    await _render_last_activity_settings(
        message=callback.message,
        state=state,
        locale=locale,
        i18n=i18n,
        enabled=enabled,
    )


@router.callback_query(F.data.in_({CB_PROFILE_LAST_ACTIVITY_ENABLE, CB_PROFILE_LAST_ACTIVITY_DISABLE}))
async def profile_last_activity_toggle_handler(
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

    enabled = (callback.data == CB_PROFILE_LAST_ACTIVITY_ENABLE)
    current = await UserService(session).set_last_activity_visible(callback.from_user.id, enabled)
    if current is None:
        await callback.answer(i18n.t(locale, 'error.update_failed'), show_alert=True)
        return

    await callback.answer(i18n.t(locale, 'profile.last_activity.updated'))
    await _render_last_activity_settings(
        message=callback.message,
        state=state,
        locale=locale,
        i18n=i18n,
        enabled=current,
    )


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
