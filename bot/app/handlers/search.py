from datetime import datetime, timezone
from html import escape
from pathlib import Path
import re
import random
from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    BTN_FIND_TEAMMATE_TEXTS,
    CB_SEARCH_BACK_MAIN,
    CB_SEARCH_CANCEL_MESSAGE,
    CB_SEARCH_CREATE_PROFILE,
    CB_SEARCH_GAME_PICK_PREFIX,
    CB_SEARCH_HIDE_NOTICE,
    CB_SEARCH_LIKE_PREFIX,
    CB_SEARCH_MESSAGE_PREFIX,
    CB_SEARCH_NEXT_PREFIX,
    CB_SEARCH_PREV_PREFIX,
    CB_SEARCH_RETRY_PREFIX,
    CB_SEARCH_SUB_PREFIX,
    CB_SEARCH_VIEW_LIKER_PREFIX,
    CB_SEARCH_VIEW_PROFILE_PREFIX,
    CB_SEARCH_USER_PROFILES_PREFIX,
    CB_SEARCH_USER_PROFILE_GAME_PREFIX,
    CB_SEARCH_BACK_TO_CARD,
    CB_SEARCH_BACK_TO_PROFILE_PREFIX,
    MAIN_MENU_IMAGE_FILE_ID,
    SEARCH_GAME_PICK_IMAGE_FILE_ID,
    MY_PROFILES_CREATE_IMAGE_FILE_ID,
)
from app.database import GameCode, MlbbLaneCode
from app.handlers.context import ensure_user_and_locale, main_menu_keyboard_with_counters
from app.handlers.states import SearchStates
from app.keyboards import (
    chat_new_message_notice_keyboard,
    search_empty_keyboard,
    search_game_pick_keyboard,
    search_hide_keyboard,
    search_like_notice_keyboard,
    search_message_cancel_keyboard,
    my_profiles_create_game_keyboard,
    search_need_profile_keyboard,
    search_profile_actions_keyboard,
    search_profile_notice_keyboard,
    search_user_profiles_games_keyboard,
    search_subscription_notice_keyboard,
)
from app.locales import LocalizationManager
from app.services import InteractionService, ProfileService, UserService
from app.services.action_logs import (
    log_like_action,
    log_message_action,
    log_mutual_like_action,
    log_subscription_action,
)
from app.utils import format_datetime

router = Router(name='search')

DEFAULT_AVATAR_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'default_avatar.png'
SEARCH_IMAGE_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'search.png'
SUPPORTED_SEARCH_GAMES = (GameCode.MLBB, GameCode.GENSHIN_IMPACT, GameCode.PUBG_MOBILE)


def _game_title(game: GameCode) -> str:
    if game == GameCode.MLBB:
        return 'Mobile Legends'
    if game == GameCode.GENSHIN_IMPACT:
        return 'Genshin Impact'
    if game == GameCode.PUBG_MOBILE:
        return 'PUBG Mobile'
    return 'Неизвестная игра'


def _genshin_region_label(code: str | None) -> str:
    mapping = {
        'ASIA': 'Азия',
        'EUROPE': 'Европа',
        'AMERICA': 'Америка',
        'TW_HK_MO': 'TW, HK, MO',
    }
    if not code:
        return 'Не указано'
    return mapping.get(code, code)


def _lane_title(raw: str | None) -> str:
    mapping = {
        MlbbLaneCode.GOLD.value: 'Линия золота',
        MlbbLaneCode.MID.value: 'Средняя линия',
        MlbbLaneCode.EXP.value: 'Линия опыта',
        MlbbLaneCode.JUNGLE.value: 'Лесник',
        MlbbLaneCode.ROAM.value: 'Роумер',
        MlbbLaneCode.ALL.value: 'На всех линиях',
    }
    if raw is None:
        return 'Не указано'
    return mapping.get(raw, 'Не указано')


def _extra_lanes_text(extra_lanes: list[str] | None) -> str:
    if not extra_lanes:
        return 'Не указано'
    return ', '.join(_lane_title(item) for item in extra_lanes)


def _format_rank(rank: str | None, mythic_stars: int | None) -> str:
    value = rank or 'Не указано'
    if rank == 'Мифический' and isinstance(mythic_stars, int) and mythic_stars > 0:
        return f'{value} ({mythic_stars} ⭐)'
    return value


def _full_name(user) -> str:
    if user.full_name and user.full_name.strip():
        return user.full_name.strip()
    parts = [part for part in [user.first_name, user.last_name] if part]
    if parts:
        return ' '.join(parts)
    return 'Не указано'


def _username(user) -> str:
    return f'@{user.username}' if user.username else 'Не указан'


def _gender_label(user) -> str:
    raw = getattr(getattr(user, 'gender', None), 'value', getattr(user, 'gender', None))
    mapping = {
        'male': 'Мужской',
        'female': 'Женский',
        'not_specified': 'Не указано',
    }
    return mapping.get(str(raw), 'Не указано')


def _public_game_id(raw_value: str | None) -> str:
    if not raw_value or not raw_value.strip():
        return 'Не указано'
    value = raw_value.strip()
    if '(' in value:
        base = value.split('(', 1)[0].strip()
        if base:
            return base
    match = re.match(r'^(\d+)', value)
    if match is not None:
        return match.group(1)
    return value


def _activity_status(last_seen_at: datetime | None, locale: str) -> str:
    is_en = locale.startswith('en')
    is_uz = locale.startswith('uz')
    if last_seen_at is None:
        if is_en:
            return '🕒 Recently active'
        if is_uz:
            return "🕒 Yaqinda faol bo'lgan"
        return '🕒 Был недавно'
    seen_at = last_seen_at if last_seen_at.tzinfo is not None else last_seen_at.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - seen_at
    if delta.total_seconds() <= 180:
        if is_en:
            return '🟢 Online'
        if is_uz:
            return '🟢 Onlayn'
        return '🟢 Онлайн'
    total_minutes = max(1, int(delta.total_seconds() // 60))
    if total_minutes < 60:
        if is_en:
            return f'🕒 Active {total_minutes} min ago'
        if is_uz:
            return f"🕒 {total_minutes} daqiqa oldin faol"
        return f'🕒 Был {total_minutes} мин назад'
    total_hours = total_minutes // 60
    if total_hours < 24:
        if is_en:
            return f'🕒 Active {total_hours} h ago'
        if is_uz:
            return f"🕒 {total_hours} soat oldin faol"
        return f'🕒 Был {total_hours} ч назад'
    total_days = total_hours // 24
    if is_en:
        return f'🕒 Active {total_days} d ago'
    if is_uz:
        return f"🕒 {total_days} kun oldin faol"
    return f'🕒 Был {total_days} дн назад'


def _search_card_text(profile, user, *, locale: str) -> str:
    title = escape(_game_title(profile.game))
    show_last_activity = bool(getattr(user, 'show_last_activity', True))
    activity_status = _activity_status(getattr(user, 'last_seen_at', None), locale) if show_last_activity else (
        'Recently active' if locale.startswith('en') else ("Yaqinda faol bo'lgan" if locale.startswith('uz') else 'Был(а) недавно')
    )
    if profile.game == GameCode.MLBB:
        return (
            f"<b>🎮 {title}: {escape(_full_name(user))}</b>\n\n"
            f"<b>🆔 ID:</b> <code>{escape(_public_game_id(profile.game_player_id))}</code>\n"
            f"<b>🌍 Регион:</b> {escape(profile.play_time or 'Не указано')}\n\n"
            f"<b>🎖 Ранг:</b> {escape(_format_rank(profile.rank, profile.mythic_stars))}\n"
            f"<b>🛡 Основная линия:</b> {escape(_lane_title(profile.main_lane.value if profile.main_lane else None))}\n"
            f"<b>🎯 Доп. линии:</b> {escape(_extra_lanes_text(profile.extra_lanes))}\n\n"
            f"<b>📝 О себе:</b> {escape(profile.description or 'Не указано')}\n\n"
            f"{activity_status}"
        )
    if profile.game == GameCode.GENSHIN_IMPACT:
        return (
            f"<b>🎮 {title}: {escape(_full_name(user))}</b>\n\n"
            f"<b>🆔 UID:</b> <code>{escape(_public_game_id(profile.game_player_id))}</code>\n"
            f"<b>🌍 Регион:</b> {escape(_genshin_region_label(profile.play_time))}\n"
            f"<b>⭐ Уровень приключения:</b> {escape(profile.rank or 'Не указано')}\n\n"
            f"<b>📝 О себе:</b> {escape(profile.description or 'Не указано')}\n\n"
            f"{activity_status}"
        )
    if profile.game == GameCode.PUBG_MOBILE:
        return (
            f"<b>🎮 {title}: {escape(_full_name(user))}</b>\n\n"
            f"<b>🆔 UID:</b> <code>{escape(_public_game_id(profile.game_player_id))}</code>\n"
            f"<b>🎖 Ранг:</b> {escape(profile.rank or 'Не указано')}\n\n"
            f"<b>📝 О себе:</b> {escape(profile.description or 'Не указано')}\n\n"
            f"{activity_status}"
        )
    return (
        f"<b>🎮 {title}: {escape(_full_name(user))}</b>\n\n"
        f"<b>🆔 ID:</b> <code>{escape(_public_game_id(profile.game_player_id))}</code>\n"
        f"<b>📝 О себе:</b> {escape(profile.description or 'Не указано')}\n\n"
        f"{activity_status}"
    )


def _profile_text(payload: dict[str, object], *, locale: str) -> str:
    user = payload.get('user')
    if user is None:
        return '<b>Профиль недоступен</b>'
    likes_raw = payload.get('likes_count')
    followers_raw = payload.get('followers_count')
    subscriptions_raw = payload.get('subscriptions_count')
    friends_raw = payload.get('friends_count')
    if all(isinstance(value, int) for value in (likes_raw, followers_raw, subscriptions_raw, friends_raw)):
        likes = int(likes_raw)
        followers = int(followers_raw)
        subscriptions = int(subscriptions_raw)
        friends = int(friends_raw)
    else:
        stats = payload.get('stats')
        likes = int(getattr(stats, 'likes_count', 0) or 0) if stats is not None else 0
        followers = int(getattr(stats, 'followers_count', 0) or 0) if stats is not None else 0
        subscriptions = int(getattr(stats, 'subscriptions_count', 0) or 0) if stats is not None else 0
        friends = int(getattr(stats, 'friends_count', 0) or 0) if stats is not None else 0
    return (
        f"<b>👤 {escape(_full_name(user))}</b>\n\n"
        f"<b>⚧ Пол:</b> {escape(_gender_label(user))}\n"
        f"<b>❤️ Лайки:</b> {likes}\n"
        f"<b>👥 Подписчики:</b> {followers}\n"
        f"<b>⭐ Подписки:</b> {subscriptions}\n"
        f"<b>🤝 Друзья:</b> {friends}\n\n"
        f"<b>📅 Дата регистрации:</b> {format_datetime(user.registered_at, locale).split(' ')[0]}"
    )


def _game_from_raw(raw: str) -> GameCode | None:
    try:
        game = GameCode(raw)
    except ValueError:
        return None
    if game not in SUPPORTED_SEARCH_GAMES:
        return None
    return game


async def _send_or_edit_profile_card(
    *,
    message: Message,
    caption: str,
    reply_markup,
    photo_file_id: str | None,
) -> Message:
    media = InputMediaPhoto(
        media=photo_file_id or FSInputFile(DEFAULT_AVATAR_PATH),
        caption=caption,
        parse_mode='HTML',
    )
    try:
        await message.edit_media(media=media, reply_markup=reply_markup)
        return message
    except TelegramBadRequest:
        sent = await message.answer_photo(
            photo=photo_file_id or FSInputFile(DEFAULT_AVATAR_PATH),
            caption=caption,
            parse_mode='HTML',
            reply_markup=reply_markup,
        )
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        return sent


async def _show_next_profile(
    *,
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
    locale: str,
    user_id: int,
    game: GameCode,
    reset_cycle: bool = False,
) -> None:
    profile_service = ProfileService(session)
    interaction_service = InteractionService(session)
    data = await state.get_data()
    history_raw = data.get('search_history_profile_ids')
    history: list[str] = [item for item in history_raw if isinstance(item, str)] if isinstance(history_raw, list) else []
    if reset_cycle:
        history = []
    else:
        current_profile_id = data.get('search_current_profile_id')
        if isinstance(current_profile_id, str):
            if not history or history[-1] != current_profile_id:
                history.append(current_profile_id)

    found = await profile_service.search_profiles(user_id, game)
    if not found:
        try:
            await message.edit_text(
                i18n.t(locale, 'search.empty.inline'),
                reply_markup=search_empty_keyboard(i18n=i18n, locale=locale, game=game),
            )
        except TelegramBadRequest:
            await message.answer(
                i18n.t(locale, 'search.empty.inline'),
                reply_markup=search_empty_keyboard(i18n=i18n, locale=locale, game=game),
            )
        return

    last_profile_id = None if reset_cycle else data.get('search_last_profile_id')
    pool = found
    if isinstance(last_profile_id, str):
        filtered = [item for item in found if str(item[0].id) != last_profile_id]
        if filtered:
            pool = filtered
        elif len(found) == 1:
            try:
                await message.edit_text(
                    i18n.t(locale, 'search.empty.inline'),
                    reply_markup=search_empty_keyboard(i18n=i18n, locale=locale, game=game),
                )
            except TelegramBadRequest:
                await message.answer(
                    i18n.t(locale, 'search.empty.inline'),
                    reply_markup=search_empty_keyboard(i18n=i18n, locale=locale, game=game),
                )
            return

    profile, owner = random.choice(pool)
    if int(owner.id) != user_id:
        await UserService(session).increment_profile_views_count(int(owner.id))
    subscribed = await interaction_service.is_subscribed(user_id, owner.id)
    liked = await interaction_service.has_like(user_id, owner.id, game)
    sent = await _send_or_edit_profile_card(
        message=message,
        caption=_search_card_text(profile, owner, locale=locale),
        reply_markup=search_profile_actions_keyboard(
            i18n=i18n,
            locale=locale,
            target_user_id=owner.id,
            game=game,
            subscribed=subscribed,
            liked=liked,
            include_previous=bool(history),
        ),
        photo_file_id=profile.profile_image_file_id,
    )
    await state.update_data(
        search_game=game.value,
        search_last_profile_id=str(profile.id),
        search_current_profile_id=str(profile.id),
        search_current_target_user_id=owner.id,
        search_card_chat_id=sent.chat.id,
        search_card_message_id=sent.message_id,
        search_view_mode='game_card',
        search_history_profile_ids=history,
    )


@router.message(F.text.in_(BTN_FIND_TEAMMATE_TEXTS))
@router.message(Command('search'))
async def find_teammate_entry(
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
        await message.answer(i18n.t(i18n.default_locale, 'language.select'))
        return

    await message.answer_photo(
        photo=SEARCH_GAME_PICK_IMAGE_FILE_ID,
        caption=i18n.t(locale, 'game.choose.search'),
        reply_markup=search_game_pick_keyboard(i18n, locale),
    )


@router.callback_query(F.data == CB_SEARCH_CREATE_PROFILE)
async def search_create_profile_hint(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    await callback.answer()
    await _send_or_edit_profile_card(
        message=callback.message,
        caption=i18n.t(locale, 'game.choose.create'),
        reply_markup=my_profiles_create_game_keyboard(
            games=[GameCode.MLBB, GameCode.GENSHIN_IMPACT, GameCode.PUBG_MOBILE]
        ),
        photo_file_id=MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )


@router.callback_query(F.data == CB_SEARCH_BACK_MAIN)
async def search_back_to_main(callback: CallbackQuery, state: FSMContext, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    await state.clear()
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.message.answer_photo(
        photo=MAIN_MENU_IMAGE_FILE_ID,
        caption=i18n.t(locale, 'start.welcome'),
        parse_mode='HTML',
        reply_markup=await main_menu_keyboard_with_counters(
            user_id=user_id,
            locale=locale,
            session=session,
            i18n=i18n,
        ),
    )


@router.callback_query(F.data.startswith(CB_SEARCH_GAME_PICK_PREFIX))
async def search_game_pick(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    raw = (callback.data or '').replace(CB_SEARCH_GAME_PICK_PREFIX, '', 1)
    game = _game_from_raw(raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'search.alert.game_unavailable'), show_alert=True)
        return
    if await ProfileService(session).get_profile_for_game(user_id, game) is None:
        await callback.answer(i18n.t(locale, 'search.alert.profile_required'), show_alert=True)
        await _send_or_edit_profile_card(
            message=callback.message,
            caption=i18n.t(locale, 'search.need_profile.for_game', game=escape(_game_title(game))),
            reply_markup=my_profiles_create_game_keyboard(games=[game]),
            photo_file_id=MY_PROFILES_CREATE_IMAGE_FILE_ID,
        )
        return
    await callback.answer()
    await _show_next_profile(
        message=callback.message,
        state=state,
        session=session,
        i18n=i18n,
        locale=locale,
        user_id=user_id,
        game=game,
        reset_cycle=True,
    )


@router.callback_query(F.data.startswith(CB_SEARCH_NEXT_PREFIX))
async def search_next_profile(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    raw = (callback.data or '').replace(CB_SEARCH_NEXT_PREFIX, '', 1)
    game = _game_from_raw(raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'search.alert.game_unavailable'), show_alert=True)
        return
    await callback.answer()
    await _show_next_profile(
        message=callback.message,
        state=state,
        session=session,
        i18n=i18n,
        locale=locale,
        user_id=user_id,
        game=game,
    )


@router.callback_query(F.data.startswith(CB_SEARCH_PREV_PREFIX))
async def search_prev_profile(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    raw = (callback.data or '').replace(CB_SEARCH_PREV_PREFIX, '', 1)
    game = _game_from_raw(raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'search.alert.game_unavailable'), show_alert=True)
        return

    data = await state.get_data()
    history_raw = data.get('search_history_profile_ids')
    history: list[str] = [item for item in history_raw if isinstance(item, str)] if isinstance(history_raw, list) else []
    if not history:
        await callback.answer('Предыдущих анкет пока нет', show_alert=False)
        return

    profile_service = ProfileService(session)
    interaction_service = InteractionService(session)
    found = await profile_service.search_profiles(user_id, game)
    found_map = {str(profile.id): (profile, owner) for profile, owner in found}

    selected_profile = None
    selected_owner = None
    while history:
        profile_id = history.pop()
        pair = found_map.get(profile_id)
        if pair is None:
            continue
        profile, owner = pair
        selected_profile = profile
        selected_owner = owner
        break

    if selected_profile is None or selected_owner is None:
        await state.update_data(search_history_profile_ids=[])
        await callback.answer('Эта анкета уже недоступна', show_alert=False)
        return

    if int(selected_owner.id) != user_id:
        await UserService(session).increment_profile_views_count(int(selected_owner.id))
    selected_subscribed = await interaction_service.is_subscribed(user_id, selected_owner.id)
    selected_liked = await interaction_service.has_like(user_id, selected_owner.id, game)
    await callback.answer()
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_search_card_text(selected_profile, selected_owner, locale=locale),
        reply_markup=search_profile_actions_keyboard(
            i18n=i18n,
            locale=locale,
            target_user_id=selected_owner.id,
            game=game,
            subscribed=selected_subscribed,
            liked=selected_liked,
            include_previous=bool(history),
        ),
        photo_file_id=selected_profile.profile_image_file_id,
    )
    await state.update_data(
        search_game=game.value,
        search_last_profile_id=str(selected_profile.id),
        search_current_profile_id=str(selected_profile.id),
        search_current_target_user_id=selected_owner.id,
        search_card_chat_id=sent.chat.id,
        search_card_message_id=sent.message_id,
        search_view_mode='game_card',
        search_history_profile_ids=history,
    )


@router.callback_query(F.data.startswith(CB_SEARCH_RETRY_PREFIX))
async def search_retry(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    raw = (callback.data or '').replace(CB_SEARCH_RETRY_PREFIX, '', 1)
    game = _game_from_raw(raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'search.alert.game_unavailable'), show_alert=True)
        return
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await _show_next_profile(
        message=callback.message,
        state=state,
        session=session,
        i18n=i18n,
        locale=locale,
        user_id=user_id,
        game=game,
        reset_cycle=True,
    )


@router.callback_query(F.data.startswith(CB_SEARCH_LIKE_PREFIX))
async def search_like(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return
    from_user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    payload = (callback.data or '').replace(CB_SEARCH_LIKE_PREFIX, '', 1)
    try:
        target_raw, game_raw = payload.split(':', 1)
        to_user_id = int(target_raw)
    except (ValueError, TypeError):
        await callback.answer('Не понял действие, попробуй ещё', show_alert=True)
        return
    game = _game_from_raw(game_raw)
    if game is None or to_user_id == from_user_id:
        await callback.answer('Это действие сейчас недоступно', show_alert=True)
        return

    interactions = InteractionService(session)
    added = await interactions.add_like(from_user_id, to_user_id, game)
    if not added:
        await callback.answer('⚠️ Ты уже лайкал этого игрока', show_alert=False)
        return

    await callback.answer('❤️ Лайк отправлен', show_alert=False)
    await log_like_action(
        bot=callback.bot,
        session=session,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        game=game,
    )
    to_user_settings = await UserService(session).notification_settings(to_user_id)
    if to_user_settings.get('likes', True):
        from_user = await UserService(session).get_user(from_user_id)
        from_name = escape(_full_name(from_user)) if from_user else 'Пользователь'
        await callback.bot.send_message(
            to_user_id,
            f'❤️ Твоя анкета понравилась {from_name}',
            parse_mode='HTML',
            reply_markup=search_like_notice_keyboard(i18n=i18n, locale=locale, liker_user_id=from_user_id, game=game),
        )

    if await interactions.is_mutual_like(from_user_id, to_user_id, game):
        await log_mutual_like_action(
            bot=callback.bot,
            session=session,
            user_a_id=from_user_id,
            user_b_id=to_user_id,
            game=game,
        )
        users = UserService(session)
        first = await users.get_user(from_user_id)
        second = await users.get_user(to_user_id)
        if first and second:
            for receiver, other in ((from_user_id, second), (to_user_id, first)):
                receiver_settings = await users.notification_settings(receiver)
                if not receiver_settings.get('likes', True):
                    continue
                text = "🔥 Взаимный лайк!\n\nПохоже, это мэтч 💥"
                if other.username:
                    text += f"\n🔗 @{other.username}"
                    builder = InlineKeyboardBuilder()
                    builder.button(text='💬 Перейти в ЛС', url=f'https://t.me/{other.username}')
                    builder.button(text='💤 Скрыть сообщение', callback_data=CB_SEARCH_HIDE_NOTICE)
                    builder.adjust(1)
                    keyboard = builder.as_markup()
                else:
                    text += '\n🔗 Юзернейм не указан'
                    builder = InlineKeyboardBuilder()
                    builder.button(text='Написать в боте', callback_data=f'{CB_SEARCH_MESSAGE_PREFIX}{other.id}')
                    builder.button(text='💤 Скрыть сообщение', callback_data=CB_SEARCH_HIDE_NOTICE)
                    builder.adjust(1)
                    keyboard = builder.as_markup()
                await callback.bot.send_message(receiver, text, reply_markup=keyboard)

    if isinstance(callback.message, Message):
        data = await state.get_data()
        current_target = data.get('search_current_target_user_id')
        history_raw = data.get('search_history_profile_ids')
        history = [item for item in history_raw if isinstance(item, str)] if isinstance(history_raw, list) else []
        game_raw = data.get('search_game')
        current_game = _game_from_raw(game_raw) if isinstance(game_raw, str) else None
        if isinstance(current_target, int) and current_target == to_user_id and current_game == game:
            subscribed = await interactions.is_subscribed(from_user_id, to_user_id)
            await callback.message.edit_reply_markup(
                reply_markup=search_profile_actions_keyboard(
                    i18n=i18n,
                    locale=locale,
                    target_user_id=to_user_id,
                    game=game,
                    subscribed=subscribed,
                    liked=True,
                    include_previous=bool(history),
                )
            )


@router.callback_query(F.data.startswith(CB_SEARCH_VIEW_LIKER_PREFIX))
async def search_view_liker(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    payload = (callback.data or '').replace(CB_SEARCH_VIEW_LIKER_PREFIX, '', 1)
    try:
        liker_raw, game_raw = payload.split(':', 1)
        liker_id = int(liker_raw)
    except (TypeError, ValueError):
        await callback.answer('Ошибка действия', show_alert=True)
        return
    game = _game_from_raw(game_raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'search.alert.game_unavailable'), show_alert=True)
        return

    profile = await ProfileService(session).get_profile_for_game(liker_id, game)
    user = await UserService(session).get_user(liker_id)
    if profile is None or user is None:
        await callback.answer('Эта анкета больше недоступна.', show_alert=True)
        return

    if liker_id != user_id:
        await UserService(session).increment_profile_views_count(liker_id)
    interactions = InteractionService(session)
    subscribed = await interactions.is_subscribed(user_id, liker_id)
    liked = await interactions.has_like(user_id, liker_id, game)
    history_raw = (await state.get_data()).get('search_history_profile_ids')
    history = [item for item in history_raw if isinstance(item, str)] if isinstance(history_raw, list) else []
    await callback.answer()
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_search_card_text(profile, user, locale=locale),
        reply_markup=search_profile_actions_keyboard(
            i18n=i18n,
            locale=locale,
            target_user_id=liker_id,
            game=game,
            subscribed=subscribed,
            liked=liked,
            include_next=True,
            include_hide=False,
            include_previous=bool(history),
        ),
        photo_file_id=profile.profile_image_file_id,
    )
    await state.update_data(
        search_game=game.value,
        search_current_profile_id=str(profile.id),
        search_current_target_user_id=liker_id,
        search_card_chat_id=sent.chat.id,
        search_card_message_id=sent.message_id,
    )
    await state.update_data(search_view_mode='game_card')


@router.callback_query(F.data.startswith(CB_SEARCH_SUB_PREFIX))
async def search_toggle_sub(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    follower_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    target_raw = (callback.data or '').replace(CB_SEARCH_SUB_PREFIX, '', 1)
    try:
        target_id = int(target_raw)
    except ValueError:
        await callback.answer('Не понял действие, попробуй ещё', show_alert=True)
        return
    if target_id == follower_id:
        await callback.answer('На себя подписаться нельзя', show_alert=True)
        return

    interactions = InteractionService(session)
    subscribed_now = await interactions.toggle_subscription(follower_id, target_id)
    await callback.answer('Подписка активна ⭐' if subscribed_now else 'Подписка отключена')
    await log_subscription_action(
        bot=callback.bot,
        session=session,
        follower_user_id=follower_id,
        followed_user_id=target_id,
        subscribed_now=subscribed_now,
    )

    data = await state.get_data()
    current_target = data.get('search_current_target_user_id')
    history_raw = data.get('search_history_profile_ids')
    history = [item for item in history_raw if isinstance(item, str)] if isinstance(history_raw, list) else []
    game_raw = data.get('search_game')
    game = _game_from_raw(game_raw) if isinstance(game_raw, str) else GameCode.MLBB
    view_mode = data.get('search_view_mode')
    viewed_profile_user_id = data.get('search_profile_view_user_id')
    profile_view_source = data.get('search_profile_view_source')
    profile_has_back = bool(data.get('search_profile_has_back'))

    if view_mode == 'user_profile' and isinstance(viewed_profile_user_id, int) and viewed_profile_user_id == target_id:
        await _render_user_profile_view(
            callback=callback,
            state=state,
            session=session,
            viewer_id=follower_id,
            target_id=target_id,
            i18n=i18n,
            locale=locale,
            from_message_notice=profile_view_source == 'message_notice',
            from_activity=profile_view_source == 'activity',
            include_back_to_card=profile_has_back,
        )
    elif isinstance(current_target, int) and current_target == target_id:
        await callback.message.edit_reply_markup(
            reply_markup=search_profile_actions_keyboard(
                i18n=i18n,
                locale=locale,
                target_user_id=target_id,
                game=game,
                subscribed=subscribed_now,
                liked=await interactions.has_like(follower_id, target_id, game),
                include_previous=bool(history),
            )
        )
    else:
        await callback.message.edit_reply_markup(
            reply_markup=search_profile_notice_keyboard(
                i18n=i18n,
                locale=locale,
                user_id=target_id,
                subscribed=subscribed_now,
                game=game,
            )
        )

    if subscribed_now:
        users = UserService(session)
        follower = await users.get_user(follower_id)
        follower_name = escape(_full_name(follower)) if follower else 'Пользователь'
        target_settings = await users.notification_settings(target_id)
        if target_settings.get('subscriptions', True):
            await callback.bot.send_message(
                target_id,
                f'⭐ На тебя подписался {follower_name}',
                parse_mode='HTML',
                reply_markup=search_subscription_notice_keyboard(i18n=i18n, locale=locale, user_id=follower_id),
            )


@router.callback_query(F.data.startswith(CB_SEARCH_MESSAGE_PREFIX))
async def search_start_message(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    target_raw = (callback.data or '').replace(CB_SEARCH_MESSAGE_PREFIX, '', 1)
    try:
        target_id = int(target_raw)
    except ValueError:
        await callback.answer('Не понял действие, попробуй ещё', show_alert=True)
        return
    if target_id == user_id:
        await callback.answer('Себе написать нельзя', show_alert=True)
        return

    await state.set_state(SearchStates.waiting_for_message_text)
    await state.update_data(search_message_target_user_id=target_id)
    await callback.answer()
    prompt = await callback.message.answer(
        '💬 Введи сообщение для отправки игроку.',
        reply_markup=search_message_cancel_keyboard(i18n, locale),
    )
    await state.update_data(search_message_prompt_chat_id=prompt.chat.id, search_message_prompt_message_id=prompt.message_id)


@router.callback_query(F.data == CB_SEARCH_CANCEL_MESSAGE)
async def search_cancel_message(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.answer('Окей, отменил 👌', show_alert=False)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.message(StateFilter(SearchStates.waiting_for_message_text))
async def search_send_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return
    from_user_id, locale = await ensure_user_and_locale(message.from_user, session)
    locale = locale or i18n.default_locale
    data = await state.get_data()
    target_id = data.get('search_message_target_user_id')
    if not isinstance(target_id, int):
        await state.clear()
        await message.answer('Не получилось отправить. Попробуй ещё раз.')
        return
    text = (message.text or '').strip()
    if not text:
        await message.answer(
            'Введи текст сообщения или нажми «❌ Отменить».',
            reply_markup=search_message_cancel_keyboard(i18n, locale),
        )
        return
    if len(text) > 1000:
        await message.answer(
            'Слишком длинно. Максимум 1000 символов.',
            reply_markup=search_message_cancel_keyboard(i18n, locale),
        )
        return

    prompt_chat_id = data.get('search_message_prompt_chat_id')
    prompt_message_id = data.get('search_message_prompt_message_id')
    if isinstance(prompt_chat_id, int) and isinstance(prompt_message_id, int):
        try:
            await message.bot.delete_message(chat_id=prompt_chat_id, message_id=prompt_message_id)
        except TelegramBadRequest:
            pass

    interactions = InteractionService(session)
    try:
        message_entity = await interactions.create_message(from_user_id, target_id, text)
    except ValueError:
        await message.answer(
            'Не удалось отправить сообщение. Попробуй снова.',
            reply_markup=search_message_cancel_keyboard(i18n, locale),
        )
        return
    await log_message_action(
        bot=message.bot,
        session=session,
        from_user_id=from_user_id,
        to_user_id=target_id,
        text=text,
    )
    users = UserService(session)
    sender = await users.get_user(from_user_id)
    sender_name = 'Пользователь'
    if sender is not None:
        sender_name = sender.username or _full_name(sender)
    target_settings = await users.notification_settings(target_id)
    if target_settings.get('messages', True):
        target_user = await users.get_user(target_id)
        target_locale = getattr(getattr(target_user, 'language', None), 'value', None) or locale
        try:
            await message.bot.send_message(
                target_id,
                i18n.t(target_locale, 'chat.notify.new_in_chat', nickname=escape(sender_name)),
                parse_mode='HTML',
                reply_markup=chat_new_message_notice_keyboard(
                    i18n=i18n,
                    locale=target_locale,
                    chat_id=int(message_entity.chat_id),
                    user_id=from_user_id,
                ),
            )
        except Exception:
            pass
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await state.clear()
    await message.bot.send_message(chat_id=message.chat.id, text=
        f"<b>✅ Сообщение отправлено.</b>\n\n💬 <b>Текст:</b>\n<code>{escape(text)}</code>",
        parse_mode='HTML',
        reply_markup=search_hide_keyboard(i18n, locale),
    )


@router.callback_query(F.data.startswith(CB_SEARCH_VIEW_PROFILE_PREFIX))
async def search_view_profile(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    viewer_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    raw = (callback.data or '').replace(CB_SEARCH_VIEW_PROFILE_PREFIX, '', 1)
    from_message_notice = False
    from_activity = False
    if ':' in raw:
        target_raw, source_raw = raw.split(':', 1)
        raw = target_raw
        from_message_notice = source_raw == 'msg'
        from_activity = source_raw == 'activity'
    normalized = raw.strip()
    try:
        target_id = int(normalized)
    except ValueError:
        await callback.answer('Ошибка действия', show_alert=True)
        return
    target = await UserService(session).get_user(target_id)
    if target is None:
        await callback.answer('Профиль недоступен', show_alert=True)
        return
    if target_id != viewer_id:
        await UserService(session).increment_profile_visits_count(target_id)
    subscribed = await InteractionService(session).is_subscribed(viewer_id, target_id)
    payload = await UserService(session).get_profile_stats(target_id)
    state_data = await state.get_data()
    current_target = state_data.get('search_current_target_user_id')
    game_raw = state_data.get('search_game')
    has_back_to_card = (
        isinstance(current_target, int)
        and isinstance(game_raw, str)
        and _game_from_raw(game_raw) is not None
    )
    await callback.answer()
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_profile_text(payload, locale=locale),
        reply_markup=search_profile_notice_keyboard(
            i18n=i18n,
            locale=locale,
            user_id=target_id,
            subscribed=subscribed,
            game=GameCode.MLBB,
            include_back_to_card=(not from_message_notice) and (not from_activity) and has_back_to_card,
            include_back_to_activity=from_activity,
            include_hide_notice=False,
        ),
        photo_file_id=target.avatar_file_id,
    )
    await state.update_data(
        search_view_mode='user_profile',
        search_profile_view_user_id=target_id,
        search_profile_view_source='message_notice' if from_message_notice else ('activity' if from_activity else 'default'),
        search_profile_has_back=has_back_to_card,
        search_card_chat_id=sent.chat.id,
        search_card_message_id=sent.message_id,
    )


@router.callback_query(F.data.startswith(CB_SEARCH_USER_PROFILES_PREFIX))
async def search_user_profiles_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    _, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    raw = (callback.data or '').replace(CB_SEARCH_USER_PROFILES_PREFIX, '', 1)
    try:
        target_id = int(raw)
    except ValueError:
        await callback.answer('Ошибка действия', show_alert=True)
        return

    profiles_by_game = await ProfileService(session).get_profiles_indexed_by_game(target_id)
    games = list(profiles_by_game.keys())
    if not games:
        await callback.answer('У пользователя нет игровых анкет', show_alert=True)
        return

    await callback.answer()
    await _send_or_edit_profile_card(
        message=callback.message,
        caption='<b>🎮 Игровые анкеты игрока</b>\n\nВыбери игру:',
        reply_markup=search_user_profiles_games_keyboard(i18n=i18n, locale=locale, user_id=target_id, games=games),
        photo_file_id=MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )


@router.callback_query(F.data.startswith(CB_SEARCH_USER_PROFILE_GAME_PREFIX))
async def search_user_profile_game(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    viewer_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    payload = (callback.data or '').replace(CB_SEARCH_USER_PROFILE_GAME_PREFIX, '', 1)
    try:
        target_raw, game_raw = payload.split(':', 1)
        target_id = int(target_raw)
    except (TypeError, ValueError):
        await callback.answer('Ошибка действия', show_alert=True)
        return

    game = _game_from_raw(game_raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'search.alert.game_unavailable'), show_alert=True)
        return

    profile = await ProfileService(session).get_profile_for_game(target_id, game)
    user = await UserService(session).get_user(target_id)
    if profile is None or user is None:
        await callback.answer('Эта анкета больше недоступна.', show_alert=True)
        return

    if target_id != viewer_id:
        await UserService(session).increment_profile_views_count(target_id)
    interactions = InteractionService(session)
    subscribed = await interactions.is_subscribed(viewer_id, target_id)
    liked = await interactions.has_like(viewer_id, target_id, game)
    history_raw = (await state.get_data()).get('search_history_profile_ids')
    history = [item for item in history_raw if isinstance(item, str)] if isinstance(history_raw, list) else []
    await callback.answer()
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_search_card_text(profile, user, locale=locale),
        reply_markup=search_profile_actions_keyboard(
            i18n=i18n,
            locale=locale,
            target_user_id=target_id,
            game=game,
            subscribed=subscribed,
            liked=liked,
            include_next=True,
            include_hide=False,
            include_previous=bool(history),
        ),
        photo_file_id=profile.profile_image_file_id,
    )
    await state.update_data(
        search_game=game.value,
        search_current_profile_id=str(profile.id),
        search_current_target_user_id=target_id,
        search_card_chat_id=sent.chat.id,
        search_card_message_id=sent.message_id,
        search_view_mode='game_card',
    )


async def _render_current_search_card(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> bool:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return False
    viewer_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    data = await state.get_data()
    target_id = data.get('search_current_target_user_id')
    game_raw = data.get('search_game')
    history_raw = data.get('search_history_profile_ids')
    history = [item for item in history_raw if isinstance(item, str)] if isinstance(history_raw, list) else []
    if not isinstance(target_id, int) or not isinstance(game_raw, str):
        return False

    game = _game_from_raw(game_raw)
    if game is None:
        return False

    profile = await ProfileService(session).get_profile_for_game(target_id, game)
    user = await UserService(session).get_user(target_id)
    if profile is None or user is None:
        return False

    if target_id != viewer_id:
        await UserService(session).increment_profile_views_count(target_id)
    subscribed = await InteractionService(session).is_subscribed(viewer_id, target_id)
    liked = await InteractionService(session).has_like(viewer_id, target_id, game)
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_search_card_text(profile, user, locale=locale),
        reply_markup=search_profile_actions_keyboard(
            i18n=i18n,
            locale=locale,
            target_user_id=target_id,
            game=game,
            subscribed=subscribed,
            liked=liked,
            include_next=True,
            include_hide=False,
            include_previous=bool(history),
        ),
        photo_file_id=profile.profile_image_file_id,
    )
    await state.update_data(
        search_view_mode='game_card',
        search_current_profile_id=str(profile.id),
        search_card_chat_id=sent.chat.id,
        search_card_message_id=sent.message_id,
    )
    return True


async def _render_user_profile_view(
    *,
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    viewer_id: int,
    target_id: int,
    i18n: LocalizationManager,
    locale: str,
    from_message_notice: bool = False,
    from_activity: bool = False,
    include_back_to_card: bool = True,
) -> bool:
    if not isinstance(callback.message, Message):
        return False
    target = await UserService(session).get_user(target_id)
    if target is None:
        return False
    if target_id != viewer_id:
        await UserService(session).increment_profile_visits_count(target_id)
    subscribed = await InteractionService(session).is_subscribed(viewer_id, target_id)
    payload = await UserService(session).get_profile_stats(target_id)
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_profile_text(payload, locale=locale),
        reply_markup=search_profile_notice_keyboard(
            i18n=i18n,
            locale=locale,
            user_id=target_id,
            subscribed=subscribed,
            game=GameCode.MLBB,
            include_back_to_card=(not from_message_notice) and (not from_activity) and include_back_to_card,
            include_back_to_activity=from_activity,
            include_hide_notice=False,
        ),
        photo_file_id=target.avatar_file_id,
    )
    await state.update_data(
        search_view_mode='user_profile',
        search_profile_view_user_id=target_id,
        search_profile_view_source='message_notice' if from_message_notice else ('activity' if from_activity else 'default'),
        search_profile_has_back=include_back_to_card,
        search_card_chat_id=sent.chat.id,
        search_card_message_id=sent.message_id,
    )
    return True


@router.callback_query(F.data == CB_SEARCH_BACK_TO_CARD)
async def search_back_to_card(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    await callback.answer()
    ok = await _render_current_search_card(callback, state, session, i18n)
    if not ok:
        await callback.answer('Не удалось вернуться к анкете', show_alert=True)


@router.callback_query(F.data.startswith(CB_SEARCH_BACK_TO_PROFILE_PREFIX))
async def search_back_to_profile(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    viewer_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    raw = (callback.data or '').replace(CB_SEARCH_BACK_TO_PROFILE_PREFIX, '', 1)
    if ':' in raw:
        raw = raw.split(':', 1)[0]
    try:
        target_id = int(raw)
    except ValueError:
        await callback.answer('Ошибка действия', show_alert=True)
        return

    source = (await state.get_data()).get('search_profile_view_source')
    await callback.answer()
    ok = await _render_user_profile_view(
        callback=callback,
        state=state,
        session=session,
        viewer_id=viewer_id,
        target_id=target_id,
        i18n=i18n,
        locale=locale,
        from_message_notice=False,
        from_activity=source == 'activity',
    )
    if not ok:
        await callback.answer('Профиль недоступен', show_alert=True)


@router.callback_query(F.data == CB_SEARCH_HIDE_NOTICE)
async def search_hide_notice(callback: CallbackQuery) -> None:
    if not isinstance(callback.message, Message):
        return
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
