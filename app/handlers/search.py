from html import escape
from pathlib import Path
import random
from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
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
    SEARCH_GAME_PICK_IMAGE_FILE_ID,
    MY_PROFILES_CREATE_IMAGE_FILE_ID,
)
from app.database import GameCode, MlbbLaneCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.states import SearchStates
from app.keyboards import (
    main_menu_keyboard,
    search_empty_keyboard,
    search_game_pick_keyboard,
    search_hide_keyboard,
    search_like_notice_keyboard,
    search_message_notice_keyboard,
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
from app.utils import format_datetime

router = Router(name='search')

DEFAULT_AVATAR_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'default_avatar.png'
SEARCH_IMAGE_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'search.png'


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


def _search_card_text(profile, user) -> str:
    return (
        f"<b>🎮 Игровая анкета {escape(_full_name(user))}</b>\n\n"
        f"<b>🆔 ID:</b> <code>{escape(profile.game_player_id or 'Не указано')}</code>\n"
        f"<b>🌍 Сервер:</b> {escape(profile.play_time or 'Не указано')}\n\n"
        f"<b>🎖 Ранг:</b> {escape(_format_rank(profile.rank, profile.mythic_stars))}\n"
        f"<b>🛡 Основная линия:</b> {escape(_lane_title(profile.main_lane.value if profile.main_lane else None))}\n"
        f"<b>🎯 Доп. линии:</b> {escape(_extra_lanes_text(profile.extra_lanes))}\n\n"
        f"<b>📝 О себе:</b> {escape(profile.description or 'Не указано')}"
    )


def _profile_text(payload: dict[str, object]) -> str:
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
        f"<b>❤️ Лайки:</b> {likes}\n"
        f"<b>👥 Подписчики:</b> {followers}\n"
        f"<b>⭐ Подписки:</b> {subscriptions}\n"
        f"<b>🤝 Друзья:</b> {friends}\n\n"
        f"<b>📅 Дата регистрации:</b> {format_datetime(user.registered_at, 'ru').split(' ')[0]}"
    )


def _game_from_raw(raw: str) -> GameCode | None:
    try:
        game = GameCode(raw)
    except ValueError:
        return None
    if game != GameCode.MLBB:
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
    filtered_found: list[tuple[object, object, bool, bool]] = []
    for profile, owner in found:
        subscribed = await interaction_service.is_subscribed(user_id, owner.id)
        liked = await interaction_service.has_like(user_id, owner.id, game)
        if subscribed and liked:
            continue
        filtered_found.append((profile, owner, subscribed, liked))

    if not filtered_found:
        try:
            await message.edit_text(
                '😕 Пока больше анкет не найдено. Попробуйте позже.',
                reply_markup=search_empty_keyboard(i18n=i18n, locale=locale, game=game),
            )
        except TelegramBadRequest:
            await message.answer(
                '😕 Пока больше анкет не найдено. Попробуйте позже.',
                reply_markup=search_empty_keyboard(i18n=i18n, locale=locale, game=game),
            )
        return

    last_profile_id = None if reset_cycle else data.get('search_last_profile_id')
    pool = filtered_found
    if isinstance(last_profile_id, str):
        filtered = [item for item in filtered_found if str(item[0].id) != last_profile_id]
        if filtered:
            pool = filtered
        elif len(filtered_found) == 1:
            try:
                await message.edit_text(
                    '😕 Пока больше анкет не найдено. Попробуйте позже.',
                    reply_markup=search_empty_keyboard(i18n=i18n, locale=locale, game=game),
                )
            except TelegramBadRequest:
                await message.answer(
                    '😕 Пока больше анкет не найдено. Попробуйте позже.',
                    reply_markup=search_empty_keyboard(i18n=i18n, locale=locale, game=game),
                )
            return

    profile, owner, subscribed, liked = random.choice(pool)
    sent = await _send_or_edit_profile_card(
        message=message,
        caption=_search_card_text(profile, owner),
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

    if not await ProfileService(session).has_any_profile(user_id):
        await message.answer(
            '⚠️ Сначала создайте анкету, чтобы искать тиммейтов.',
            reply_markup=search_need_profile_keyboard(i18n, locale),
        )
        return

    await message.answer_photo(
        photo=SEARCH_GAME_PICK_IMAGE_FILE_ID,
        caption=(
            "<b>🎮 Выберите игру для поиска</b>\n\n"
            "Мы покажем актуальные игровые анкеты,\n"
            "где можно сразу <b>лайкнуть</b> или <b>написать</b>.\n\n"
            "✨ Чем подробнее заполнена анкета, тем быстрее найдется тиммейт."
        ),
        reply_markup=search_game_pick_keyboard(i18n, locale),
    )


@router.callback_query(F.data == CB_SEARCH_CREATE_PROFILE)
async def search_create_profile_hint(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    await ensure_user_and_locale(callback.from_user, session)
    await callback.answer()
    await _send_or_edit_profile_card(
        message=callback.message,
        caption="<b>🎮 Выберите игру для создания анкеты</b>",
        reply_markup=my_profiles_create_game_keyboard(games=[GameCode.MLBB]),
        photo_file_id=MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )


@router.callback_query(F.data == CB_SEARCH_BACK_MAIN)
async def search_back_to_main(callback: CallbackQuery, state: FSMContext, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    _, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    await state.clear()
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.message.answer(i18n.t(locale, 'start.welcome'), reply_markup=main_menu_keyboard(i18n, locale))


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
        await callback.answer('Игра пока недоступна', show_alert=True)
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
        await callback.answer('Игра пока недоступна', show_alert=True)
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
        await callback.answer('Игра пока недоступна', show_alert=True)
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
    selected_subscribed = False
    selected_liked = False
    while history:
        profile_id = history.pop()
        pair = found_map.get(profile_id)
        if pair is None:
            continue
        profile, owner = pair
        subscribed = await interaction_service.is_subscribed(user_id, owner.id)
        liked = await interaction_service.has_like(user_id, owner.id, game)
        if subscribed and liked:
            continue
        selected_profile = profile
        selected_owner = owner
        selected_subscribed = subscribed
        selected_liked = liked
        break

    if selected_profile is None or selected_owner is None:
        await state.update_data(search_history_profile_ids=[])
        await callback.answer('Предыдущая анкета недоступна', show_alert=False)
        return

    await callback.answer()
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_search_card_text(selected_profile, selected_owner),
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
        await callback.answer('Игра пока недоступна', show_alert=True)
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
        await callback.answer('Ошибка действия', show_alert=True)
        return
    game = _game_from_raw(game_raw)
    if game is None or to_user_id == from_user_id:
        await callback.answer('Нельзя выполнить действие', show_alert=True)
        return

    interactions = InteractionService(session)
    added = await interactions.add_like(from_user_id, to_user_id, game)
    if not added:
        await callback.answer('⚠️ Вы уже лайкали этого пользователя', show_alert=False)
        return

    await callback.answer('❤️ Лайк отправлен!', show_alert=False)
    to_user_settings = await UserService(session).notification_settings(to_user_id)
    if to_user_settings.get('likes', True):
        from_user = await UserService(session).get_user(from_user_id)
        from_name = escape(_full_name(from_user)) if from_user else 'Пользователь'
        await callback.bot.send_message(
            to_user_id,
            f'❤️ Ваша анкета понравилась {from_name}',
            parse_mode='HTML',
            reply_markup=search_like_notice_keyboard(i18n=i18n, locale=locale, liker_user_id=from_user_id, game=game),
        )

    if await interactions.is_mutual_like(from_user_id, to_user_id, game):
        users = UserService(session)
        first = await users.get_user(from_user_id)
        second = await users.get_user(to_user_id)
        if first and second:
            for receiver, other in ((from_user_id, second), (to_user_id, first)):
                receiver_settings = await users.notification_settings(receiver)
                if not receiver_settings.get('likes', True):
                    continue
                text = "🔥 Взаимные лайки!\n\nПриятно проведите время!"
                if other.username:
                    text += f"\nЮзернейм: @{other.username}"
                    builder = InlineKeyboardBuilder()
                    builder.button(text='💬 Перейти в ЛС', url=f'https://t.me/{other.username}')
                    builder.button(text='🔺 Скрыть сообщение', callback_data=CB_SEARCH_HIDE_NOTICE)
                    builder.adjust(1)
                    keyboard = builder.as_markup()
                else:
                    text += '\nЮзернейм: не указан'
                    builder = InlineKeyboardBuilder()
                    builder.button(text='Написать в боте', callback_data=f'{CB_SEARCH_MESSAGE_PREFIX}{other.id}')
                    builder.button(text='🔺 Скрыть сообщение', callback_data=CB_SEARCH_HIDE_NOTICE)
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
        await callback.answer('Игра пока недоступна', show_alert=True)
        return

    profile = await ProfileService(session).get_profile_for_game(liker_id, game)
    user = await UserService(session).get_user(liker_id)
    if profile is None or user is None:
        await callback.answer('Эта анкета больше недоступна.', show_alert=True)
        return

    interactions = InteractionService(session)
    subscribed = await interactions.is_subscribed(user_id, liker_id)
    liked = await interactions.has_like(user_id, liker_id, game)
    history_raw = (await state.get_data()).get('search_history_profile_ids')
    history = [item for item in history_raw if isinstance(item, str)] if isinstance(history_raw, list) else []
    await callback.answer()
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_search_card_text(profile, user),
        reply_markup=search_profile_actions_keyboard(
            i18n=i18n,
            locale=locale,
            target_user_id=liker_id,
            game=game,
            subscribed=subscribed,
            liked=liked,
            include_next=True,
            include_hide=True,
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
        await callback.answer('Ошибка действия', show_alert=True)
        return
    if target_id == follower_id:
        await callback.answer('Нельзя подписаться на себя', show_alert=True)
        return

    interactions = InteractionService(session)
    subscribed_now = await interactions.toggle_subscription(follower_id, target_id)
    await callback.answer('Подписка оформлена ⭐' if subscribed_now else 'Подписка отменена')

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
                f'⭐ На вас подписался {follower_name}',
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
        await callback.answer('Ошибка действия', show_alert=True)
        return
    if target_id == user_id:
        await callback.answer('Нельзя отправить сообщение себе', show_alert=True)
        return

    await state.set_state(SearchStates.waiting_for_message_text)
    await state.update_data(search_message_target_user_id=target_id)
    await callback.answer()
    prompt = await callback.message.answer(
        '💬 Введите сообщение для отправки пользователю.',
        reply_markup=search_message_cancel_keyboard(i18n, locale),
    )
    await state.update_data(search_message_prompt_chat_id=prompt.chat.id, search_message_prompt_message_id=prompt.message_id)


@router.callback_query(F.data == CB_SEARCH_CANCEL_MESSAGE)
async def search_cancel_message(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.answer('Отправка сообщения отменена')
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
        await message.answer('Ошибка отправки. Попробуйте снова.')
        return
    text = (message.text or '').strip()
    if not text:
        await message.answer(
            'Введите текст сообщения или нажмите «❌ Отменить».',
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
    await interactions.create_message(from_user_id, target_id, text)
    sender = await UserService(session).get_user(from_user_id)
    sender_name = 'Пользователь'
    if sender is not None:
        sender_name = sender.username or _full_name(sender)
    target_settings = await UserService(session).notification_settings(target_id)
    if target_settings.get('messages', True):
        await message.bot.send_message(
            target_id,
            f"📩 <b>У вас новое сообщение от {escape(sender_name)}</b>\n\n💬 <b>Сообщение:</b>\n<code>{escape(text)}</code>",
            parse_mode='HTML',
            reply_markup=search_message_notice_keyboard(i18n=i18n, locale=locale, user_id=from_user_id, game=GameCode.MLBB),
        )
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await state.clear()
    await message.bot.send_message(chat_id=message.chat.id, text=
        f"<b>✅ Ваше сообщение отправлено пользователю.</b>\n\n💬 <b>Ваше сообщение:</b>\n<code>{escape(text)}</code>",
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
    if ':' in raw:
        target_raw, source_raw = raw.split(':', 1)
        raw = target_raw
        from_message_notice = source_raw == 'msg'
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
        caption=_profile_text(payload),
        reply_markup=search_profile_notice_keyboard(
            i18n=i18n,
            locale=locale,
            user_id=target_id,
            subscribed=subscribed,
            game=GameCode.MLBB,
            include_back_to_card=(not from_message_notice) and has_back_to_card,
            include_hide_notice=False,
        ),
        photo_file_id=target.avatar_file_id,
    )
    await state.update_data(
        search_view_mode='user_profile',
        search_profile_view_user_id=target_id,
        search_profile_view_source='message_notice' if from_message_notice else 'default',
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
        caption='🕹 <b>Игровые анкеты пользователя</b>\n\nВыберите игру:',
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
        await callback.answer('Игра пока недоступна', show_alert=True)
        return

    profile = await ProfileService(session).get_profile_for_game(target_id, game)
    user = await UserService(session).get_user(target_id)
    if profile is None or user is None:
        await callback.answer('Эта анкета больше недоступна.', show_alert=True)
        return

    interactions = InteractionService(session)
    subscribed = await interactions.is_subscribed(viewer_id, target_id)
    liked = await interactions.has_like(viewer_id, target_id, game)
    history_raw = (await state.get_data()).get('search_history_profile_ids')
    history = [item for item in history_raw if isinstance(item, str)] if isinstance(history_raw, list) else []
    await callback.answer()
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_search_card_text(profile, user),
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

    subscribed = await InteractionService(session).is_subscribed(viewer_id, target_id)
    liked = await InteractionService(session).has_like(viewer_id, target_id, game)
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_search_card_text(profile, user),
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
    include_back_to_card: bool = True,
) -> bool:
    if not isinstance(callback.message, Message):
        return False
    target = await UserService(session).get_user(target_id)
    if target is None:
        return False
    subscribed = await InteractionService(session).is_subscribed(viewer_id, target_id)
    payload = await UserService(session).get_profile_stats(target_id)
    sent = await _send_or_edit_profile_card(
        message=callback.message,
        caption=_profile_text(payload),
        reply_markup=search_profile_notice_keyboard(
            i18n=i18n,
            locale=locale,
            user_id=target_id,
            subscribed=subscribed,
            game=GameCode.MLBB,
            include_back_to_card=(not from_message_notice) and include_back_to_card,
            include_hide_notice=False,
        ),
        photo_file_id=target.avatar_file_id,
    )
    await state.update_data(
        search_view_mode='user_profile',
        search_profile_view_user_id=target_id,
        search_profile_view_source='message_notice' if from_message_notice else 'default',
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
