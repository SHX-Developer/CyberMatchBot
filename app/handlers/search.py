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
    BTN_FIND_TEAMMATE,
    CB_SEARCH_BACK_MAIN,
    CB_SEARCH_CANCEL_MESSAGE,
    CB_SEARCH_CREATE_PROFILE,
    CB_SEARCH_GAME_PICK_PREFIX,
    CB_SEARCH_HIDE_NOTICE,
    CB_SEARCH_LIKE_PREFIX,
    CB_SEARCH_MESSAGE_PREFIX,
    CB_SEARCH_NEXT_PREFIX,
    CB_SEARCH_RETRY_PREFIX,
    CB_SEARCH_SUB_PREFIX,
    CB_SEARCH_VIEW_LIKER_PREFIX,
    CB_SEARCH_VIEW_PROFILE_PREFIX,
)
from app.database import GameCode, MlbbLaneCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.states import SearchStates
from app.keyboards import (
    main_menu_keyboard,
    search_empty_keyboard,
    search_game_pick_keyboard,
    search_like_notice_keyboard,
    search_message_cancel_keyboard,
    search_need_profile_keyboard,
    search_profile_actions_keyboard,
    search_profile_notice_keyboard,
)
from app.locales import LocalizationManager
from app.services import InteractionService, ProfileService, UserService

router = Router(name='search')

DEFAULT_AVATAR_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'default_avatar.png'


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
        "<b>🎮 Анкета игрока</b>\n\n"
        f"<b>👤 Игрок:</b> {escape(_full_name(user))}\n"
        f"<b>🔗 Username:</b> {escape(_username(user))}\n"
        f"<b>🆔 ID:</b> <code>{escape(profile.game_player_id or 'Не указано')}</code>\n"
        f"<b>🎖 Ранг:</b> {escape(profile.rank or 'Не указано')}\n"
        f"<b>🛡 Основная линия:</b> {escape(_lane_title(profile.main_lane.value if profile.main_lane else None))}\n"
        f"<b>🎯 Доп. линии:</b> {escape(_extra_lanes_text(profile.extra_lanes))}\n"
        f"<b>🌍 Сервер:</b> {escape(profile.play_time or 'Не указано')}\n"
        f"<b>📝 О себе:</b> {escape(profile.description or 'Не указано')}"
    )


def _profile_text(user) -> str:
    return (
        "<b>👤 Профиль пользователя</b>\n\n"
        f"<b>📝 Имя:</b> {escape(_full_name(user))}\n"
        f"<b>🔗 Username:</b> {escape(_username(user))}"
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
    user_id: int,
    game: GameCode,
    reset_cycle: bool = False,
) -> None:
    profile_service = ProfileService(session)
    interaction_service = InteractionService(session)
    found = await profile_service.search_profiles(user_id, game)
    if not found:
        try:
            await message.edit_text(
                '😕 Пока больше анкет не найдено. Попробуйте позже.',
                reply_markup=search_empty_keyboard(game=game),
            )
        except TelegramBadRequest:
            await message.answer('😕 Пока больше анкет не найдено. Попробуйте позже.', reply_markup=search_empty_keyboard(game=game))
        return

    data = await state.get_data()
    last_profile_id = None if reset_cycle else data.get('search_last_profile_id')
    pool = found
    if isinstance(last_profile_id, str):
        filtered = [item for item in found if str(item[0].id) != last_profile_id]
        if filtered:
            pool = filtered
        elif len(found) == 1:
            try:
                await message.edit_text(
                    '😕 Пока больше анкет не найдено. Попробуйте позже.',
                    reply_markup=search_empty_keyboard(game=game),
                )
            except TelegramBadRequest:
                await message.answer('😕 Пока больше анкет не найдено. Попробуйте позже.', reply_markup=search_empty_keyboard(game=game))
            return

    profile, owner = random.choice(pool)
    subscribed = await interaction_service.is_subscribed(user_id, owner.id)
    sent = await _send_or_edit_profile_card(
        message=message,
        caption=_search_card_text(profile, owner),
        reply_markup=search_profile_actions_keyboard(target_user_id=owner.id, game=game, subscribed=subscribed),
        photo_file_id=profile.profile_image_file_id,
    )
    await state.update_data(
        search_game=game.value,
        search_last_profile_id=str(profile.id),
        search_current_target_user_id=owner.id,
        search_card_chat_id=sent.chat.id,
        search_card_message_id=sent.message_id,
    )


@router.message(F.text == BTN_FIND_TEAMMATE)
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
            reply_markup=search_need_profile_keyboard(),
        )
        return

    await message.answer('🎮 Выберите игру для поиска', reply_markup=search_game_pick_keyboard())


@router.callback_query(F.data == CB_SEARCH_CREATE_PROFILE)
async def search_create_profile_hint(callback: CallbackQuery) -> None:
    if not isinstance(callback.message, Message):
        return
    await callback.answer()
    await callback.message.edit_text(
        'Откройте раздел «🗂 Мои анкеты» в главном меню и создайте анкету Mobile Legends.',
        reply_markup=search_need_profile_keyboard(),
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
    await callback.message.answer(i18n.t(locale, 'start.welcome'), reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith(CB_SEARCH_GAME_PICK_PREFIX))
async def search_game_pick(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    raw = (callback.data or '').replace(CB_SEARCH_GAME_PICK_PREFIX, '', 1)
    game = _game_from_raw(raw)
    if game is None:
        await callback.answer('Игра пока недоступна', show_alert=True)
        return
    await callback.answer()
    await _show_next_profile(message=callback.message, state=state, session=session, user_id=user_id, game=game, reset_cycle=True)


@router.callback_query(F.data.startswith(CB_SEARCH_NEXT_PREFIX))
async def search_next_profile(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    raw = (callback.data or '').replace(CB_SEARCH_NEXT_PREFIX, '', 1)
    game = _game_from_raw(raw)
    if game is None:
        await callback.answer('Игра пока недоступна', show_alert=True)
        return
    await callback.answer()
    await _show_next_profile(message=callback.message, state=state, session=session, user_id=user_id, game=game)


@router.callback_query(F.data.startswith(CB_SEARCH_RETRY_PREFIX))
async def search_retry(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    raw = (callback.data or '').replace(CB_SEARCH_RETRY_PREFIX, '', 1)
    game = _game_from_raw(raw)
    if game is None:
        await callback.answer('Игра пока недоступна', show_alert=True)
        return
    await callback.answer()
    await _show_next_profile(message=callback.message, state=state, session=session, user_id=user_id, game=game, reset_cycle=True)


@router.callback_query(F.data.startswith(CB_SEARCH_LIKE_PREFIX))
async def search_like(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None:
        return
    from_user_id, _ = await ensure_user_and_locale(callback.from_user, session)
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
        await callback.answer('Вы уже лайкнули этого пользователя', show_alert=True)
        return

    await callback.answer('Лайк отправлен ❤️')
    await callback.bot.send_message(
        to_user_id,
        '❤️ Вас лайкнули!\n\nНажмите «Посмотреть», чтобы открыть анкету.',
        reply_markup=search_like_notice_keyboard(liker_user_id=from_user_id, game=game),
    )

    if await interactions.is_mutual_like(from_user_id, to_user_id, game):
        users = UserService(session)
        first = await users.get_user(from_user_id)
        second = await users.get_user(to_user_id)
        if first and second:
            for receiver, other in ((from_user_id, second), (to_user_id, first)):
                text = "🔥 <b>Взаимные лайки!</b>\nПриятно проведите время!"
                if other.username:
                    text += f"\nЮзернейм: @{escape(other.username)}"
                    builder = InlineKeyboardBuilder()
                    builder.button(text='💬 Перейти в ЛС', url=f'https://t.me/{other.username}')
                    keyboard = builder.as_markup()
                else:
                    text += '\nУ пользователя нет username. Напишите ему через бот.'
                    builder = InlineKeyboardBuilder()
                    builder.button(text='💬 Отправить сообщение', callback_data=f'{CB_SEARCH_MESSAGE_PREFIX}{other.id}')
                    keyboard = builder.as_markup()
                await callback.bot.send_message(receiver, text, parse_mode='HTML', reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_SEARCH_VIEW_LIKER_PREFIX))
async def search_view_liker(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
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

    subscribed = await InteractionService(session).is_subscribed(user_id, liker_id)
    await callback.answer()
    await _send_or_edit_profile_card(
        message=callback.message,
        caption=_search_card_text(profile, user),
        reply_markup=search_profile_actions_keyboard(
            target_user_id=liker_id,
            game=game,
            subscribed=subscribed,
            include_next=False,
            include_hide=True,
        ),
        photo_file_id=profile.profile_image_file_id,
    )
    await state.update_data(search_game=game.value, search_current_target_user_id=liker_id)


@router.callback_query(F.data.startswith(CB_SEARCH_SUB_PREFIX))
async def search_toggle_sub(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    follower_id, _ = await ensure_user_and_locale(callback.from_user, session)
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
    game_raw = data.get('search_game')
    game = _game_from_raw(game_raw) if isinstance(game_raw, str) else GameCode.MLBB

    if isinstance(current_target, int) and current_target == target_id:
        await callback.message.edit_reply_markup(
            reply_markup=search_profile_actions_keyboard(
                target_user_id=target_id,
                game=game,
                subscribed=subscribed_now,
            )
        )
    else:
        await callback.message.edit_reply_markup(
            reply_markup=search_profile_notice_keyboard(user_id=target_id, subscribed=subscribed_now)
        )

    if subscribed_now:
        users = UserService(session)
        follower = await users.get_user(follower_id)
        follower_name = escape(_full_name(follower)) if follower else 'Пользователь'
        target_subscribed = await interactions.is_subscribed(target_id, follower_id)
        await callback.bot.send_message(
            target_id,
            f'⭐ На вас подписались!\nПодписчик: {follower_name}',
            parse_mode='HTML',
            reply_markup=search_profile_notice_keyboard(user_id=follower_id, subscribed=target_subscribed),
        )


@router.callback_query(F.data.startswith(CB_SEARCH_MESSAGE_PREFIX))
async def search_start_message(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
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
    await callback.message.answer('💬 Введите сообщение для отправки пользователю.', reply_markup=search_message_cancel_keyboard())


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
async def search_send_message(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    from_user_id, _ = await ensure_user_and_locale(message.from_user, session)
    data = await state.get_data()
    target_id = data.get('search_message_target_user_id')
    if not isinstance(target_id, int):
        await state.clear()
        await message.answer('Ошибка отправки. Попробуйте снова.')
        return
    text = (message.text or '').strip()
    if not text:
        await message.answer('Введите текст сообщения или нажмите «❌ Отменить».', reply_markup=search_message_cancel_keyboard())
        return

    interactions = InteractionService(session)
    await interactions.create_message(from_user_id, target_id, text)
    sender = await UserService(session).get_user(from_user_id)
    sender_name = escape(_full_name(sender)) if sender else 'Пользователь'
    target_subscribed = await interactions.is_subscribed(target_id, from_user_id)
    await message.bot.send_message(
        target_id,
        f"📩 <b>Вам пришло новое сообщение!</b>\nОт: {sender_name}\n\n{escape(text)}",
        parse_mode='HTML',
        reply_markup=search_profile_notice_keyboard(user_id=from_user_id, subscribed=target_subscribed),
    )
    await state.clear()
    await message.answer('✅ Сообщение отправлено.')


@router.callback_query(F.data.startswith(CB_SEARCH_VIEW_PROFILE_PREFIX))
async def search_view_profile(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    viewer_id, _ = await ensure_user_and_locale(callback.from_user, session)
    raw = (callback.data or '').replace(CB_SEARCH_VIEW_PROFILE_PREFIX, '', 1)
    try:
        target_id = int(raw)
    except ValueError:
        await callback.answer('Ошибка действия', show_alert=True)
        return
    target = await UserService(session).get_user(target_id)
    if target is None:
        await callback.answer('Профиль недоступен', show_alert=True)
        return
    subscribed = await InteractionService(session).is_subscribed(viewer_id, target_id)
    await callback.answer()
    await callback.message.edit_text(
        _profile_text(target),
        parse_mode='HTML',
        reply_markup=search_profile_notice_keyboard(user_id=target_id, subscribed=subscribed),
    )


@router.callback_query(F.data == CB_SEARCH_HIDE_NOTICE)
async def search_hide_notice(callback: CallbackQuery) -> None:
    if not isinstance(callback.message, Message):
        return
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
