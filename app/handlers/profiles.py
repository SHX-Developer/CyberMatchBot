from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    BTN_MY_PROFILES_TEXTS,
    CB_MY_PROFILES_BACK,
    CB_MY_PROFILES_CARD_BACK,
    CB_MY_PROFILES_CREATE_CANCEL,
    CB_MY_PROFILES_CREATE_MENU,
    CB_MY_PROFILES_CREATE_PICK_PREFIX,
    CB_MY_PROFILES_DELETE_ASK,
    CB_MY_PROFILES_DELETE_CANCEL,
    CB_MY_PROFILES_DELETE_CONFIRM,
    CB_MY_PROFILES_REFILL,
    CB_MY_PROFILES_EDIT,
    CB_MY_PROFILES_EDIT_CANCEL,
    CB_MY_PROFILES_HIDE_NOTICE,
    CB_MY_PROFILES_EDIT_FIELD_PREFIX,
    CB_MY_PROFILES_GAME_PREFIX,
    CB_MY_PROFILES_MLBB_EXTRA_DONE,
    CB_MY_PROFILES_MLBB_EXTRA_PREFIX,
    CB_MY_PROFILES_MLBB_MAIN_PREFIX,
    CB_MY_PROFILES_MLBB_RANK_PREFIX,
    CB_MY_PROFILES_MLBB_SERVER_PREFIX,
    MY_PROFILES_CREATE_IMAGE_FILE_ID,
    MY_PROFILES_IMAGE_FILE_ID,
)
from app.database import GameCode, MlbbLaneCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.states import ProfilesSectionStates
from app.keyboards import (
    language_keyboard,
    my_profile_details_keyboard,
    my_profiles_create_cancel_keyboard,
    my_profiles_create_game_keyboard,
    my_profiles_dashboard_keyboard,
    my_profiles_delete_confirm_keyboard,
    my_profiles_edit_fields_keyboard,
    my_profiles_edit_cancel_keyboard,
    my_profiles_mlbb_extra_lanes_keyboard,
    my_profiles_hide_notice_keyboard,
    my_profiles_mlbb_main_lane_keyboard,
    my_profiles_mlbb_rank_keyboard,
    my_profiles_mlbb_server_keyboard,
)
from app.locales import LocalizationManager
from app.services import ProfileService
from app.utils import is_valid_mlbb_player_id

router = Router(name='profiles_section')

DEFAULT_AVATAR_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'default_avatar.png'
ASSETS_DIR = Path(__file__).resolve().parent.parent / 'assets'
DASHBOARD_PHOTO_PATH = ASSETS_DIR / 'anketi.png'
CREATE_GAMES_PHOTO_PATH = ASSETS_DIR / 'games.png'
MLBB_CREATE_PHOTO_PATH = ASSETS_DIR / 'mobile_legends.png'
DELETE_PROFILE_PHOTO_PATH = ASSETS_DIR / 'delete_anketu.png'
SUPPORTED_GAMES = (GameCode.MLBB,)


def _parse_lane(raw: str) -> MlbbLaneCode | None:
    try:
        return MlbbLaneCode(raw)
    except ValueError:
        return None


def _lane_title(lane: MlbbLaneCode) -> str:
    mapping = {
        MlbbLaneCode.GOLD: 'Линия золота',
        MlbbLaneCode.MID: 'Средняя линия',
        MlbbLaneCode.EXP: 'Линия опыта',
        MlbbLaneCode.JUNGLE: 'Лесник',
        MlbbLaneCode.ROAM: 'Роумер',
        MlbbLaneCode.ALL: 'На всех линиях',
    }
    return mapping[lane]


def _game_title(game: GameCode) -> str:
    if game == GameCode.MLBB:
        return 'Mobile Legends'
    return 'Неизвестная игра'


def _safe(value: str | None) -> str:
    if value and value.strip():
        return value.strip()
    return 'Не указано'


def _dashboard_text(profiles_by_game: dict[GameCode, object]) -> str:
    lines = ['<b>🎮 Ваши игровые анкеты</b>', '']
    for game in SUPPORTED_GAMES:
        if game in profiles_by_game:
            lines.append(f'✅ {_game_title(game)}: Создана')
        else:
            lines.append(f'❌ {_game_title(game)}: Не создана')
        lines.append('')
    lines.append('❌ Genshin Impact: Не создана')
    lines.append('')
    lines.append('❌ Roblox: Не создана')
    return '\n'.join(lines)


def _profile_card_text(profile) -> str:
    if profile.game == GameCode.MLBB:
        main_role = _lane_title(profile.main_lane) if profile.main_lane else 'Не указано'
        extra_values: list[str] = []
        for raw in profile.extra_lanes or []:
            lane = _parse_lane(raw)
            if lane is None:
                continue
            extra_values.append(_lane_title(lane))
        extra_roles = ', '.join(extra_values) if extra_values else 'Не указано'

        return (
            f"<b>🎮 Анкета: {_game_title(profile.game)}</b>\n\n"
            f"<b>🆔 ID:</b> {_safe(profile.game_player_id)}\n"
            f"<b>🌍 Регион:</b> {_safe(profile.play_time)}\n\n"
            f"<b>🎖 Ранг:</b> {_safe(profile.rank)}\n"
            f"<b>🛡 Роль:</b> {main_role}\n"
            f"<b>🎯 Доп. линии:</b> {extra_roles}\n\n"
            f"<b>📝 О себе:</b> {_safe(profile.description)}"
        )

    return (
        f"<b>Анкета: {_game_title(profile.game)}</b>\n\n"
        f"<b>🎮 Игра:</b> {_game_title(profile.game)}\n"
        f"<b>🆔 ID:</b> {_safe(profile.game_player_id)}\n"
        f"<b>🎖 Ранг:</b> {_safe(profile.rank)}\n"
        f"<b>🛡 Роль:</b> {_safe(profile.role)}\n"
        f"<b>🌍 Сервер:</b> {_safe(profile.play_time)}\n"
        f"<b>📝 О себе:</b> {_safe(profile.description or profile.about)}"
    )


def _mlbb_progress_caption(data: dict) -> str:
    lines = ['<b>🎮 Создание анкеты Mobile Legends</b>', '']
    top_block: list[str] = []
    middle_block: list[str] = []
    bottom_block: list[str] = []

    if isinstance(data.get('mlbb_game_id'), str):
        top_block.append(f"<b>🆔 ID:</b> {data['mlbb_game_id'].strip()}")
    if isinstance(data.get('mlbb_server'), str):
        top_block.append(f"<b>🌍 Регион:</b> {data['mlbb_server'].strip()}")

    if isinstance(data.get('mlbb_rank'), str):
        middle_block.append(f"<b>🎖 Ранг:</b> {data['mlbb_rank'].strip()}")

    main_lane = None
    main_raw = data.get('mlbb_main_lane')
    if isinstance(main_raw, str):
        lane = _parse_lane(main_raw)
        if lane is not None:
            main_lane = _lane_title(lane)
            middle_block.append(f"<b>🛡 Роль:</b> {main_lane}")

    extra_raw = data.get('mlbb_extra_lanes') if isinstance(data.get('mlbb_extra_lanes'), list) else []
    extra_values: list[str] = []
    for raw in extra_raw:
        lane = _parse_lane(raw)
        if lane is not None and _lane_title(lane) != main_lane:
            extra_values.append(_lane_title(lane))
    if extra_values:
        middle_block.append(f"<b>🎯 Доп. линии:</b> {', '.join(extra_values)}")

    if isinstance(data.get('mlbb_about_preview'), str):
        bottom_block.append(f"<b>📝 О себе:</b> {data['mlbb_about_preview'].strip()}")

    if top_block:
        lines.extend(top_block)
    if middle_block:
        if top_block:
            lines.append('')
        lines.extend(middle_block)
    if bottom_block:
        if top_block or middle_block:
            lines.append('')
        lines.extend(bottom_block)
    return '\n'.join(lines)


async def _remember_temp_notice(state: FSMContext, message: Message) -> None:
    data = await state.get_data()
    existing = data.get('edit_temp_notice_ids') if isinstance(data.get('edit_temp_notice_ids'), list) else []
    existing.append(message.message_id)
    await state.update_data(edit_temp_notice_ids=existing)


async def _delete_temp_notices(state: FSMContext, source_message: Message) -> None:
    data = await state.get_data()
    notice_ids = data.get('edit_temp_notice_ids') if isinstance(data.get('edit_temp_notice_ids'), list) else []
    for message_id in notice_ids:
        if not isinstance(message_id, int):
            continue
        try:
            await source_message.bot.delete_message(chat_id=source_message.chat.id, message_id=message_id)
        except TelegramBadRequest:
            pass
    await state.update_data(edit_temp_notice_ids=[])


async def _remember_message(state: FSMContext, message: Message) -> None:
    await state.update_data(my_profiles_chat_id=message.chat.id, my_profiles_message_id=message.message_id)


async def _remember_prompt_message(state: FSMContext, message: Message) -> None:
    await state.update_data(my_profiles_prompt_chat_id=message.chat.id, my_profiles_prompt_message_id=message.message_id)


async def _message_ref(state: FSMContext) -> tuple[int, int] | None:
    data = await state.get_data()
    chat_id = data.get('my_profiles_chat_id')
    message_id = data.get('my_profiles_message_id')
    if not isinstance(chat_id, int) or not isinstance(message_id, int):
        return None
    return chat_id, message_id


async def _prompt_ref(state: FSMContext) -> tuple[int, int] | None:
    data = await state.get_data()
    chat_id = data.get('my_profiles_prompt_chat_id')
    message_id = data.get('my_profiles_prompt_message_id')
    if not isinstance(chat_id, int) or not isinstance(message_id, int):
        return None
    return chat_id, message_id


async def _delete_prompt_by_ref(state: FSMContext, source_message: Message) -> None:
    ref = await _prompt_ref(state)
    if ref is None:
        return
    chat_id, message_id = ref
    try:
        await source_message.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass
    await state.update_data(my_profiles_prompt_chat_id=None, my_profiles_prompt_message_id=None)


def _photo_media(photo_file_id: str | None, photo_path: Path | None = None):
    if photo_file_id:
        return photo_file_id
    if photo_path is not None and photo_path.exists():
        return FSInputFile(photo_path)
    return FSInputFile(DEFAULT_AVATAR_PATH)


def _message_image_file_id(message: Message) -> str | None:
    if message.photo:
        return message.photo[-1].file_id
    document = message.document
    if document is not None and (document.mime_type or '').startswith('image/'):
        return document.file_id
    return None


async def _edit_screen(
    message: Message,
    *,
    caption: str,
    reply_markup,
    photo_file_id: str | None = None,
    photo_path: Path | None = None,
) -> None:
    media = InputMediaPhoto(media=_photo_media(photo_file_id, photo_path), caption=caption, parse_mode='HTML')
    try:
        await message.edit_media(media=media, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if 'message is not modified' not in str(exc):
            raise


async def _edit_screen_by_ref(
    state: FSMContext,
    source_message: Message,
    *,
    caption: str,
    reply_markup,
    photo_file_id: str | None = None,
    photo_path: Path | None = None,
) -> None:
    ref = await _message_ref(state)
    if ref is None:
        return

    chat_id, message_id = ref
    media = InputMediaPhoto(media=_photo_media(photo_file_id, photo_path), caption=caption, parse_mode='HTML')
    try:
        await source_message.bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=media,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as exc:
        if 'message is not modified' not in str(exc):
            raise


async def _render_dashboard_by_ref(state: FSMContext, source_message: Message, user_id: int, session: AsyncSession) -> None:
    profile_service = ProfileService(session)
    profiles_by_game = await profile_service.get_profiles_indexed_by_game(user_id)
    created_games = [game for game in SUPPORTED_GAMES if game in profiles_by_game]
    await _edit_screen_by_ref(
        state,
        source_message,
        caption=_dashboard_text(profiles_by_game),
        reply_markup=my_profiles_dashboard_keyboard(created_games=created_games),
        photo_file_id=MY_PROFILES_IMAGE_FILE_ID,
    )


async def _render_dashboard(
    *,
    message: Message,
    state: FSMContext,
    user_id: int,
    session: AsyncSession,
    use_edit: bool,
) -> None:
    profile_service = ProfileService(session)
    profiles_by_game = await profile_service.get_profiles_indexed_by_game(user_id)

    created_games = [game for game in SUPPORTED_GAMES if game in profiles_by_game]
    caption = _dashboard_text(profiles_by_game)
    keyboard = my_profiles_dashboard_keyboard(created_games=created_games)

    if use_edit:
        await _edit_screen(message, caption=caption, reply_markup=keyboard, photo_file_id=MY_PROFILES_IMAGE_FILE_ID)
        await _remember_message(state, message)
        return

    start_photo = MY_PROFILES_IMAGE_FILE_ID
    sent = await message.answer_photo(photo=start_photo, caption=caption, reply_markup=keyboard)
    await _remember_message(state, sent)


async def _render_profile_card(
    *,
    message: Message,
    state: FSMContext,
    user_id: int,
    game: GameCode,
    session: AsyncSession,
) -> None:
    profile = await ProfileService(session).get_profile_for_game(user_id, game)
    if profile is None:
        await _render_dashboard(message=message, state=state, user_id=user_id, session=session, use_edit=True)
        return

    await state.update_data(active_game=game.value, active_profile_id=str(profile.id))
    await _edit_screen(
        message,
        caption=_profile_card_text(profile),
        reply_markup=my_profile_details_keyboard(),
        photo_file_id=profile.profile_image_file_id,
    )
    await _remember_message(state, message)


async def _render_active_profile_by_ref(state: FSMContext, source_message: Message, user_id: int, session: AsyncSession) -> None:
    data = await state.get_data()
    game_raw = data.get('active_game')
    if isinstance(game_raw, str):
        try:
            game = GameCode(game_raw)
            profile = await ProfileService(session).get_profile_for_game(user_id, game)
            if profile is not None:
                await state.update_data(active_profile_id=str(profile.id))
                await _edit_screen_by_ref(
                    state,
                    source_message,
                    caption=_profile_card_text(profile),
                    reply_markup=my_profile_details_keyboard(),
                    photo_file_id=profile.profile_image_file_id,
                )
                return
        except ValueError:
            pass
    await _render_dashboard_by_ref(state, source_message, user_id, session)


async def _finalize_profile_edit_success(
    state: FSMContext,
    source_message: Message,
    session: AsyncSession,
    user_id: int,
) -> None:
    await _delete_temp_notices(state, source_message)
    await state.set_state(None)
    await state.update_data(edit_field=None, edit_extra_lanes=[])
    await source_message.answer('✅ Данные анкеты сохранены.', reply_markup=my_profiles_hide_notice_keyboard())
    await _render_active_profile_by_ref(state, source_message, user_id, session)


@router.message(F.text.in_(BTN_MY_PROFILES_TEXTS))
async def my_profiles_open_handler(
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

    await _render_dashboard(message=message, state=state, user_id=user_id, session=session, use_edit=False)


@router.callback_query(F.data.startswith(CB_MY_PROFILES_GAME_PREFIX))
async def my_profiles_open_game_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    game_raw = (callback.data or '').replace(CB_MY_PROFILES_GAME_PREFIX, '', 1)
    try:
        game = GameCode(game_raw)
    except ValueError:
        await callback.answer('Неизвестная игра', show_alert=True)
        return

    await callback.answer()
    await _render_profile_card(message=callback.message, state=state, user_id=user_id, game=game, session=session)


@router.callback_query(F.data == CB_MY_PROFILES_BACK)
async def my_profiles_back_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    await callback.answer()
    await _render_dashboard(message=callback.message, state=state, user_id=user_id, session=session, use_edit=True)


@router.callback_query(F.data == CB_MY_PROFILES_CARD_BACK)
async def my_profiles_card_back_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    game_raw = data.get('active_game')
    if isinstance(game_raw, str):
        try:
            await callback.answer()
            await _render_profile_card(
                message=callback.message,
                state=state,
                user_id=user_id,
                game=GameCode(game_raw),
                session=session,
            )
            return
        except ValueError:
            pass

    await callback.answer()
    await _render_dashboard(message=callback.message, state=state, user_id=user_id, session=session, use_edit=True)


@router.callback_query(F.data == CB_MY_PROFILES_HIDE_NOTICE)
async def my_profiles_hide_notice_handler(callback: CallbackQuery) -> None:
    if not isinstance(callback.message, Message):
        return
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == CB_MY_PROFILES_CREATE_MENU)
async def my_profiles_create_menu_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    profiles_by_game = await ProfileService(session).get_profiles_indexed_by_game(user_id)
    missing_games = [game for game in SUPPORTED_GAMES if game not in profiles_by_game]

    if not missing_games:
        await callback.answer('Скоро добавим новые игры для анкет', show_alert=True)
        return

    await callback.answer()
    await _edit_screen(
        callback.message,
        caption='<b>🎮 Выберите игру для создания анкеты</b>',
        reply_markup=my_profiles_create_game_keyboard(games=missing_games),
        photo_file_id=MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await _remember_message(state, callback.message)


@router.callback_query(F.data.startswith(CB_MY_PROFILES_CREATE_PICK_PREFIX))
async def my_profiles_create_pick_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, _ = await ensure_user_and_locale(callback.from_user, session)
    game_raw = (callback.data or '').replace(CB_MY_PROFILES_CREATE_PICK_PREFIX, '', 1)
    try:
        game = GameCode(game_raw)
    except ValueError:
        await callback.answer('Неизвестная игра', show_alert=True)
        return

    if game != GameCode.MLBB:
        await callback.answer('Для этой игры создание будет добавлено позже', show_alert=True)
        return

    await state.set_state(ProfilesSectionStates.mlbb_waiting_photo)
    await state.update_data(create_game=game.value, create_mode='new', mlbb_extra_lanes=[])
    await callback.answer()
    await _edit_screen(
        callback.message,
        caption="<b>🎮 Создание анкеты Mobile Legends</b>",
        reply_markup=None,
        photo_file_id=MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await _remember_message(state, callback.message)
    prompt = await callback.message.answer(
        "📸 <b>Отправьте скриншот вашей анкеты из игры.</b>\n\n"
        "Это поможет другим игрокам быстрее вас узнать.",
        reply_markup=my_profiles_create_cancel_keyboard(),
    )
    await _remember_prompt_message(state, prompt)


@router.callback_query(F.data == CB_MY_PROFILES_CREATE_CANCEL)
async def my_profiles_create_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    create_mode = data.get('create_mode')
    if create_mode == 'new':
        profile = await ProfileService(session).get_profile_for_game(user_id, GameCode.MLBB)
        if profile is not None:
            is_incomplete = (
                not profile.game_player_id
                or not profile.profile_image_file_id
                or not profile.rank
                or not profile.play_time
                or profile.main_lane is None
                or not profile.extra_lanes
                or not profile.description
            )
            if is_incomplete:
                await ProfileService(session).delete_owned_profile(user_id, profile.id)
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await _delete_temp_notices(state, callback.message)
    await state.set_state(None)
    await state.update_data(create_mode=None)
    if create_mode == 'refill':
        await _render_active_profile_by_ref(state, callback.message, user_id, session)
        return
    await _render_dashboard_by_ref(state, callback.message, user_id, session)


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_photo), F.photo | F.document)
async def mlbb_create_photo_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None:
        return

    await ensure_user_and_locale(message.from_user, session)
    photo_file_id = _message_image_file_id(message)
    if photo_file_id is None:
        await message.answer('Пожалуйста, отправьте изображение.', reply_markup=my_profiles_create_cancel_keyboard())
        return
    await state.update_data(mlbb_photo_file_id=photo_file_id)
    data = await state.get_data()
    await _edit_screen_by_ref(
        state,
        message,
        caption=_mlbb_progress_caption(data),
        reply_markup=None,
        photo_file_id=photo_file_id,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_game_id)
    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    prompt = await message.answer(
        "<b>🆔 Введите ваши ID из игры:</b>\n\nПример: <code>1129099628(13762)</code>",
        reply_markup=my_profiles_create_cancel_keyboard(),
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_photo))
async def mlbb_create_photo_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    await ensure_user_and_locale(message.from_user, session)
    await message.answer('Пожалуйста, отправьте изображение.', reply_markup=my_profiles_create_cancel_keyboard())


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_game_id))
async def mlbb_create_game_id_handler(message: Message, state: FSMContext, session: AsyncSession, i18n: LocalizationManager) -> None:
    if message.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    locale = locale or i18n.default_locale
    game_id_raw = (message.text or '').strip()
    if not is_valid_mlbb_player_id(game_id_raw):
        await message.answer(
            '❌ <b>Неверный формат ID.</b>\n\nВведите в формате:\n<code>1129099628(13762)</code>',
            reply_markup=my_profiles_create_cancel_keyboard(),
        )
        return

    if await ProfileService(session).mlbb_id_exists(game_id_raw, exclude_owner_id=user_id):
        await message.answer(
            '⚠️ Такой MLBB ID уже используется в другой анкете.\n\n'
            'Пожалуйста, введите другой ID.',
            reply_markup=my_profiles_create_cancel_keyboard(),
        )
        return

    await state.update_data(mlbb_game_id=game_id_raw)
    data = await state.get_data()
    photo_file_id = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_screen_by_ref(
        state,
        message,
        caption=_mlbb_progress_caption(data),
        reply_markup=None,
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_server)
    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    prompt = await message.answer(
        '🌍 <b>Выберите ваш регион в игре.</b>',
        reply_markup=my_profiles_mlbb_server_keyboard(),
    )
    await _remember_prompt_message(state, prompt)


@router.callback_query(
    StateFilter(ProfilesSectionStates.mlbb_waiting_rank),
    F.data.startswith(CB_MY_PROFILES_MLBB_RANK_PREFIX),
)
async def mlbb_create_rank_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    rank = (callback.data or '').replace(CB_MY_PROFILES_MLBB_RANK_PREFIX, '', 1).strip()
    if rank not in {'Мастер', 'Грандмастер', 'Эпический', 'Легендарный', 'Мифический'}:
        await callback.answer('Неверный ранг', show_alert=True)
        return

    await state.update_data(mlbb_rank=rank)
    data = await state.get_data()
    photo_file_id = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_screen_by_ref(
        state,
        callback.message,
        caption=_mlbb_progress_caption(data),
        reply_markup=None,
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_main_lane)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        '🛡 <b>Выберите вашу основную линию:</b>',
        reply_markup=my_profiles_mlbb_main_lane_keyboard(i18n, locale),
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_rank))
async def mlbb_create_rank_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    await message.answer('Выберите ранг кнопками ниже.', reply_markup=my_profiles_mlbb_rank_keyboard())


@router.callback_query(StateFilter(ProfilesSectionStates.mlbb_waiting_main_lane), F.data.startswith(CB_MY_PROFILES_MLBB_MAIN_PREFIX))
async def mlbb_create_main_lane_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    lane_raw = (callback.data or '').replace(CB_MY_PROFILES_MLBB_MAIN_PREFIX, '', 1)
    lane = _parse_lane(lane_raw)
    if lane is None or lane == MlbbLaneCode.ALL:
        await callback.answer('Неверная линия', show_alert=True)
        return

    await state.update_data(mlbb_main_lane=lane.value, mlbb_extra_lanes=[])
    data = await state.get_data()
    photo_file_id = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_screen_by_ref(
        state,
        callback.message,
        caption=_mlbb_progress_caption(data),
        reply_markup=None,
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_extra_lanes)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        text='🎯 <b>Выберите дополнительные линии:</b>\n<i>Можно выбрать несколько</i>',
        reply_markup=my_profiles_mlbb_extra_lanes_keyboard(i18n, locale, selected=set(), excluded_lanes={lane}),
    )
    await _remember_prompt_message(state, prompt)


@router.callback_query(
    StateFilter(ProfilesSectionStates.mlbb_waiting_extra_lanes),
    F.data.startswith(CB_MY_PROFILES_MLBB_EXTRA_PREFIX),
    F.data != CB_MY_PROFILES_MLBB_EXTRA_DONE,
)
async def mlbb_create_extra_lane_toggle_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    lane_raw = (callback.data or '').replace(CB_MY_PROFILES_MLBB_EXTRA_PREFIX, '', 1)
    lane = _parse_lane(lane_raw)
    data = await state.get_data()
    main_lane_raw = data.get('mlbb_main_lane')
    main_lane = _parse_lane(main_lane_raw) if isinstance(main_lane_raw, str) else None
    if lane is None or (main_lane is not None and lane == main_lane):
        await callback.answer('Неверная линия', show_alert=True)
        return

    selected_raw = data.get('mlbb_extra_lanes') if isinstance(data.get('mlbb_extra_lanes'), list) else []
    selected: set[MlbbLaneCode] = set()
    for raw in selected_raw:
        parsed = _parse_lane(raw)
        if parsed is not None:
            selected.add(parsed)

    if lane in selected:
        selected.remove(lane)
    else:
        selected.add(lane)

    await state.update_data(mlbb_extra_lanes=[value.value for value in selected])
    await callback.answer()
    await callback.message.edit_text(
        '🎯 <b>Выберите дополнительные линии:</b>\n<i>Можно выбрать несколько</i>',
        reply_markup=my_profiles_mlbb_extra_lanes_keyboard(
            i18n,
            locale,
            selected=selected,
            excluded_lanes={main_lane} if main_lane is not None else set(),
        ),
    )


@router.callback_query(StateFilter(ProfilesSectionStates.mlbb_waiting_extra_lanes), F.data == CB_MY_PROFILES_MLBB_EXTRA_DONE)
async def mlbb_create_extra_done_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    data = await state.get_data()
    extra_raw = data.get('mlbb_extra_lanes') if isinstance(data.get('mlbb_extra_lanes'), list) else []

    extra_lanes: list[MlbbLaneCode] = []
    main_lane_raw = data.get('mlbb_main_lane')
    main_lane = _parse_lane(main_lane_raw) if isinstance(main_lane_raw, str) else None
    for raw in extra_raw:
        lane = _parse_lane(raw)
        if lane is not None and lane != main_lane:
            extra_lanes.append(lane)

    if not extra_lanes:
        await callback.answer('Выберите хотя бы одну дополнительную линию', show_alert=True)
        return

    await state.update_data(mlbb_extra_lanes=[lane.value for lane in extra_lanes])
    data = await state.get_data()
    photo_file_id = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_screen_by_ref(
        state,
        callback.message,
        caption=_mlbb_progress_caption(data),
        reply_markup=None,
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_about)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        '📝 <b>Добавьте описание в анкету:</b>\n\n'
        'Расскажите кратко о стиле игры, роли и когда обычно играете.',
        reply_markup=my_profiles_create_cancel_keyboard(),
    )
    await _remember_prompt_message(state, prompt)


@router.callback_query(
    StateFilter(ProfilesSectionStates.mlbb_waiting_server),
    F.data.startswith(CB_MY_PROFILES_MLBB_SERVER_PREFIX),
)
async def mlbb_create_server_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    await ensure_user_and_locale(callback.from_user, session)
    server = (callback.data or '').replace(CB_MY_PROFILES_MLBB_SERVER_PREFIX, '', 1).strip()
    if server not in {'UZ', 'RU', 'EU'}:
        await callback.answer('Неверный сервер', show_alert=True)
        return

    await state.update_data(mlbb_server=server)
    data = await state.get_data()
    photo_file_id = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_screen_by_ref(
        state,
        callback.message,
        caption=_mlbb_progress_caption(data),
        reply_markup=None,
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_rank)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        '🎖 <b>Выберите ваш ранг:</b>',
        reply_markup=my_profiles_mlbb_rank_keyboard(),
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_server))
async def mlbb_create_server_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    await message.answer('Выберите сервер кнопками ниже.', reply_markup=my_profiles_mlbb_server_keyboard())


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_about))
async def mlbb_create_about_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    about = (message.text or '').strip()
    if len(about) < 20:
        await message.answer('Описание должно быть минимум 20 символов.', reply_markup=my_profiles_create_cancel_keyboard())
        return
    if len(about) > 500:
        await message.answer('Описание слишком длинное. Максимум 500 символов.', reply_markup=my_profiles_create_cancel_keyboard())
        return

    data = await state.get_data()
    await state.update_data(mlbb_about_preview=about)
    data = await state.get_data()
    photo_preview = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_screen_by_ref(
        state,
        message,
        caption=_mlbb_progress_caption(data),
        reply_markup=None,
        photo_file_id=photo_preview or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )

    photo_file_id = data.get('mlbb_photo_file_id')
    game_id = data.get('mlbb_game_id')
    rank = data.get('mlbb_rank')
    server = data.get('mlbb_server')
    main_lane_raw = data.get('mlbb_main_lane')
    extra_raw = data.get('mlbb_extra_lanes') if isinstance(data.get('mlbb_extra_lanes'), list) else []

    if (
        not isinstance(photo_file_id, str)
        or not isinstance(game_id, str)
        or not isinstance(rank, str)
        or not isinstance(server, str)
        or not isinstance(main_lane_raw, str)
    ):
        await message.answer('Не удалось завершить анкету.', reply_markup=my_profiles_create_cancel_keyboard())
        return

    main_lane = _parse_lane(main_lane_raw)
    if main_lane is None:
        await message.answer('Не удалось завершить анкету.', reply_markup=my_profiles_create_cancel_keyboard())
        return

    extra_lanes: list[MlbbLaneCode] = []
    for raw in extra_raw:
        lane = _parse_lane(raw)
        if lane is not None and lane != main_lane:
            extra_lanes.append(lane)
    if not extra_lanes:
        await message.answer('Выберите хотя бы одну дополнительную линию.', reply_markup=my_profiles_create_cancel_keyboard())
        return

    profile = await ProfileService(session).save_mlbb_profile(
        owner_id=user_id,
        game_player_id=game_id,
        profile_image_file_id=photo_file_id,
        rank=rank,
        role=_lane_title(main_lane),
        server=server,
        main_lane=main_lane,
        extra_lanes=extra_lanes,
        description=about,
    )

    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await state.update_data(active_game=GameCode.MLBB.value, active_profile_id=str(profile.id))
    await _edit_screen_by_ref(
        state,
        message,
        caption=_profile_card_text(profile),
        reply_markup=my_profile_details_keyboard(),
        photo_file_id=profile.profile_image_file_id,
    )
    await message.answer('✅ Анкета успешно создана!', reply_markup=my_profiles_hide_notice_keyboard())
    await state.set_state(None)
    await state.update_data(create_mode=None)


@router.callback_query(F.data == CB_MY_PROFILES_EDIT)
async def my_profiles_edit_menu_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    photo_file_id: str | None = None
    game_raw = data.get('active_game')
    if isinstance(game_raw, str):
        try:
            profile = await ProfileService(session).get_profile_for_game(user_id, GameCode(game_raw))
            if profile is not None:
                photo_file_id = profile.profile_image_file_id
        except ValueError:
            photo_file_id = None
    await callback.answer()
    await _edit_screen(
        callback.message,
        caption='<b>⚙️ Выберите, что хотите изменить:</b>',
        reply_markup=my_profiles_edit_fields_keyboard(),
        photo_file_id=photo_file_id,
    )


@router.callback_query(F.data == CB_MY_PROFILES_REFILL)
async def my_profiles_refill_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    profile = await ProfileService(session).get_profile_for_game(user_id, GameCode.MLBB)
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    await state.set_state(ProfilesSectionStates.mlbb_waiting_photo)
    await state.update_data(
        create_game=GameCode.MLBB.value,
        create_mode='refill',
        mlbb_photo_file_id=None,
        mlbb_game_id=None,
        mlbb_rank=None,
        mlbb_main_lane=None,
        mlbb_extra_lanes=[],
        mlbb_server=None,
        mlbb_about_preview=None,
    )
    await callback.answer()
    await _edit_screen(
        callback.message,
        caption=_mlbb_progress_caption(await state.get_data()),
        reply_markup=None,
        photo_file_id=MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await _remember_message(state, callback.message)
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        "📸 <b>Отправьте скриншот вашей анкеты из игры.</b>\n\n"
        "Это поможет другим игрокам быстрее вас узнать.",
        reply_markup=my_profiles_create_cancel_keyboard(),
    )
    await _remember_prompt_message(state, prompt)


@router.callback_query(F.data.startswith(CB_MY_PROFILES_EDIT_FIELD_PREFIX))
async def my_profiles_edit_field_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    field = (callback.data or '').replace(CB_MY_PROFILES_EDIT_FIELD_PREFIX, '', 1)
    profile = await ProfileService(session).get_profile_for_game(user_id, GameCode.MLBB)
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)

    if field == 'photo':
        await state.set_state(ProfilesSectionStates.edit_waiting_photo)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '🖼 <b>Отправьте новую картинку анкеты.</b>',
            reply_markup=my_profiles_edit_cancel_keyboard(),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'id':
        await state.set_state(ProfilesSectionStates.edit_waiting_id)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '<b>🆔 Введите ваши ID из игры:</b>\n\nПример: <code>1129099628(13762)</code>',
            reply_markup=my_profiles_edit_cancel_keyboard(),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'rank':
        await state.set_state(ProfilesSectionStates.edit_waiting_rank)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '🎖 <b>Выберите новый ранг:</b>',
            reply_markup=my_profiles_mlbb_rank_keyboard(cancel_callback=CB_MY_PROFILES_EDIT_CANCEL),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'role':
        await state.set_state(ProfilesSectionStates.edit_waiting_main_lane)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '🛡 <b>Выберите новую основную линию:</b>',
            reply_markup=my_profiles_mlbb_main_lane_keyboard(
                i18n,
                locale,
                cancel_callback=CB_MY_PROFILES_EDIT_CANCEL,
            ),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'extra_lanes':
        selected: set[MlbbLaneCode] = set()
        for raw in profile.extra_lanes or []:
            lane = _parse_lane(raw)
            if lane is not None:
                selected.add(lane)
        excluded_main = {profile.main_lane} if profile.main_lane is not None else set()
        selected = {lane for lane in selected if lane not in excluded_main}
        await state.set_state(ProfilesSectionStates.edit_waiting_extra_lanes)
        await state.update_data(edit_field=field, edit_extra_lanes=[lane.value for lane in selected])
        prompt = await callback.message.answer(
            '🎯 <b>Выберите дополнительные линии:</b>\n<i>Можно выбрать несколько</i>',
            reply_markup=my_profiles_mlbb_extra_lanes_keyboard(
                i18n,
                locale,
                selected=selected,
                excluded_lanes=excluded_main,
                cancel_callback=CB_MY_PROFILES_EDIT_CANCEL,
            ),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'server':
        await state.set_state(ProfilesSectionStates.edit_waiting_server)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '🌍 <b>Выберите новый регион в игре:</b>',
            reply_markup=my_profiles_mlbb_server_keyboard(cancel_callback=CB_MY_PROFILES_EDIT_CANCEL),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'about':
        await state.set_state(ProfilesSectionStates.edit_waiting_about)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '📝 <b>Введите новое описание анкеты:</b>',
            reply_markup=my_profiles_edit_cancel_keyboard(),
        )
        await _remember_prompt_message(state, prompt)
        return

    await callback.answer('Это поле пока недоступно', show_alert=True)


@router.callback_query(
    F.data == CB_MY_PROFILES_EDIT_CANCEL,
    StateFilter(
        ProfilesSectionStates.edit_waiting_photo,
        ProfilesSectionStates.edit_waiting_id,
        ProfilesSectionStates.edit_waiting_rank,
        ProfilesSectionStates.edit_waiting_main_lane,
        ProfilesSectionStates.edit_waiting_extra_lanes,
        ProfilesSectionStates.edit_waiting_server,
        ProfilesSectionStates.edit_waiting_about,
    ),
)
async def my_profiles_edit_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await state.set_state(None)
    await state.update_data(edit_field=None, edit_extra_lanes=[])
    await _render_active_profile_by_ref(state, callback.message, user_id, session)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_photo), F.photo | F.document)
async def my_profiles_edit_photo_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    photo_file_id = _message_image_file_id(message)
    if photo_file_id is None:
        notice = await message.answer('Пожалуйста, отправьте изображение.')
        await _remember_temp_notice(state, notice)
        return
    profile = await ProfileService(session).update_mlbb_profile_fields(owner_id=user_id, profile_image_file_id=photo_file_id)
    if profile is None:
        await message.answer('Анкета не найдена.')
        return

    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _finalize_profile_edit_success(state, message, session, user_id)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_photo))
async def my_profiles_edit_photo_invalid_handler(message: Message, state: FSMContext) -> None:
    notice = await message.answer('Пожалуйста, отправьте изображение.')
    await _remember_temp_notice(state, notice)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_id))
async def my_profiles_edit_id_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    game_id_raw = (message.text or '').strip()
    if not is_valid_mlbb_player_id(game_id_raw):
        notice = await message.answer('❌ <b>Неверный формат ID.</b>\n\nВведите в формате:\n<code>1129099628(13762)</code>')
        await _remember_temp_notice(state, notice)
        return
    if await ProfileService(session).mlbb_id_exists(game_id_raw, exclude_owner_id=user_id):
        notice = await message.answer('⚠️ Такой MLBB ID уже используется.\nВведите другой ID.')
        await _remember_temp_notice(state, notice)
        return

    profile = await ProfileService(session).update_mlbb_profile_fields(owner_id=user_id, game_player_id=game_id_raw)
    if profile is None:
        await message.answer('Анкета не найдена.')
        return

    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _finalize_profile_edit_success(state, message, session, user_id)


@router.callback_query(
    StateFilter(ProfilesSectionStates.edit_waiting_rank),
    F.data.startswith(CB_MY_PROFILES_MLBB_RANK_PREFIX),
)
async def my_profiles_edit_rank_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    rank = (callback.data or '').replace(CB_MY_PROFILES_MLBB_RANK_PREFIX, '', 1).strip()
    if rank not in {'Мастер', 'Грандмастер', 'Эпический', 'Легендарный', 'Мифический'}:
        await callback.answer('Неверный ранг', show_alert=True)
        return

    profile = await ProfileService(session).update_mlbb_profile_fields(owner_id=user_id, rank=rank)
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    await _finalize_profile_edit_success(state, callback.message, session, user_id)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_rank))
async def my_profiles_edit_rank_invalid_handler(message: Message, state: FSMContext) -> None:
    notice = await message.answer('Выберите ранг кнопками ниже.')
    await _remember_temp_notice(state, notice)


@router.callback_query(
    StateFilter(ProfilesSectionStates.edit_waiting_main_lane),
    F.data.startswith(CB_MY_PROFILES_MLBB_MAIN_PREFIX),
)
async def my_profiles_edit_main_lane_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    lane_raw = (callback.data or '').replace(CB_MY_PROFILES_MLBB_MAIN_PREFIX, '', 1)
    lane = _parse_lane(lane_raw)
    if lane is None or lane == MlbbLaneCode.ALL:
        await callback.answer('Неверная линия', show_alert=True)
        return

    profile = await ProfileService(session).update_mlbb_profile_fields(
        owner_id=user_id,
        main_lane=lane,
        role=_lane_title(lane),
    )
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    await _finalize_profile_edit_success(state, callback.message, session, user_id)


@router.callback_query(
    StateFilter(ProfilesSectionStates.edit_waiting_extra_lanes),
    F.data.startswith(CB_MY_PROFILES_MLBB_EXTRA_PREFIX),
    F.data != CB_MY_PROFILES_MLBB_EXTRA_DONE,
)
async def my_profiles_edit_extra_lane_toggle_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    profile = await ProfileService(session).get_profile_for_game(user_id, GameCode.MLBB)
    excluded_main = {profile.main_lane} if profile is not None and profile.main_lane is not None else set()
    lane_raw = (callback.data or '').replace(CB_MY_PROFILES_MLBB_EXTRA_PREFIX, '', 1)
    lane = _parse_lane(lane_raw)
    if lane is None or lane in excluded_main:
        await callback.answer('Неверная линия', show_alert=True)
        return

    data = await state.get_data()
    selected_raw = data.get('edit_extra_lanes') if isinstance(data.get('edit_extra_lanes'), list) else []
    selected: set[MlbbLaneCode] = set()
    for raw in selected_raw:
        parsed = _parse_lane(raw)
        if parsed is not None:
            selected.add(parsed)

    if lane in selected:
        selected.remove(lane)
    else:
        selected.add(lane)

    await state.update_data(edit_extra_lanes=[value.value for value in selected])
    await callback.answer()
    await callback.message.edit_text(
        '🎯 <b>Выберите дополнительные линии:</b>\n<i>Можно выбрать несколько</i>',
        reply_markup=my_profiles_mlbb_extra_lanes_keyboard(
            i18n,
            locale,
            selected=selected,
            excluded_lanes=excluded_main,
            cancel_callback=CB_MY_PROFILES_EDIT_CANCEL,
        ),
    )


@router.callback_query(StateFilter(ProfilesSectionStates.edit_waiting_extra_lanes), F.data == CB_MY_PROFILES_MLBB_EXTRA_DONE)
async def my_profiles_edit_extra_done_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    extra_raw = data.get('edit_extra_lanes') if isinstance(data.get('edit_extra_lanes'), list) else []

    extra_lanes: list[MlbbLaneCode] = []
    for raw in extra_raw:
        lane = _parse_lane(raw)
        if lane is not None:
            extra_lanes.append(lane)
    if not extra_lanes:
        await callback.answer('Выберите хотя бы одну дополнительную линию', show_alert=True)
        return

    profile = await ProfileService(session).update_mlbb_profile_fields(
        owner_id=user_id,
        extra_lanes=[lane.value for lane in extra_lanes],
    )
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    await _finalize_profile_edit_success(state, callback.message, session, user_id)


@router.callback_query(
    StateFilter(ProfilesSectionStates.edit_waiting_server),
    F.data.startswith(CB_MY_PROFILES_MLBB_SERVER_PREFIX),
)
async def my_profiles_edit_server_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    server = (callback.data or '').replace(CB_MY_PROFILES_MLBB_SERVER_PREFIX, '', 1).strip()
    if server not in {'UZ', 'RU', 'EU'}:
        await callback.answer('Неверный сервер', show_alert=True)
        return

    profile = await ProfileService(session).update_mlbb_profile_fields(owner_id=user_id, play_time=server)
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    await _finalize_profile_edit_success(state, callback.message, session, user_id)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_server))
async def my_profiles_edit_server_invalid_handler(message: Message, state: FSMContext) -> None:
    notice = await message.answer('Выберите регион кнопками ниже.')
    await _remember_temp_notice(state, notice)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_about))
async def my_profiles_edit_about_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    about = (message.text or '').strip()
    if len(about) < 20:
        notice = await message.answer('Описание должно быть минимум 20 символов.')
        await _remember_temp_notice(state, notice)
        return
    if len(about) > 500:
        notice = await message.answer('Описание слишком длинное. Максимум 500 символов.')
        await _remember_temp_notice(state, notice)
        return

    profile = await ProfileService(session).update_mlbb_profile_fields(owner_id=user_id, description=about, about=about)
    if profile is None:
        await message.answer('Анкета не найдена.')
        return

    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _finalize_profile_edit_success(state, message, session, user_id)


@router.callback_query(F.data == CB_MY_PROFILES_DELETE_ASK)
async def my_profiles_delete_ask_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    game_raw = data.get('active_game')
    game_title = _game_title(GameCode(game_raw)) if isinstance(game_raw, str) else 'эту игру'

    await callback.answer()
    await _edit_screen(
        callback.message,
        caption=(
            '⚠️ <b>Удаление анкеты</b>\n\n'
            f'Вы уверены, что хотите удалить анкету <b>{game_title}</b>?'
        ),
        reply_markup=my_profiles_delete_confirm_keyboard(),
        photo_path=DELETE_PROFILE_PHOTO_PATH,
    )


@router.callback_query(F.data == CB_MY_PROFILES_DELETE_CANCEL)
async def my_profiles_delete_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    game_raw = data.get('active_game')
    if isinstance(game_raw, str):
        try:
            game = GameCode(game_raw)
            await callback.answer()
            await _render_profile_card(message=callback.message, state=state, user_id=user_id, game=game, session=session)
            return
        except ValueError:
            pass

    await callback.answer()
    await _render_dashboard(message=callback.message, state=state, user_id=user_id, session=session, use_edit=True)


@router.callback_query(F.data == CB_MY_PROFILES_DELETE_CONFIRM)
async def my_profiles_delete_confirm_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    profile_id_raw = data.get('active_profile_id')

    deleted = False
    if isinstance(profile_id_raw, str):
        from uuid import UUID

        try:
            deleted = await ProfileService(session).delete_owned_profile(user_id, UUID(profile_id_raw))
        except ValueError:
            deleted = False

    await callback.answer('Анкета удалена' if deleted else 'Анкета не найдена', show_alert=not deleted)
    await _render_dashboard(message=callback.message, state=state, user_id=user_id, session=session, use_edit=True)
