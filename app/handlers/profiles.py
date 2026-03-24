import uuid

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode, MlbbLaneCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.filters import LocalizedTextFilter
from app.handlers.states import MlbbProfileStates
from app.keyboards import (
    create_profile_for_game_keyboard,
    delete_confirmation_keyboard,
    language_keyboard,
    mlbb_extra_lanes_keyboard,
    mlbb_main_lane_keyboard,
    my_profile_actions_keyboard,
    my_profiles_games_keyboard,
)
from app.locales import LocalizationManager
from app.models import PlayerProfile
from app.services import ProfileService
from app.utils import (
    DESCRIPTION_MAX_LENGTH,
    DESCRIPTION_MIN_LENGTH,
    format_generic_profile_card,
    format_mlbb_profile_card,
    format_profiles_status,
    is_valid_mlbb_player_id,
    is_valid_profile_description,
    lane_label,
)

router = Router(name='profiles')


def _parse_game(value: str) -> GameCode | None:
    try:
        return GameCode(value)
    except ValueError:
        return None


def _parse_profile_id(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _lanes_from_state(raw_values: list[str] | None) -> set[MlbbLaneCode]:
    if not raw_values:
        return set()

    lanes: set[MlbbLaneCode] = set()
    for raw in raw_values:
        try:
            lanes.add(MlbbLaneCode(raw))
        except ValueError:
            continue
    return lanes


def _extra_lanes_text(i18n: LocalizationManager, locale: str, selected: set[MlbbLaneCode]) -> str:
    if selected:
        selected_text = ', '.join(lane_label(i18n, locale, lane) for lane in selected)
    else:
        selected_text = i18n.t(locale, 'value.not_set')

    return (
        f"{i18n.t(locale, 'mlbb.extra_lanes.prompt')}\n\n"
        f"{i18n.t(locale, 'mlbb.extra_lanes.selected', selected=selected_text)}"
    )


async def _send_profiles_dashboard(
    message: Message,
    *,
    user_id: int,
    locale: str,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    profile_service = ProfileService(session)
    profiles_by_game = await profile_service.get_profiles_indexed_by_game(user_id)

    await message.answer(
        format_profiles_status(i18n, locale, profiles_by_game),
        reply_markup=my_profiles_games_keyboard(i18n, locale),
    )


async def _send_profile_card_with_actions(
    message: Message,
    *,
    profile: PlayerProfile,
    locale: str,
    i18n: LocalizationManager,
) -> None:
    if profile.game == GameCode.MLBB:
        caption = format_mlbb_profile_card(i18n, locale, profile, title_key='profiles.card.mlbb')
        if profile.profile_image_file_id:
            await message.answer_photo(photo=profile.profile_image_file_id, caption=caption)
        else:
            await message.answer(caption)
    else:
        await message.answer(format_generic_profile_card(i18n, locale, profile))

    await message.answer(
        i18n.t(locale, 'profiles.actions.prompt'),
        reply_markup=my_profile_actions_keyboard(
            i18n,
            locale,
            game=profile.game,
            profile_id=profile.id,
        ),
    )


async def _start_mlbb_fsm(
    *,
    state: FSMContext,
    message: Message,
    locale: str,
    i18n: LocalizationManager,
    start_key: str,
) -> None:
    await state.clear()
    await state.update_data(extra_lanes=[])
    await state.set_state(MlbbProfileStates.game_player_id)

    await message.answer(i18n.t(locale, start_key))
    await message.answer(i18n.t(locale, 'mlbb.id.prompt'))


@router.message(LocalizedTextFilter('menu.my_profiles'))
async def my_profiles_handler(
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

    await _send_profiles_dashboard(message, user_id=user_id, locale=locale, session=session, i18n=i18n)


@router.callback_query(F.data == 'my_profiles:open')
async def my_profiles_open_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await _send_profiles_dashboard(callback.message, user_id=user_id, locale=locale, session=session, i18n=i18n)


@router.callback_query(F.data.startswith('my_profiles:game:'))
async def my_profiles_game_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    game_raw = (callback.data or '').split(':')[-1]
    game = _parse_game(game_raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    profile = await ProfileService(session).get_profile_for_game(user_id, game)

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if profile is None:
        await callback.message.answer(
            i18n.t(locale, 'profiles.game.not_created', game=i18n.t(locale, f'game.{game.value}')),
            reply_markup=create_profile_for_game_keyboard(i18n, locale, game),
        )
        return

    await _send_profile_card_with_actions(callback.message, profile=profile, locale=locale, i18n=i18n)


@router.callback_query(F.data.startswith('my_profiles:create:'))
async def my_profiles_create_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    game_raw = (callback.data or '').split(':')[-1]
    game = _parse_game(game_raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    profile_service = ProfileService(session)
    profile, created = await profile_service.create_profile_or_get_existing(user_id, game)

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if game == GameCode.MLBB:
        await _start_mlbb_fsm(
            state=state,
            message=callback.message,
            locale=locale,
            i18n=i18n,
            start_key='mlbb.start.create',
        )
        return

    if created:
        await callback.message.answer(i18n.t(locale, 'profile.created.generic', game=i18n.t(locale, f'game.{game.value}')))
    else:
        await callback.message.answer(i18n.t(locale, 'profile.updated.generic', game=i18n.t(locale, f'game.{game.value}')))

    await _send_profile_card_with_actions(callback.message, profile=profile, locale=locale, i18n=i18n)


@router.callback_query(F.data.startswith('my_profiles:edit:'))
async def my_profiles_edit_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    game_raw = (callback.data or '').split(':')[-1]
    game = _parse_game(game_raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    profile_service = ProfileService(session)
    profile = await profile_service.get_profile_for_game(user_id, game)

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if profile is None:
        await callback.message.answer(i18n.t(locale, 'profile.not_found'))
        return

    if game == GameCode.MLBB:
        await _start_mlbb_fsm(
            state=state,
            message=callback.message,
            locale=locale,
            i18n=i18n,
            start_key='mlbb.start.edit',
        )
        return

    await _send_profile_card_with_actions(callback.message, profile=profile, locale=locale, i18n=i18n)


@router.callback_query(F.data.startswith('my_profiles:refill:'))
async def my_profiles_refill_handler(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    game_raw = (callback.data or '').split(':')[-1]
    game = _parse_game(game_raw)
    if game is None:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    reset_done = await ProfileService(session).reset_by_owner_and_game(user_id, game)

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if not reset_done:
        await callback.message.answer(i18n.t(locale, 'profile.not_found'))
        return

    if game == GameCode.MLBB:
        await _start_mlbb_fsm(
            state=state,
            message=callback.message,
            locale=locale,
            i18n=i18n,
            start_key='mlbb.start.refill',
        )
        return

    profile = await ProfileService(session).get_profile_for_game(user_id, game)
    if profile is None:
        await callback.message.answer(i18n.t(locale, 'profile.not_found'))
        return

    await callback.message.answer(i18n.t(locale, 'profile.updated.generic', game=i18n.t(locale, f'game.{game.value}')))
    await _send_profile_card_with_actions(callback.message, profile=profile, locale=locale, i18n=i18n)


@router.callback_query(F.data.startswith('my_profiles:delete_ask:'))
async def my_profiles_delete_ask_handler(
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

    profile_id_raw = (callback.data or '').split(':')[-1]
    profile_id = _parse_profile_id(profile_id_raw)
    if profile_id is None:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            i18n.t(locale, 'profile.delete.confirm'),
            reply_markup=delete_confirmation_keyboard(i18n, locale, profile_id=profile_id),
        )


@router.callback_query(F.data.startswith('my_profiles:delete_yes:'))
async def my_profiles_delete_yes_handler(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    profile_id_raw = (callback.data or '').split(':')[-1]
    profile_id = _parse_profile_id(profile_id_raw)
    if profile_id is None:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    deleted = await ProfileService(session).delete_owned_profile(user_id, profile_id)

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if not deleted:
        await callback.message.answer(i18n.t(locale, 'profile.not_found'))
        return

    await callback.message.answer(i18n.t(locale, 'profile.deleted'))
    await _send_profiles_dashboard(callback.message, user_id=user_id, locale=locale, session=session, i18n=i18n)


@router.callback_query(F.data == 'my_profiles:delete_no')
async def my_profiles_delete_no_handler(callback: CallbackQuery, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(i18n.t(locale, 'profile.delete.canceled'))


@router.message(StateFilter(MlbbProfileStates.game_player_id))
async def mlbb_game_player_id_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return

    _, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        return

    value = message.text or ''
    if not is_valid_mlbb_player_id(value):
        await message.answer(i18n.t(locale, 'mlbb.id.invalid'))
        return

    await state.update_data(game_player_id=value.strip())
    await state.set_state(MlbbProfileStates.profile_image)
    await message.answer(i18n.t(locale, 'mlbb.image.prompt'))


@router.message(StateFilter(MlbbProfileStates.profile_image))
async def mlbb_profile_image_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return

    _, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        return

    image_file_id: str | None = None

    if message.photo:
        image_file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
        image_file_id = message.document.file_id

    if image_file_id is None:
        await message.answer(i18n.t(locale, 'mlbb.image.invalid'))
        return

    await state.update_data(profile_image_file_id=image_file_id)
    await state.set_state(MlbbProfileStates.main_lane)
    await message.answer(
        i18n.t(locale, 'mlbb.main_lane.prompt'),
        reply_markup=mlbb_main_lane_keyboard(i18n, locale),
    )


@router.callback_query(StateFilter(MlbbProfileStates.main_lane), F.data.startswith('mlbb:main_lane:'))
async def mlbb_main_lane_handler(
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

    lane_raw = (callback.data or '').split(':')[-1]
    try:
        lane = MlbbLaneCode(lane_raw)
    except ValueError:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    if lane == MlbbLaneCode.ALL:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    await state.update_data(main_lane=lane.value, extra_lanes=[])
    await state.set_state(MlbbProfileStates.extra_lanes)

    await callback.answer()
    if isinstance(callback.message, Message):
        selected = _lanes_from_state([])
        await callback.message.answer(
            _extra_lanes_text(i18n, locale, selected),
            reply_markup=mlbb_extra_lanes_keyboard(i18n, locale, selected=selected),
        )


@router.callback_query(StateFilter(MlbbProfileStates.extra_lanes), F.data.startswith('mlbb:extra_toggle:'))
async def mlbb_extra_lanes_toggle_handler(
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

    lane_raw = (callback.data or '').split(':')[-1]
    try:
        lane = MlbbLaneCode(lane_raw)
    except ValueError:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    data = await state.get_data()
    selected = _lanes_from_state(data.get('extra_lanes'))

    if lane == MlbbLaneCode.ALL:
        selected = {MlbbLaneCode.ALL}
    else:
        selected.discard(MlbbLaneCode.ALL)
        if lane in selected:
            selected.remove(lane)
        else:
            selected.add(lane)

    await state.update_data(extra_lanes=[item.value for item in selected])

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            _extra_lanes_text(i18n, locale, selected),
            reply_markup=mlbb_extra_lanes_keyboard(i18n, locale, selected=selected),
        )


@router.callback_query(StateFilter(MlbbProfileStates.extra_lanes), F.data == 'mlbb:extra_done')
async def mlbb_extra_lanes_done_handler(
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

    data = await state.get_data()
    selected = _lanes_from_state(data.get('extra_lanes'))
    if not selected:
        await callback.answer(i18n.t(locale, 'mlbb.extra_lanes.need_one'), show_alert=True)
        return

    await state.set_state(MlbbProfileStates.description)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(i18n.t(locale, 'mlbb.description.prompt'))


@router.message(StateFilter(MlbbProfileStates.description))
async def mlbb_description_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return

    owner_id, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        return

    description = (message.text or '').strip()
    if not is_valid_profile_description(description):
        await message.answer(
            i18n.t(
                locale,
                'mlbb.description.invalid',
                min_len=DESCRIPTION_MIN_LENGTH,
                max_len=DESCRIPTION_MAX_LENGTH,
            )
        )
        return

    data = await state.get_data()

    game_player_id = str(data.get('game_player_id', '')).strip()
    profile_image_file_id = str(data.get('profile_image_file_id', '')).strip()
    main_lane_raw = str(data.get('main_lane', '')).strip()
    extra_lanes_raw = data.get('extra_lanes') if isinstance(data.get('extra_lanes'), list) else []

    if not game_player_id or not profile_image_file_id or not main_lane_raw:
        await message.answer(i18n.t(locale, 'error.unknown'))
        await state.clear()
        return

    try:
        main_lane = MlbbLaneCode(main_lane_raw)
        extra_lanes = [MlbbLaneCode(item) for item in extra_lanes_raw]
    except ValueError:
        await message.answer(i18n.t(locale, 'error.unknown'))
        await state.clear()
        return

    profile = await ProfileService(session).save_mlbb_profile(
        owner_id=owner_id,
        game_player_id=game_player_id,
        profile_image_file_id=profile_image_file_id,
        main_lane=main_lane,
        extra_lanes=extra_lanes,
        description=description,
    )

    await state.clear()

    await message.answer(i18n.t(locale, 'mlbb.saved'))
    await _send_profile_card_with_actions(message, profile=profile, locale=locale, i18n=i18n)


@router.message(StateFilter(MlbbProfileStates.main_lane, MlbbProfileStates.extra_lanes))
async def mlbb_state_text_guard(message: Message, session: AsyncSession, i18n: LocalizationManager) -> None:
    if message.from_user is None:
        return

    _, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        return

    await message.answer(i18n.t(locale, 'error.unknown'))
