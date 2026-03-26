from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    BTN_MY_PROFILES,
    CB_MY_PROFILES_BACK,
    CB_MY_PROFILES_CREATE_CANCEL,
    CB_MY_PROFILES_CREATE_MENU,
    CB_MY_PROFILES_CREATE_PICK_PREFIX,
    CB_MY_PROFILES_DELETE_ASK,
    CB_MY_PROFILES_DELETE_CANCEL,
    CB_MY_PROFILES_DELETE_CONFIRM,
    CB_MY_PROFILES_EDIT,
    CB_MY_PROFILES_EDIT_FIELD_PREFIX,
    CB_MY_PROFILES_GAME_PREFIX,
    CB_MY_PROFILES_MLBB_EXTRA_DONE,
    CB_MY_PROFILES_MLBB_EXTRA_PREFIX,
    CB_MY_PROFILES_MLBB_MAIN_PREFIX,
    CB_MY_PROFILES_MLBB_RANK_PREFIX,
    CB_MY_PROFILES_MLBB_SERVER_PREFIX,
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
    my_profiles_mlbb_extra_lanes_keyboard,
    my_profiles_mlbb_main_lane_keyboard,
    my_profiles_mlbb_rank_keyboard,
    my_profiles_mlbb_server_keyboard,
)
from app.locales import LocalizationManager
from app.services import ProfileService
from app.utils import is_valid_mlbb_player_id

router = Router(name='profiles_section')

DEFAULT_AVATAR_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'default_avatar.png'
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
    lines = ['<b>Ваши анкеты</b>', '']
    for game in SUPPORTED_GAMES:
        status = 'Создана' if game in profiles_by_game else 'Отсутствует'
        lines.append(f'🎮 {_game_title(game)}: {status}')
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
            f"<b>Анкета: {_game_title(profile.game)}</b>\n\n"
            f"<b>🎮 Игра:</b> {_game_title(profile.game)}\n"
            f"<b>🆔 ID:</b> {_safe(profile.game_player_id)}\n"
            f"<b>🎖 Ранг:</b> {_safe(profile.rank)}\n"
            f"<b>🛡 Роль:</b> {main_role}\n"
            f"<b>🌍 Сервер:</b> {_safe(profile.play_time)}\n"
            f"<b>📝 О себе:</b> {_safe(profile.description)}\n"
            f"<b>🎯 Доп. линии:</b> {extra_roles}"
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


def _photo_media(photo_file_id: str | None):
    if photo_file_id:
        return photo_file_id
    return FSInputFile(DEFAULT_AVATAR_PATH)


async def _edit_screen(message: Message, *, caption: str, reply_markup, photo_file_id: str | None = None) -> None:
    media = InputMediaPhoto(media=_photo_media(photo_file_id), caption=caption, parse_mode='HTML')
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
) -> None:
    ref = await _message_ref(state)
    if ref is None:
        return

    chat_id, message_id = ref
    media = InputMediaPhoto(media=_photo_media(photo_file_id), caption=caption, parse_mode='HTML')
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
    missing_games = [game for game in SUPPORTED_GAMES if game not in profiles_by_game]
    await _edit_screen_by_ref(
        state,
        source_message,
        caption=_dashboard_text(profiles_by_game),
        reply_markup=my_profiles_dashboard_keyboard(created_games=created_games, has_missing=bool(missing_games)),
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
    missing_games = [game for game in SUPPORTED_GAMES if game not in profiles_by_game]

    caption = _dashboard_text(profiles_by_game)
    keyboard = my_profiles_dashboard_keyboard(created_games=created_games, has_missing=bool(missing_games))

    if use_edit:
        await _edit_screen(message, caption=caption, reply_markup=keyboard)
        await _remember_message(state, message)
        return

    sent = await message.answer_photo(photo=FSInputFile(DEFAULT_AVATAR_PATH), caption=caption, reply_markup=keyboard)
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


@router.message(F.text == BTN_MY_PROFILES)
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


@router.callback_query(F.data == CB_MY_PROFILES_CREATE_MENU)
async def my_profiles_create_menu_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    profiles_by_game = await ProfileService(session).get_profiles_indexed_by_game(user_id)
    missing_games = [game for game in SUPPORTED_GAMES if game not in profiles_by_game]

    if not missing_games:
        await callback.answer('Анкеты по всем играм уже созданы', show_alert=True)
        return

    await callback.answer()
    await _edit_screen(
        callback.message,
        caption='<b>Выберите игру для создания анкеты</b>',
        reply_markup=my_profiles_create_game_keyboard(games=missing_games),
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
    await state.update_data(create_game=game.value, mlbb_extra_lanes=[])
    await callback.answer()
    await _edit_screen(
        callback.message,
        caption="<b>🎮 Создание анкеты Mobile Legends</b>",
        reply_markup=None,
    )
    await _remember_message(state, callback.message)
    prompt = await callback.message.answer(
        "Отправьте скриншот вашего профиля из игры.",
        reply_markup=my_profiles_create_cancel_keyboard(),
    )
    await _remember_prompt_message(state, prompt)


@router.callback_query(F.data == CB_MY_PROFILES_CREATE_CANCEL)
async def my_profiles_create_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await state.set_state(None)
    await _render_dashboard_by_ref(state, callback.message, user_id, session)


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_photo), F.photo)
async def mlbb_create_photo_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.from_user is None or not message.photo:
        return

    await ensure_user_and_locale(message.from_user, session)
    photo_file_id = message.photo[-1].file_id
    await state.update_data(mlbb_photo_file_id=photo_file_id)
    await _edit_screen_by_ref(
        state,
        message,
        caption="<b>🎮 Создание анкеты Mobile Legends</b>",
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
        "Введите ваш ID из игры.\n\nПример:\n1129099628(13762)",
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

    _, locale = await ensure_user_and_locale(message.from_user, session)
    locale = locale or i18n.default_locale
    game_id_raw = (message.text or '').strip()
    if not is_valid_mlbb_player_id(game_id_raw):
        await message.answer(
            'Неверный формат ID.\n\nВведите в формате:\n1129099628(13762)',
            reply_markup=my_profiles_create_cancel_keyboard(),
        )
        return

    await state.update_data(mlbb_game_id=game_id_raw)
    await state.set_state(ProfilesSectionStates.mlbb_waiting_rank)
    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    prompt = await message.answer(
        'Выберите ваш ранг.',
        reply_markup=my_profiles_mlbb_rank_keyboard(),
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
    await state.set_state(ProfilesSectionStates.mlbb_waiting_main_lane)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        'Выберите вашу основную линию:',
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
    await state.set_state(ProfilesSectionStates.mlbb_waiting_extra_lanes)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        text='В каких еще линиях вы умеете играть?\n(Можно выбрать несколько)',
        reply_markup=my_profiles_mlbb_extra_lanes_keyboard(i18n, locale, selected=set()),
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
    if lane is None:
        await callback.answer('Неверная линия', show_alert=True)
        return

    data = await state.get_data()
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
        'В каких еще линиях вы умеете играть?\n(Можно выбрать несколько)',
        reply_markup=my_profiles_mlbb_extra_lanes_keyboard(i18n, locale, selected=selected),
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
    for raw in extra_raw:
        lane = _parse_lane(raw)
        if lane is not None:
            extra_lanes.append(lane)

    if not extra_lanes:
        await callback.answer('Выберите хотя бы одну дополнительную линию', show_alert=True)
        return

    await state.update_data(mlbb_extra_lanes=[lane.value for lane in extra_lanes])
    await state.set_state(ProfilesSectionStates.mlbb_waiting_server)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        'Выберите ваш сервер.',
        reply_markup=my_profiles_mlbb_server_keyboard(),
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
    await state.set_state(ProfilesSectionStates.mlbb_waiting_about)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        'Напишите кратко о себе.',
        reply_markup=my_profiles_create_cancel_keyboard(),
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
        if lane is not None:
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
    await message.answer('✅ Анкета успешно создана!')
    await state.set_state(None)


@router.callback_query(F.data == CB_MY_PROFILES_EDIT)
async def my_profiles_edit_menu_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    await ensure_user_and_locale(callback.from_user, session)
    await callback.answer()
    await _edit_screen(
        callback.message,
        caption='<b>Что хотите изменить?</b>',
        reply_markup=my_profiles_edit_fields_keyboard(),
    )


@router.callback_query(F.data.startswith(CB_MY_PROFILES_EDIT_FIELD_PREFIX))
async def my_profiles_edit_field_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    await ensure_user_and_locale(callback.from_user, session)
    field = (callback.data or '').replace(CB_MY_PROFILES_EDIT_FIELD_PREFIX, '', 1)
    await state.set_state(ProfilesSectionStates.editing_profile_field)
    await state.update_data(edit_field=field)
    await callback.answer()
    await _edit_screen(
        callback.message,
        caption=f"<b>Редактирование поля: {field}</b>\n\nFSM для редактирования подготовлен.",
        reply_markup=my_profiles_create_cancel_keyboard(),
    )


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
        caption=f'Вы уверены, что хотите удалить анкету {game_title}?',
        reply_markup=my_profiles_delete_confirm_keyboard(),
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
