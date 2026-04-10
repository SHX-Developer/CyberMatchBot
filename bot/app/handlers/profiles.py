from html import escape
from pathlib import Path
import re
from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    CB_ADMIN_PROFILE_APPROVE_PREFIX,
    CB_ADMIN_PROFILE_DELETE_PREFIX,
    CB_ADMIN_PROFILE_DELETE_REASON_PREFIX,
    CB_ADMIN_PROFILE_REFRESH_PREFIX,
    CB_ADMIN_PROFILE_HIDE_PREFIX,
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
    CB_MY_PROFILES_GENSHIN_REGION_PREFIX,
    CB_MY_PROFILES_MLBB_MAIN_PREFIX,
    CB_MY_PROFILES_PUBG_RANK_PREFIX,
    CB_MY_PROFILES_MLBB_RANK_PREFIX,
    CB_MY_PROFILES_MLBB_SERVER_PREFIX,
    MY_PROFILES_CREATE_IMAGE_FILE_ID,
    MY_PROFILES_DELETE_IMAGE_FILE_ID,
    MY_PROFILES_IMAGE_FILE_ID,
)
from app.database import GameCode, MlbbLaneCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.states import ProfilesSectionStates
from app.keyboards import (
    admin_profile_delete_reason_keyboard,
    admin_profile_review_keyboard,
    language_keyboard,
    my_profile_details_keyboard,
    my_profiles_create_cancel_keyboard,
    my_profiles_create_game_keyboard,
    my_profiles_dashboard_keyboard,
    my_profiles_delete_confirm_keyboard,
    my_profiles_edit_fields_keyboard,
    my_profiles_edit_cancel_keyboard,
    my_profiles_genshin_region_keyboard,
    my_profiles_mlbb_extra_lanes_keyboard,
    my_profiles_hide_notice_keyboard,
    my_profiles_mlbb_main_lane_keyboard,
    my_profiles_pubg_rank_keyboard,
    my_profiles_mlbb_rank_keyboard,
    my_profiles_mlbb_server_keyboard,
)
from app.locales import LocalizationManager
from app.services import ProfileService, UserService
from app.utils import is_valid_mlbb_player_id

router = Router(name='profiles_section')

DEFAULT_AVATAR_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'default_avatar.png'
ASSETS_DIR = Path(__file__).resolve().parent.parent / 'assets'
DASHBOARD_PHOTO_PATH = ASSETS_DIR / 'anketi.png'
CREATE_GAMES_PHOTO_PATH = ASSETS_DIR / 'games.png'
MLBB_CREATE_PHOTO_PATH = ASSETS_DIR / 'mobile_legends.png'
MLBB_CREATE_EXAMPLE_IMAGE_FILE_ID = 'AgACAgIAAxkBAAILxmnWA65xAzMC1K5Vy9weS5Sh_ubRAAJDEmsbc-uxStx8E2uHcht7AQADAgADbQADOwQ'
GENSHIN_CREATE_EXAMPLE_IMAGE_FILE_ID = 'AgACAgIAAxkBAAILxGnWA41Jvu2ohW6pj4OSys1J_zOKAAJCEmsbc-uxSpyTYOSqpMjgAQADAgADbQADOwQ'
PUBG_CREATE_EXAMPLE_IMAGE_FILE_ID = 'AgACAgIAAxkBAAILyGnWA9WK22wFoo6fMkqUpAccbjy1AAJEEmsbc-uxSgSvLgRme-SFAQADAgADbQADOwQ'
SUPPORTED_GAMES = (GameCode.MLBB, GameCode.GENSHIN_IMPACT, GameCode.PUBG_MOBILE)
MODERATION_REVIEW_CHAT_ID = -5122358580
# Для добавления новых модераторов дополняйте этот набор Telegram ID.
MODERATOR_USER_IDS = {
    284929331,
    1340041796,
    622781320,
}
MODERATION_SEARCH_COMMANDS: dict[str, GameCode] = {
    'search_mlbb': GameCode.MLBB,
    'search_gi': GameCode.GENSHIN_IMPACT,
    'search_pubgm': GameCode.PUBG_MOBILE,
}
ADMIN_DELETE_REASONS = {
    'img': 'Картинка не из игры',
    '18p': '18+ контент',
    'spam': 'Спам или реклама',
    'bd': 'Некорректные данные',
    'other': 'Другая причина',
}
GENSHIN_REGION_CODES = {'ASIA', 'EUROPE', 'AMERICA', 'TW_HK_MO'}
PUBG_RANK_CHOICES = {
    'Bronze',
    'Silver',
    'Gold',
    'Platinum',
    'Diamond',
    'Crown',
    'Ace',
    'Ace Master',
    'Ace Dominator',
    'Conqueror',
}
DESCRIPTION_MIN_LENGTH = 10
DESCRIPTION_MAX_LENGTH = 500


def _is_valid_uid(raw: str, *, min_len: int = 6, max_len: int = 20) -> bool:
    value = raw.strip()
    return value.isdigit() and min_len <= len(value) <= max_len


def _adventure_level_value(raw: object) -> int | None:
    if isinstance(raw, int) and 1 <= raw <= 60:
        return raw
    if isinstance(raw, str):
        if not raw.strip().isdigit():
            return None
        value = int(raw.strip())
        if 1 <= value <= 60:
            return value
    return None


def _active_game_from_state(data: dict) -> GameCode:
    raw = data.get('active_game')
    if isinstance(raw, str):
        try:
            return GameCode(raw)
        except ValueError:
            pass
    create_raw = data.get('create_game')
    if isinstance(create_raw, str):
        try:
            return GameCode(create_raw)
        except ValueError:
            pass
    return GameCode.MLBB


def _is_admin(user_id: int | None) -> bool:
    return isinstance(user_id, int) and user_id in MODERATOR_USER_IDS


def _admin_game_from_code(raw: str | None) -> GameCode | None:
    mapping = {
        'm': GameCode.MLBB,
        'g': GameCode.GENSHIN_IMPACT,
        'p': GameCode.PUBG_MOBILE,
    }
    if raw is None:
        return None
    return mapping.get(raw)


def _display_owner_name(owner) -> str:
    if owner is None:
        return 'Не указано'
    if isinstance(owner.full_name, str) and owner.full_name.strip():
        return owner.full_name.strip()
    parts = [item.strip() for item in (owner.first_name, owner.last_name) if isinstance(item, str) and item.strip()]
    if parts:
        return ' '.join(parts)
    return 'Не указано'


def _display_owner_username(owner) -> str:
    if owner is None:
        return 'Не указан'
    if isinstance(owner.username, str) and owner.username.strip():
        return f'@{owner.username.strip()}'
    return 'Не указан'


def _display_owner_language(owner) -> str:
    if owner is None:
        return 'Не указан'
    language = getattr(owner, 'language_code', None)
    if language is None:
        return 'Не указан'
    value = getattr(language, 'value', None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return str(language)


def _moderator_name(callback: CallbackQuery) -> str:
    user = callback.from_user
    if user is None:
        return 'Неизвестный модератор'
    if isinstance(user.full_name, str) and user.full_name.strip():
        return user.full_name.strip()
    username = getattr(user, 'username', None)
    if isinstance(username, str) and username.strip():
        return f'@{username.strip()}'
    return str(getattr(user, 'id', 'Неизвестный модератор'))


async def _send_moderation_group_log(callback: CallbackQuery, text: str) -> None:
    if not isinstance(callback.message, Message):
        return
    try:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            parse_mode='HTML',
        )
    except Exception:
        pass


def _owner_moderation_line(owner, owner_id: int) -> str:
    display_name = escape(_display_owner_name(owner))
    display_username = escape(_display_owner_username(owner))
    return (
        f"👤 {display_name}\n"
        f"🔗 {display_username}\n"
        f"🆔 <code>{owner_id}</code>"
    )


def _recreate_profile_keyboard(game: GameCode):
    builder = InlineKeyboardBuilder()
    builder.button(
        text='🔄 Создать заново',
        callback_data=f'{CB_MY_PROFILES_CREATE_PICK_PREFIX}{game.value}',
    )
    builder.adjust(1)
    return builder.as_markup()


def _parse_admin_profile_payload(payload: str) -> tuple[UUID, int, GameCode | None] | None:
    parts = payload.split(':', 2)
    if len(parts) < 2:
        return None
    raw_profile_id, raw_owner_id = parts[0], parts[1]
    raw_game_code = parts[2] if len(parts) == 3 else None
    try:
        profile_id = UUID(raw_profile_id)
        owner_id = int(raw_owner_id)
    except (TypeError, ValueError):
        return None
    if owner_id <= 0:
        return None
    return profile_id, owner_id, _admin_game_from_code(raw_game_code)


def _parse_admin_reason_payload(payload: str) -> tuple[str, UUID, int, GameCode | None] | None:
    parts = payload.split(':', 3)
    if len(parts) < 3:
        return None
    reason_code, raw_profile_id, raw_owner_id = parts[0], parts[1], parts[2]
    raw_game_code = parts[3] if len(parts) == 4 else None
    if reason_code not in ADMIN_DELETE_REASONS:
        return None
    try:
        profile_id = UUID(raw_profile_id)
        owner_id = int(raw_owner_id)
    except (TypeError, ValueError):
        return None
    if owner_id <= 0:
        return None
    return reason_code, profile_id, owner_id, _admin_game_from_code(raw_game_code)


def _admin_profile_caption(profile, owner, *, event_type: str) -> str:
    details_lines: list[str]
    if profile.game == GameCode.MLBB:
        main_role = _lane_title(profile.main_lane) if profile.main_lane else 'Не указано'
        extra_values: list[str] = []
        for raw in profile.extra_lanes or []:
            lane = _parse_lane(raw)
            if lane is None:
                continue
            extra_values.append(_lane_title(lane))
        extra_roles = ', '.join(extra_values) if extra_values else 'Не указано'
        details_lines = [
            f"<b>🆔 Игровой ID:</b> <code>{escape(_public_game_id(profile.game_player_id))}</code>",
            f"<b>🌍 Регион:</b> {escape(_safe(profile.play_time))}",
            f"<b>🎖 Ранг:</b> {escape(_format_rank(profile.rank, _mythic_stars_value(profile.mythic_stars)))}",
            f"<b>🛡 Основная линия:</b> {escape(main_role)}",
            f"<b>🎯 Доп. линии:</b> {escape(extra_roles)}",
            f"<b>📝 О себе:</b> {escape(_safe(profile.description or profile.about))}",
        ]
    elif profile.game == GameCode.GENSHIN_IMPACT:
        details_lines = [
            f"<b>🆔 UID:</b> <code>{escape(_public_game_id(profile.game_player_id))}</code>",
            f"<b>🌍 Регион:</b> {escape(_genshin_region_label(profile.play_time))}",
            f"<b>⭐ Уровень приключения:</b> {escape(_safe(profile.rank))}",
            f"<b>📝 О себе:</b> {escape(_safe(profile.description or profile.about))}",
        ]
    elif profile.game == GameCode.PUBG_MOBILE:
        details_lines = [
            f"<b>🆔 UID:</b> <code>{escape(_public_game_id(profile.game_player_id))}</code>",
            f"<b>🎖 Ранг:</b> {escape(_safe(profile.rank))}",
            f"<b>📝 О себе:</b> {escape(_safe(profile.description or profile.about))}",
        ]
    else:
        details_lines = [
            f"<b>🆔 Игровой ID:</b> <code>{escape(_public_game_id(profile.game_player_id))}</code>",
            f"<b>📝 О себе:</b> {escape(_safe(profile.description or profile.about))}",
        ]

    event_titles = {
        'created': '🆕 Новая анкета на проверку',
        'updated': '♻️ Анкета изменена: повторная проверка',
        'random': '🎲 Случайная анкета для проверки',
    }
    event_title = event_titles.get(event_type, event_titles['updated'])
    return (
        f"<b>{event_title}</b>\n\n"
        f"<b>👤 Пользователь:</b> {escape(_display_owner_name(owner))}\n"
        f"<b>🆔 Telegram ID:</b> <code>{getattr(owner, 'id', profile.owner_id)}</code>\n"
        f"<b>🔗 Username:</b> {escape(_display_owner_username(owner))}\n"
        f"<b>🌐 Язык:</b> {escape(_display_owner_language(owner))}\n\n"
        f"<b>🎮 Игра:</b> {escape(_game_title(profile.game))}\n"
        + '\n'.join(details_lines)
    )


async def _send_profile_to_admin_review(
    source_message: Message,
    *,
    profile,
    owner,
    event_type: str,
) -> None:
    try:
        await source_message.bot.send_photo(
            chat_id=MODERATION_REVIEW_CHAT_ID,
            photo=_photo_media(profile.profile_image_file_id),
            caption=_admin_profile_caption(profile, owner, event_type=event_type),
            parse_mode='HTML',
            reply_markup=admin_profile_review_keyboard(
                profile_id=profile.id,
                owner_id=profile.owner_id,
                game=profile.game,
            ),
        )
    except Exception:
        pass


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
    if game == GameCode.GENSHIN_IMPACT:
        return 'Genshin Impact'
    if game == GameCode.PUBG_MOBILE:
        return 'PUBG Mobile'
    return 'Неизвестная игра'


def _create_example_image_file_id(game: GameCode) -> str:
    if game == GameCode.MLBB:
        return MLBB_CREATE_EXAMPLE_IMAGE_FILE_ID
    if game == GameCode.GENSHIN_IMPACT:
        return GENSHIN_CREATE_EXAMPLE_IMAGE_FILE_ID
    if game == GameCode.PUBG_MOBILE:
        return PUBG_CREATE_EXAMPLE_IMAGE_FILE_ID
    return MY_PROFILES_CREATE_IMAGE_FILE_ID


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


def _safe(value: str | None) -> str:
    if value and value.strip():
        return value.strip()
    return 'Не указано'


def _public_game_id(value: str | None) -> str:
    raw = _safe(value)
    if raw == 'Не указано':
        return raw
    if '(' in raw:
        trimmed = raw.split('(', 1)[0].strip()
        if trimmed:
            return trimmed
    match = re.match(r'^(\d+)', raw)
    if match is not None:
        return match.group(1)
    return raw


def _mythic_stars_value(raw: object) -> int | None:
    if isinstance(raw, int) and raw > 0:
        return raw
    return None


def _format_rank(rank: str | None, mythic_stars: int | None) -> str:
    value = _safe(rank)
    if rank == 'Мифический' and mythic_stars is not None and mythic_stars > 0:
        return f'{value} ({mythic_stars} ⭐)'
    return value


def _dashboard_text(profiles_by_game: dict[GameCode, object]) -> str:
    lines = ['<b>🎮 Твои игровые анкеты</b>', '']
    for game in SUPPORTED_GAMES:
        if game in profiles_by_game:
            lines.append(f'✅ {_game_title(game)} — готово к поиску')
        else:
            lines.append(f'❌ {_game_title(game)} — не создана')
        lines.append('')
    lines.append('🔥 Создай анкеты и открывай больше возможностей')
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
            f"<b>🆔 ID:</b> {_public_game_id(profile.game_player_id)}\n"
            f"<b>🌍 Регион:</b> {_safe(profile.play_time)}\n\n"
            f"<b>🎖 Ранг:</b> {_format_rank(profile.rank, _mythic_stars_value(profile.mythic_stars))}\n"
            f"<b>🛡 Роль:</b> {main_role}\n"
            f"<b>🎯 Доп. линии:</b> {extra_roles}\n\n"
            f"<b>📝 О себе:</b> {_safe(profile.description)}"
        )
    if profile.game == GameCode.GENSHIN_IMPACT:
        return (
            f"<b>🎮 Анкета: {_game_title(profile.game)}</b>\n\n"
            f"<b>🆔 UID:</b> {_public_game_id(profile.game_player_id)}\n"
            f"<b>🌍 Регион:</b> {_genshin_region_label(profile.play_time)}\n"
            f"<b>⭐ Уровень приключения:</b> {_safe(profile.rank)}\n\n"
            f"<b>📝 О себе:</b> {_safe(profile.description)}"
        )
    if profile.game == GameCode.PUBG_MOBILE:
        return (
            f"<b>🎮 Анкета: {_game_title(profile.game)}</b>\n\n"
            f"<b>🆔 UID:</b> {_public_game_id(profile.game_player_id)}\n"
            f"<b>🎖 Ранг:</b> {_safe(profile.rank)}\n\n"
            f"<b>📝 О себе:</b> {_safe(profile.description)}"
        )

    return (
        f"<b>Анкета: {_game_title(profile.game)}</b>\n\n"
        f"<b>🎮 Игра:</b> {_game_title(profile.game)}\n"
        f"<b>🆔 ID:</b> {_public_game_id(profile.game_player_id)}\n"
        f"<b>🎖 Ранг:</b> {_format_rank(profile.rank, _mythic_stars_value(profile.mythic_stars))}\n"
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

    mythic_stars = _mythic_stars_value(data.get('mlbb_mythic_stars'))
    if isinstance(data.get('mlbb_rank'), str):
        middle_block.append(
            f"<b>🎖 Ранг:</b> {_format_rank(data['mlbb_rank'].strip(), mythic_stars)}"
        )

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


def _genshin_progress_caption(data: dict) -> str:
    lines = ['<b>🎮 Создание анкеты Genshin Impact</b>', '']
    if isinstance(data.get('genshin_uid'), str):
        lines.append(f"<b>🆔 UID:</b> {data['genshin_uid'].strip()}")
    if isinstance(data.get('genshin_region'), str):
        lines.append(f"<b>🌍 Регион:</b> {_genshin_region_label(data['genshin_region'].strip())}")
    level = _adventure_level_value(data.get('genshin_adventure_level'))
    if level is not None:
        lines.append(f"<b>⭐ Уровень приключения:</b> {level}")
    about = data.get('genshin_about_preview')
    if isinstance(about, str) and about.strip():
        lines.extend(['', f"<b>📝 О себе:</b> {about.strip()}"])
    return '\n'.join(lines)


def _pubg_progress_caption(data: dict) -> str:
    lines = ['<b>🎮 Создание анкеты Pubg Mobile</b>', '']
    if isinstance(data.get('pubg_uid'), str):
        lines.append(f"<b>🆔 UID:</b> {data['pubg_uid'].strip()}")
    if isinstance(data.get('pubg_rank'), str):
        lines.append(f"<b>🎖 Ранг:</b> {data['pubg_rank'].strip()}")
    about = data.get('pubg_about_preview')
    if isinstance(about, str) and about.strip():
        lines.extend(['', f"<b>📝 О себе:</b> {about.strip()}"])
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


async def _delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def _cleanup_input_messages(state: FSMContext, message: Message) -> None:
    await _delete_prompt_by_ref(state, message)
    await _delete_user_message(message)


async def _send_error_notice(message: Message, text: str, *, state: FSMContext | None = None) -> Message:
    notice = await message.answer(text, reply_markup=my_profiles_hide_notice_keyboard())
    if state is not None:
        await _remember_temp_notice(state, notice)
    return notice


async def _edit_create_progress_by_ref(
    state: FSMContext,
    source_message: Message,
    *,
    caption: str,
    photo_file_id: str | None,
) -> None:
    await _edit_screen_by_ref(
        state,
        source_message,
        caption=caption,
        reply_markup=my_profiles_create_cancel_keyboard(),
        photo_file_id=photo_file_id,
    )


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
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    await state.set_state(None)
    await state.update_data(edit_field=None, edit_extra_lanes=[])
    profile = await ProfileService(session).get_profile_for_game(user_id, active_game)
    owner = await UserService(session).get_user(user_id)
    if profile is not None and owner is not None:
        await _send_profile_to_admin_review(
            source_message,
            profile=profile,
            owner=owner,
            event_type='updated',
        )
    await source_message.answer('✅ Данные анкеты сохранены.', reply_markup=my_profiles_hide_notice_keyboard())
    await _render_active_profile_by_ref(state, source_message, user_id, session)


@router.message(F.text.in_(BTN_MY_PROFILES_TEXTS))
@router.message(Command('profiles'))
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
        caption='<b>🎮 Выбери игру для создания анкеты</b>',
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

    if game == GameCode.MLBB:
        await state.set_state(ProfilesSectionStates.mlbb_waiting_photo)
        await state.update_data(
            create_game=game.value,
            create_mode='new',
            mlbb_extra_lanes=[],
            mlbb_mythic_stars=None,
        )
        caption = "<b>🎮 Создание анкеты Mobile Legends</b>"
    elif game == GameCode.GENSHIN_IMPACT:
        await state.set_state(ProfilesSectionStates.genshin_waiting_photo)
        await state.update_data(
            create_game=game.value,
            create_mode='new',
            genshin_region=None,
            genshin_adventure_level=None,
        )
        caption = "<b>🎮 Создание анкеты Genshin Impact</b>"
    elif game == GameCode.PUBG_MOBILE:
        await state.set_state(ProfilesSectionStates.pubg_waiting_photo)
        await state.update_data(
            create_game=game.value,
            create_mode='new',
            pubg_rank=None,
        )
        caption = "<b>🎮 Создание анкеты Pubg Mobile</b>"
    else:
        await callback.answer('Для этой игры создание будет добавлено позже', show_alert=True)
        return

    await callback.answer()
    await _edit_screen(
        callback.message,
        caption=caption,
        reply_markup=my_profiles_create_cancel_keyboard(),
        photo_file_id=_create_example_image_file_id(game),
    )
    await _remember_message(state, callback.message)
    prompt = await callback.message.answer(
        "📸 <b>Отправь скриншот своей анкеты из игры</b>\n\n"
        "👀 Это поможет другим игрокам быстрее тебя узнать",
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
        create_game = _active_game_from_state(data)
        profile = await ProfileService(session).get_profile_for_game(user_id, create_game)
        if profile is not None and create_game == GameCode.MLBB:
            is_incomplete = (
                not profile.game_player_id
                or not profile.profile_image_file_id
                or not profile.rank
                or (profile.rank == 'Мифический' and (profile.mythic_stars is None or profile.mythic_stars <= 0))
                or not profile.play_time
                or profile.main_lane is None
                or not profile.extra_lanes
                or not profile.description
            )
            if is_incomplete:
                await ProfileService(session).delete_owned_profile(user_id, profile.id)
    await callback.answer('Окей, отменил 👌', show_alert=False)
    await _delete_prompt_by_ref(state, callback.message)
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
        await _delete_user_message(message)
        await _send_error_notice(message, 'Отправь изображение.')
        return
    await state.update_data(mlbb_photo_file_id=photo_file_id)
    data = await state.get_data()
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_mlbb_progress_caption(data),
        photo_file_id=photo_file_id,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_game_id)
    await _cleanup_input_messages(state, message)
    prompt = await message.answer(
        "<b>🆔 Отправь UID из игры (без Zone ID):</b>\n\nПример: <code>12345767890</code>",
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_photo))
async def mlbb_create_photo_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    await ensure_user_and_locale(message.from_user, session)
    await _delete_user_message(message)
    await _send_error_notice(message, 'Отправь изображение.')


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_game_id))
async def mlbb_create_game_id_handler(message: Message, state: FSMContext, session: AsyncSession, i18n: LocalizationManager) -> None:
    if message.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    locale = locale or i18n.default_locale
    game_id_raw = (message.text or '').strip()
    if not is_valid_mlbb_player_id(game_id_raw):
        await _send_error_notice(
            message,
            '❌ <b>Неверный формат UID.</b>\n\nОтправь только UID без Zone ID.\nПример: <code>12345767890</code>',
        )
        return

    if await ProfileService(session).mlbb_id_exists(game_id_raw, exclude_owner_id=user_id):
        await _send_error_notice(
            message,
            '⚠️ Такой MLBB ID уже используется в другой анкете.\n\n'
            'Введи другой ID.',
        )
        return

    await state.update_data(mlbb_game_id=game_id_raw)
    data = await state.get_data()
    photo_file_id = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_mlbb_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_server)
    await _cleanup_input_messages(state, message)
    prompt = await message.answer(
        '🌍 <b>Выбери свой регион в игре.</b>',
        reply_markup=my_profiles_mlbb_server_keyboard(include_cancel=False),
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
    if rank != 'Мифический':
        await state.update_data(mlbb_mythic_stars=None)
    data = await state.get_data()
    photo_file_id = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        callback.message,
        caption=_mlbb_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    if rank == 'Мифический':
        await state.set_state(ProfilesSectionStates.mlbb_waiting_mythic_stars)
        prompt = await callback.message.answer(
            '⭐ <b>Введи количество звезд (только число):</b>',
        )
        await _remember_prompt_message(state, prompt)
        return

    await state.set_state(ProfilesSectionStates.mlbb_waiting_main_lane)
    prompt = await callback.message.answer(
        '🛡 <b>Выбери свою основную линию:</b>',
        reply_markup=my_profiles_mlbb_main_lane_keyboard(i18n, locale, include_cancel=False),
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_rank))
async def mlbb_create_rank_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    await message.answer('Выбери ранг кнопками ниже.', reply_markup=my_profiles_mlbb_rank_keyboard(include_cancel=False))


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_mythic_stars))
async def mlbb_create_mythic_stars_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return
    _, locale = await ensure_user_and_locale(message.from_user, session)
    locale = locale or i18n.default_locale
    raw = (message.text or '').strip()
    if not raw.isdigit():
        await _send_error_notice(message, 'Введи количество звезд цифрами.')
        return
    stars = int(raw)
    if stars <= 0 or stars > 999:
        await _send_error_notice(message, 'Количество звезд должно быть от 1 до 999.')
        return

    await state.update_data(mlbb_mythic_stars=stars)
    data = await state.get_data()
    photo_file_id = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_mlbb_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_main_lane)
    await _cleanup_input_messages(state, message)
    prompt = await message.answer(
        '🛡 <b>Выбери свою основную линию:</b>',
        reply_markup=my_profiles_mlbb_main_lane_keyboard(i18n, locale, include_cancel=False),
    )
    await _remember_prompt_message(state, prompt)


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
    await _edit_create_progress_by_ref(
        state,
        callback.message,
        caption=_mlbb_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_extra_lanes)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        text='🎯 <b>Выбери дополнительные линии:</b>\n<i>Можно выбрать несколько</i>',
        reply_markup=my_profiles_mlbb_extra_lanes_keyboard(
            i18n,
            locale,
            selected=set(),
            excluded_lanes={lane},
            include_cancel=False,
        ),
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
        '🎯 <b>Выбери дополнительные линии:</b>\n<i>Можно выбрать несколько</i>',
        reply_markup=my_profiles_mlbb_extra_lanes_keyboard(
            i18n,
            locale,
            selected=selected,
            excluded_lanes={main_lane} if main_lane is not None else set(),
            include_cancel=False,
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
        await callback.answer('Выбери хотя бы одну дополнительную линию', show_alert=True)
        return

    await state.update_data(mlbb_extra_lanes=[lane.value for lane in extra_lanes])
    data = await state.get_data()
    photo_file_id = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        callback.message,
        caption=_mlbb_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_about)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        '📝 <b>Добавь описание в анкету:</b>\n\n'
        'Коротко расскажи про стиль игры, роль и когда ты онлайн.',
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
    await _edit_create_progress_by_ref(
        state,
        callback.message,
        caption=_mlbb_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.mlbb_waiting_rank)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        '🎖 <b>Выбери свой ранг:</b>',
        reply_markup=my_profiles_mlbb_rank_keyboard(include_cancel=False),
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_server))
async def mlbb_create_server_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    await message.answer('Выбери сервер кнопками ниже.', reply_markup=my_profiles_mlbb_server_keyboard(include_cancel=False))


@router.message(StateFilter(ProfilesSectionStates.mlbb_waiting_about))
async def mlbb_create_about_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    about = (message.text or '').strip()
    if len(about) < DESCRIPTION_MIN_LENGTH:
        await _send_error_notice(message, f'Описание должно быть минимум {DESCRIPTION_MIN_LENGTH} символов.')
        return
    if len(about) > DESCRIPTION_MAX_LENGTH:
        await _send_error_notice(message, f'Описание слишком длинное. Максимум {DESCRIPTION_MAX_LENGTH} символов.')
        return

    data = await state.get_data()
    await state.update_data(mlbb_about_preview=about)
    data = await state.get_data()
    photo_preview = data.get('mlbb_photo_file_id') if isinstance(data.get('mlbb_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_mlbb_progress_caption(data),
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
        await _send_error_notice(message, 'Не получилось завершить анкету. Попробуй ещё раз.')
        return

    main_lane = _parse_lane(main_lane_raw)
    if main_lane is None:
        await _send_error_notice(message, 'Не получилось завершить анкету. Попробуй ещё раз.')
        return

    extra_lanes: list[MlbbLaneCode] = []
    for raw in extra_raw:
        lane = _parse_lane(raw)
        if lane is not None and lane != main_lane:
            extra_lanes.append(lane)
    if not extra_lanes:
        await _send_error_notice(message, 'Выбери хотя бы одну дополнительную линию.')
        return

    mythic_stars_raw = data.get('mlbb_mythic_stars')
    mythic_stars = int(mythic_stars_raw) if isinstance(mythic_stars_raw, int) and mythic_stars_raw > 0 else None

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
        mythic_stars=mythic_stars if rank == 'Мифический' else None,
    )
    create_mode = data.get('create_mode') if isinstance(data.get('create_mode'), str) else 'new'
    event_type = 'created' if create_mode == 'new' else 'updated'
    owner = await UserService(session).get_user(user_id)
    if owner is not None:
        await _send_profile_to_admin_review(
            message,
            profile=profile,
            owner=owner,
            event_type=event_type,
        )

    await _cleanup_input_messages(state, message)

    await state.update_data(active_game=GameCode.MLBB.value, active_profile_id=str(profile.id))
    await _edit_screen_by_ref(
        state,
        message,
        caption=_profile_card_text(profile),
        reply_markup=my_profile_details_keyboard(),
        photo_file_id=profile.profile_image_file_id,
    )
    await message.answer('✅ Анкета готова к поиску', reply_markup=my_profiles_hide_notice_keyboard())
    await state.set_state(None)
    await state.update_data(create_mode=None)


@router.message(StateFilter(ProfilesSectionStates.genshin_waiting_photo), F.photo | F.document)
async def genshin_create_photo_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    photo_file_id = _message_image_file_id(message)
    if photo_file_id is None:
        await _delete_user_message(message)
        await _send_error_notice(message, 'Отправь изображение.')
        return
    await state.update_data(genshin_photo_file_id=photo_file_id)
    data = await state.get_data()
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_genshin_progress_caption(data),
        photo_file_id=photo_file_id,
    )
    await state.set_state(ProfilesSectionStates.genshin_waiting_uid)
    await _cleanup_input_messages(state, message)
    prompt = await message.answer(
        '<b>🆔 Отправь UID из игры:</b>\n\nПример: <code>712345678</code>',
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.genshin_waiting_photo))
async def genshin_create_photo_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    await _delete_user_message(message)
    await _send_error_notice(message, 'Отправь изображение.')


@router.message(StateFilter(ProfilesSectionStates.genshin_waiting_uid))
async def genshin_create_uid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    uid = (message.text or '').strip()
    if not _is_valid_uid(uid, min_len=8, max_len=12):
        await _send_error_notice(
            message,
            '❌ <b>Неверный формат UID.</b>\n\nВведи только цифры.\nПример: <code>712345678</code>',
        )
        return
    if await ProfileService(session).game_id_exists(game=GameCode.GENSHIN_IMPACT, game_player_id=uid, exclude_owner_id=user_id):
        await _send_error_notice(message, '⚠️ Такой UID уже используется в другой анкете.')
        return
    await state.update_data(genshin_uid=uid)
    data = await state.get_data()
    photo_file_id = data.get('genshin_photo_file_id') if isinstance(data.get('genshin_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_genshin_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.genshin_waiting_region)
    await _cleanup_input_messages(state, message)
    prompt = await message.answer(
        '🌍 <b>Выбери свой регион:</b>',
        reply_markup=my_profiles_genshin_region_keyboard(include_cancel=False),
    )
    await _remember_prompt_message(state, prompt)


@router.callback_query(
    StateFilter(ProfilesSectionStates.genshin_waiting_region),
    F.data.startswith(CB_MY_PROFILES_GENSHIN_REGION_PREFIX),
)
async def genshin_create_region_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    await ensure_user_and_locale(callback.from_user, session)
    code = (callback.data or '').replace(CB_MY_PROFILES_GENSHIN_REGION_PREFIX, '', 1).strip()
    if code not in GENSHIN_REGION_CODES:
        await callback.answer('Неверный регион', show_alert=True)
        return
    await state.update_data(genshin_region=code)
    data = await state.get_data()
    photo_file_id = data.get('genshin_photo_file_id') if isinstance(data.get('genshin_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        callback.message,
        caption=_genshin_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.genshin_waiting_adventure_level)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        '⭐ <b>Введи уровень приключения (1-60):</b>',
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.genshin_waiting_region))
async def genshin_create_region_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    await message.answer('Выбери регион кнопками ниже.', reply_markup=my_profiles_genshin_region_keyboard(include_cancel=False))


@router.message(StateFilter(ProfilesSectionStates.genshin_waiting_adventure_level))
async def genshin_create_level_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    raw = (message.text or '').strip()
    if not raw.isdigit():
        await _send_error_notice(message, 'Введи уровень цифрами от 1 до 60.')
        return
    level = int(raw)
    if not (1 <= level <= 60):
        await _send_error_notice(message, 'Уровень приключения должен быть от 1 до 60.')
        return
    await state.update_data(genshin_adventure_level=level)
    data = await state.get_data()
    photo_file_id = data.get('genshin_photo_file_id') if isinstance(data.get('genshin_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_genshin_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.genshin_waiting_about)
    await _cleanup_input_messages(state, message)
    prompt = await message.answer(
        '📝 <b>Добавь описание в анкету:</b>',
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.genshin_waiting_about))
async def genshin_create_about_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    about = (message.text or '').strip()
    if len(about) < DESCRIPTION_MIN_LENGTH:
        await _send_error_notice(message, f'Описание должно быть минимум {DESCRIPTION_MIN_LENGTH} символов.')
        return
    if len(about) > DESCRIPTION_MAX_LENGTH:
        await _send_error_notice(message, f'Описание слишком длинное. Максимум {DESCRIPTION_MAX_LENGTH} символов.')
        return
    await state.update_data(genshin_about_preview=about)
    data = await state.get_data()
    photo_preview = data.get('genshin_photo_file_id') if isinstance(data.get('genshin_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_genshin_progress_caption(data),
        photo_file_id=photo_preview or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    photo_file_id = data.get('genshin_photo_file_id')
    uid = data.get('genshin_uid')
    region = data.get('genshin_region')
    level = _adventure_level_value(data.get('genshin_adventure_level'))
    if not isinstance(photo_file_id, str) or not isinstance(uid, str) or not isinstance(region, str) or level is None:
        await _send_error_notice(message, 'Не получилось завершить анкету. Попробуй ещё раз.')
        return
    profile = await ProfileService(session).save_genshin_profile(
        owner_id=user_id,
        game_player_id=uid,
        profile_image_file_id=photo_file_id,
        region=region,
        adventure_level=level,
        description=about,
    )
    create_mode = data.get('create_mode') if isinstance(data.get('create_mode'), str) else 'new'
    event_type = 'created' if create_mode == 'new' else 'updated'
    owner = await UserService(session).get_user(user_id)
    if owner is not None:
        await _send_profile_to_admin_review(
            message,
            profile=profile,
            owner=owner,
            event_type=event_type,
        )
    await _cleanup_input_messages(state, message)
    await state.update_data(active_game=GameCode.GENSHIN_IMPACT.value, active_profile_id=str(profile.id))
    await _edit_screen_by_ref(
        state,
        message,
        caption=_profile_card_text(profile),
        reply_markup=my_profile_details_keyboard(),
        photo_file_id=profile.profile_image_file_id,
    )
    await message.answer('✅ Анкета готова к поиску', reply_markup=my_profiles_hide_notice_keyboard())
    await state.set_state(None)
    await state.update_data(create_mode=None)


@router.message(StateFilter(ProfilesSectionStates.pubg_waiting_photo), F.photo | F.document)
async def pubg_create_photo_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    photo_file_id = _message_image_file_id(message)
    if photo_file_id is None:
        await _delete_user_message(message)
        await _send_error_notice(message, 'Отправь изображение.')
        return
    await state.update_data(pubg_photo_file_id=photo_file_id)
    data = await state.get_data()
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_pubg_progress_caption(data),
        photo_file_id=photo_file_id,
    )
    await state.set_state(ProfilesSectionStates.pubg_waiting_uid)
    await _cleanup_input_messages(state, message)
    prompt = await message.answer(
        '<b>🆔 Отправь UID из игры:</b>\n\nПример: <code>51234567890</code>',
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.pubg_waiting_photo))
async def pubg_create_photo_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    await _delete_user_message(message)
    await _send_error_notice(message, 'Отправь изображение.')


@router.message(StateFilter(ProfilesSectionStates.pubg_waiting_uid))
async def pubg_create_uid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    uid = (message.text or '').strip()
    if not _is_valid_uid(uid, min_len=8, max_len=20):
        await _send_error_notice(
            message,
            '❌ <b>Неверный формат UID.</b>\n\nВведи только цифры.',
        )
        return
    if await ProfileService(session).game_id_exists(game=GameCode.PUBG_MOBILE, game_player_id=uid, exclude_owner_id=user_id):
        await _send_error_notice(message, '⚠️ Такой UID уже используется в другой анкете.')
        return
    await state.update_data(pubg_uid=uid)
    data = await state.get_data()
    photo_file_id = data.get('pubg_photo_file_id') if isinstance(data.get('pubg_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_pubg_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.pubg_waiting_rank)
    await _cleanup_input_messages(state, message)
    prompt = await message.answer(
        '🎖 <b>Выбери свой ранг:</b>',
        reply_markup=my_profiles_pubg_rank_keyboard(include_cancel=False),
    )
    await _remember_prompt_message(state, prompt)


@router.callback_query(
    StateFilter(ProfilesSectionStates.pubg_waiting_rank),
    F.data.startswith(CB_MY_PROFILES_PUBG_RANK_PREFIX),
)
async def pubg_create_rank_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    await ensure_user_and_locale(callback.from_user, session)
    rank = (callback.data or '').replace(CB_MY_PROFILES_PUBG_RANK_PREFIX, '', 1).strip()
    if rank not in PUBG_RANK_CHOICES:
        await callback.answer('Неверный ранг', show_alert=True)
        return
    await state.update_data(pubg_rank=rank)
    data = await state.get_data()
    photo_file_id = data.get('pubg_photo_file_id') if isinstance(data.get('pubg_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        callback.message,
        caption=_pubg_progress_caption(data),
        photo_file_id=photo_file_id or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    await state.set_state(ProfilesSectionStates.pubg_waiting_about)
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        '📝 <b>Добавь описание в анкету:</b>',
    )
    await _remember_prompt_message(state, prompt)


@router.message(StateFilter(ProfilesSectionStates.pubg_waiting_rank))
async def pubg_create_rank_invalid_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await ensure_user_and_locale(message.from_user, session)
    await message.answer('Выбери ранг кнопками ниже.', reply_markup=my_profiles_pubg_rank_keyboard(include_cancel=False))


@router.message(StateFilter(ProfilesSectionStates.pubg_waiting_about))
async def pubg_create_about_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    about = (message.text or '').strip()
    if len(about) < DESCRIPTION_MIN_LENGTH:
        await _send_error_notice(message, f'Описание должно быть минимум {DESCRIPTION_MIN_LENGTH} символов.')
        return
    if len(about) > DESCRIPTION_MAX_LENGTH:
        await _send_error_notice(message, f'Описание слишком длинное. Максимум {DESCRIPTION_MAX_LENGTH} символов.')
        return
    await state.update_data(pubg_about_preview=about)
    data = await state.get_data()
    photo_preview = data.get('pubg_photo_file_id') if isinstance(data.get('pubg_photo_file_id'), str) else None
    await _edit_create_progress_by_ref(
        state,
        message,
        caption=_pubg_progress_caption(data),
        photo_file_id=photo_preview or MY_PROFILES_CREATE_IMAGE_FILE_ID,
    )
    photo_file_id = data.get('pubg_photo_file_id')
    uid = data.get('pubg_uid')
    rank = data.get('pubg_rank')
    if not isinstance(photo_file_id, str) or not isinstance(uid, str) or not isinstance(rank, str):
        await _send_error_notice(message, 'Не получилось завершить анкету. Попробуй ещё раз.')
        return
    profile = await ProfileService(session).save_pubg_profile(
        owner_id=user_id,
        game_player_id=uid,
        profile_image_file_id=photo_file_id,
        rank=rank,
        description=about,
    )
    create_mode = data.get('create_mode') if isinstance(data.get('create_mode'), str) else 'new'
    event_type = 'created' if create_mode == 'new' else 'updated'
    owner = await UserService(session).get_user(user_id)
    if owner is not None:
        await _send_profile_to_admin_review(
            message,
            profile=profile,
            owner=owner,
            event_type=event_type,
        )
    await _cleanup_input_messages(state, message)
    await state.update_data(active_game=GameCode.PUBG_MOBILE.value, active_profile_id=str(profile.id))
    await _edit_screen_by_ref(
        state,
        message,
        caption=_profile_card_text(profile),
        reply_markup=my_profile_details_keyboard(),
        photo_file_id=profile.profile_image_file_id,
    )
    await message.answer('✅ Анкета готова к поиску', reply_markup=my_profiles_hide_notice_keyboard())
    await state.set_state(None)
    await state.update_data(create_mode=None)


@router.callback_query(F.data == CB_MY_PROFILES_EDIT)
async def my_profiles_edit_menu_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    photo_file_id: str | None = None
    profile = await ProfileService(session).get_profile_for_game(user_id, active_game)
    if profile is not None:
        photo_file_id = profile.profile_image_file_id
    await callback.answer()
    await _edit_screen(
        callback.message,
        caption='<b>🔧 Управление анкетой</b>\n\n👇 Выбирай, что изменить',
        reply_markup=my_profiles_edit_fields_keyboard(game=active_game),
        photo_file_id=photo_file_id,
    )


@router.callback_query(F.data == CB_MY_PROFILES_REFILL)
async def my_profiles_refill_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    profile = await ProfileService(session).get_profile_for_game(user_id, active_game)
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    if active_game == GameCode.MLBB:
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
            mlbb_mythic_stars=None,
        )
        caption = _mlbb_progress_caption(await state.get_data())
    elif active_game == GameCode.GENSHIN_IMPACT:
        await state.set_state(ProfilesSectionStates.genshin_waiting_photo)
        await state.update_data(
            create_game=GameCode.GENSHIN_IMPACT.value,
            create_mode='refill',
            genshin_photo_file_id=None,
            genshin_uid=None,
            genshin_region=None,
            genshin_adventure_level=None,
            genshin_about_preview=None,
        )
        caption = _genshin_progress_caption(await state.get_data())
    else:
        await state.set_state(ProfilesSectionStates.pubg_waiting_photo)
        await state.update_data(
            create_game=GameCode.PUBG_MOBILE.value,
            create_mode='refill',
            pubg_photo_file_id=None,
            pubg_uid=None,
            pubg_rank=None,
            pubg_about_preview=None,
        )
        caption = _pubg_progress_caption(await state.get_data())
    await callback.answer()
    await _edit_screen(
        callback.message,
        caption=caption,
        reply_markup=my_profiles_create_cancel_keyboard(),
        photo_file_id=_create_example_image_file_id(active_game),
    )
    await _remember_message(state, callback.message)
    await _delete_prompt_by_ref(state, callback.message)
    prompt = await callback.message.answer(
        "📸 <b>Отправь скриншот своей анкеты из игры</b>\n\n"
        "👀 Это поможет другим игрокам быстрее тебя узнать",
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
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    profile = await ProfileService(session).get_profile_for_game(user_id, active_game)
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)

    if field == 'photo':
        await state.set_state(ProfilesSectionStates.edit_waiting_photo)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '🖼 <b>Отправь новую картинку анкеты.</b>',
            reply_markup=my_profiles_edit_cancel_keyboard(),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'id':
        await state.set_state(ProfilesSectionStates.edit_waiting_id)
        await state.update_data(edit_field=field)
        uid_example = '12345767890' if active_game == GameCode.MLBB else '712345678'
        prompt = await callback.message.answer(
            f'<b>🆔 Отправь UID из игры:</b>\n\nПример: <code>{uid_example}</code>',
            reply_markup=my_profiles_edit_cancel_keyboard(),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'rank':
        if active_game == GameCode.MLBB:
            await state.set_state(ProfilesSectionStates.edit_waiting_rank)
            await state.update_data(edit_field=field)
            prompt = await callback.message.answer(
                '🎖 <b>Выбери новый ранг:</b>',
                reply_markup=my_profiles_mlbb_rank_keyboard(cancel_callback=CB_MY_PROFILES_EDIT_CANCEL),
            )
            await _remember_prompt_message(state, prompt)
            return
        if active_game == GameCode.PUBG_MOBILE:
            await state.set_state(ProfilesSectionStates.edit_waiting_rank)
            await state.update_data(edit_field=field)
            prompt = await callback.message.answer(
                '🎖 <b>Выбери новый ранг:</b>',
                reply_markup=my_profiles_pubg_rank_keyboard(cancel_callback=CB_MY_PROFILES_EDIT_CANCEL),
            )
            await _remember_prompt_message(state, prompt)
            return
        await callback.message.answer('У этой анкеты нет поля ранга.')
        return

    if field == 'adventure_level':
        if active_game != GameCode.GENSHIN_IMPACT:
            await callback.message.answer('Это поле недоступно для этой анкеты.')
            return
        await state.set_state(ProfilesSectionStates.edit_waiting_genshin_level)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '⭐ <b>Введи новый уровень приключения (1-60):</b>',
            reply_markup=my_profiles_edit_cancel_keyboard(),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'role':
        if active_game != GameCode.MLBB:
            await callback.message.answer('Это поле недоступно для этой анкеты.')
            return
        await state.set_state(ProfilesSectionStates.edit_waiting_main_lane)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '🛡 <b>Выбери новую основную линию:</b>',
            reply_markup=my_profiles_mlbb_main_lane_keyboard(
                i18n,
                locale,
                cancel_callback=CB_MY_PROFILES_EDIT_CANCEL,
            ),
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'extra_lanes':
        if active_game != GameCode.MLBB:
            await callback.message.answer('Это поле недоступно для этой анкеты.')
            return
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
            '🎯 <b>Выбери дополнительные линии:</b>\n<i>Можно выбрать несколько</i>',
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
        if active_game == GameCode.MLBB:
            prompt_text = '🌍 <b>Выбери новый регион в игре:</b>'
            keyboard = my_profiles_mlbb_server_keyboard(cancel_callback=CB_MY_PROFILES_EDIT_CANCEL)
        elif active_game == GameCode.GENSHIN_IMPACT:
            prompt_text = '🌍 <b>Выбери новый регион:</b>'
            keyboard = my_profiles_genshin_region_keyboard(cancel_callback=CB_MY_PROFILES_EDIT_CANCEL)
        else:
            await callback.message.answer('У этой анкеты нет поля региона.')
            return
        prompt = await callback.message.answer(
            prompt_text,
            reply_markup=keyboard,
        )
        await _remember_prompt_message(state, prompt)
        return

    if field == 'about':
        await state.set_state(ProfilesSectionStates.edit_waiting_about)
        await state.update_data(edit_field=field)
        prompt = await callback.message.answer(
            '📝 <b>Введи новое описание анкеты:</b>',
            reply_markup=my_profiles_edit_cancel_keyboard(),
        )
        await _remember_prompt_message(state, prompt)
        return

    await callback.message.answer('Это поле пока недоступно.')


@router.callback_query(
    F.data == CB_MY_PROFILES_EDIT_CANCEL,
    StateFilter(
        ProfilesSectionStates.edit_waiting_photo,
        ProfilesSectionStates.edit_waiting_id,
        ProfilesSectionStates.edit_waiting_rank,
        ProfilesSectionStates.edit_waiting_mythic_stars,
        ProfilesSectionStates.edit_waiting_main_lane,
        ProfilesSectionStates.edit_waiting_extra_lanes,
        ProfilesSectionStates.edit_waiting_server,
        ProfilesSectionStates.edit_waiting_about,
        ProfilesSectionStates.edit_waiting_genshin_level,
    ),
)
async def my_profiles_edit_cancel_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    await callback.answer('Окей, отменил 👌', show_alert=False)
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
        notice = await message.answer('Отправь изображение.', reply_markup=my_profiles_hide_notice_keyboard())
        await _remember_temp_notice(state, notice)
        return
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    profile = await ProfileService(session).update_profile_fields_for_game(
        owner_id=user_id,
        game=active_game,
        profile_image_file_id=photo_file_id,
    )
    if profile is None:
        await message.answer('Анкета не найдена.', reply_markup=my_profiles_hide_notice_keyboard())
        return

    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _finalize_profile_edit_success(state, message, session, user_id)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_photo))
async def my_profiles_edit_photo_invalid_handler(message: Message, state: FSMContext) -> None:
    notice = await message.answer('Отправь изображение.', reply_markup=my_profiles_hide_notice_keyboard())
    await _remember_temp_notice(state, notice)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_id))
async def my_profiles_edit_id_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    game_id_raw = (message.text or '').strip()
    if active_game == GameCode.MLBB:
        valid = is_valid_mlbb_player_id(game_id_raw)
        sample = '12345767890'
    elif active_game == GameCode.GENSHIN_IMPACT:
        valid = _is_valid_uid(game_id_raw, min_len=8, max_len=12)
        sample = '712345678'
    else:
        valid = _is_valid_uid(game_id_raw, min_len=8, max_len=20)
        sample = '51234567890'
    if not valid:
        notice = await message.answer(
            f'❌ <b>Неверный формат UID.</b>\n\nОтправь только цифры.\nПример: <code>{sample}</code>',
            reply_markup=my_profiles_hide_notice_keyboard(),
        )
        await _remember_temp_notice(state, notice)
        return
    if await ProfileService(session).game_id_exists(
        game=active_game,
        game_player_id=game_id_raw,
        exclude_owner_id=user_id,
    ):
        notice = await message.answer(
            '⚠️ Такой UID уже используется.\nВведи другой UID.',
            reply_markup=my_profiles_hide_notice_keyboard(),
        )
        await _remember_temp_notice(state, notice)
        return

    profile = await ProfileService(session).update_profile_fields_for_game(
        owner_id=user_id,
        game=active_game,
        game_player_id=game_id_raw,
    )
    if profile is None:
        await message.answer('Анкета не найдена.', reply_markup=my_profiles_hide_notice_keyboard())
        return

    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _finalize_profile_edit_success(state, message, session, user_id)


@router.callback_query(
    StateFilter(ProfilesSectionStates.edit_waiting_rank),
    (F.data.startswith(CB_MY_PROFILES_MLBB_RANK_PREFIX) | F.data.startswith(CB_MY_PROFILES_PUBG_RANK_PREFIX)),
)
async def my_profiles_edit_rank_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    active_game = _active_game_from_state(data)

    if active_game == GameCode.PUBG_MOBILE:
        rank = (callback.data or '').replace(CB_MY_PROFILES_PUBG_RANK_PREFIX, '', 1).strip()
        if rank not in PUBG_RANK_CHOICES:
            await callback.answer('Неверный ранг', show_alert=True)
            return
        profile = await ProfileService(session).update_profile_fields_for_game(
            owner_id=user_id,
            game=active_game,
            rank=rank,
            mythic_stars=None,
        )
        if profile is None:
            await callback.answer('Анкета не найдена', show_alert=True)
            return
        await callback.answer()
        await _delete_prompt_by_ref(state, callback.message)
        await _finalize_profile_edit_success(state, callback.message, session, user_id)
        return

    rank = (callback.data or '').replace(CB_MY_PROFILES_MLBB_RANK_PREFIX, '', 1).strip()
    if rank not in {'Мастер', 'Грандмастер', 'Эпический', 'Легендарный', 'Мифический'}:
        await callback.answer('Неверный ранг', show_alert=True)
        return

    await callback.answer()
    if rank == 'Мифический':
        await state.set_state(ProfilesSectionStates.edit_waiting_mythic_stars)
        await state.update_data(edit_field='rank')
        await _delete_prompt_by_ref(state, callback.message)
        prompt = await callback.message.answer(
            '⭐ <b>Введи количество звезд (только число):</b>',
            reply_markup=my_profiles_edit_cancel_keyboard(),
        )
        await _remember_prompt_message(state, prompt)
        return

    profile = await ProfileService(session).update_profile_fields_for_game(
        owner_id=user_id,
        game=GameCode.MLBB,
        rank=rank,
        mythic_stars=None,
    )
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    await _delete_prompt_by_ref(state, callback.message)
    await _finalize_profile_edit_success(state, callback.message, session, user_id)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_rank))
async def my_profiles_edit_rank_invalid_handler(message: Message, state: FSMContext) -> None:
    notice = await message.answer('Выбери ранг кнопками ниже.', reply_markup=my_profiles_hide_notice_keyboard())
    await _remember_temp_notice(state, notice)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_mythic_stars))
async def my_profiles_edit_mythic_stars_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    raw = (message.text or '').strip()
    if not raw.isdigit():
        notice = await message.answer('Введи количество звезд цифрами.', reply_markup=my_profiles_hide_notice_keyboard())
        await _remember_temp_notice(state, notice)
        return
    stars = int(raw)
    if stars <= 0 or stars > 999:
        notice = await message.answer(
            'Количество звезд должно быть от 1 до 999.',
            reply_markup=my_profiles_hide_notice_keyboard(),
        )
        await _remember_temp_notice(state, notice)
        return

    profile = await ProfileService(session).update_mlbb_profile_fields(
        owner_id=user_id,
        rank='Мифический',
        mythic_stars=stars,
    )
    if profile is None:
        await message.answer('Анкета не найдена.', reply_markup=my_profiles_hide_notice_keyboard())
        return

    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _finalize_profile_edit_success(state, message, session, user_id)


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
        '🎯 <b>Выбери дополнительные линии:</b>\n<i>Можно выбрать несколько</i>',
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
        await callback.answer('Выбери хотя бы одну дополнительную линию', show_alert=True)
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


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_genshin_level))
async def my_profiles_edit_genshin_level_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    if active_game != GameCode.GENSHIN_IMPACT:
        notice = await message.answer('Это поле недоступно для этой анкеты.', reply_markup=my_profiles_hide_notice_keyboard())
        await _remember_temp_notice(state, notice)
        return
    raw = (message.text or '').strip()
    if not raw.isdigit():
        notice = await message.answer('Введи уровень цифрами от 1 до 60.', reply_markup=my_profiles_hide_notice_keyboard())
        await _remember_temp_notice(state, notice)
        return
    level = int(raw)
    if not (1 <= level <= 60):
        notice = await message.answer(
            'Уровень приключения должен быть от 1 до 60.',
            reply_markup=my_profiles_hide_notice_keyboard(),
        )
        await _remember_temp_notice(state, notice)
        return
    profile = await ProfileService(session).update_profile_fields_for_game(
        owner_id=user_id,
        game=active_game,
        rank=str(level),
    )
    if profile is None:
        await message.answer('Анкета не найдена.', reply_markup=my_profiles_hide_notice_keyboard())
        return
    await _delete_prompt_by_ref(state, message)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _finalize_profile_edit_success(state, message, session, user_id)


@router.callback_query(
    StateFilter(ProfilesSectionStates.edit_waiting_server),
    F.data.startswith(CB_MY_PROFILES_MLBB_SERVER_PREFIX),
)
async def my_profiles_edit_server_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    if active_game != GameCode.MLBB:
        await callback.answer('Поле недоступно', show_alert=True)
        return
    server = (callback.data or '').replace(CB_MY_PROFILES_MLBB_SERVER_PREFIX, '', 1).strip()
    if server not in {'UZ', 'RU', 'EU'}:
        await callback.answer('Неверный сервер', show_alert=True)
        return

    profile = await ProfileService(session).update_profile_fields_for_game(
        owner_id=user_id,
        game=active_game,
        play_time=server,
    )
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return

    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    await _finalize_profile_edit_success(state, callback.message, session, user_id)


@router.callback_query(
    StateFilter(ProfilesSectionStates.edit_waiting_server),
    F.data.startswith(CB_MY_PROFILES_GENSHIN_REGION_PREFIX),
)
async def my_profiles_edit_genshin_region_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, _ = await ensure_user_and_locale(callback.from_user, session)
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    if active_game != GameCode.GENSHIN_IMPACT:
        await callback.answer('Поле недоступно', show_alert=True)
        return
    region = (callback.data or '').replace(CB_MY_PROFILES_GENSHIN_REGION_PREFIX, '', 1).strip()
    if region not in GENSHIN_REGION_CODES:
        await callback.answer('Неверный регион', show_alert=True)
        return
    profile = await ProfileService(session).update_profile_fields_for_game(
        owner_id=user_id,
        game=active_game,
        play_time=region,
    )
    if profile is None:
        await callback.answer('Анкета не найдена', show_alert=True)
        return
    await callback.answer()
    await _delete_prompt_by_ref(state, callback.message)
    await _finalize_profile_edit_success(state, callback.message, session, user_id)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_server))
async def my_profiles_edit_server_invalid_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    if active_game == GameCode.GENSHIN_IMPACT:
        notice = await message.answer(
            'Выбери регион кнопками ниже.',
            reply_markup=my_profiles_genshin_region_keyboard(cancel_callback=CB_MY_PROFILES_EDIT_CANCEL),
        )
    else:
        notice = await message.answer(
            'Выбери регион кнопками ниже.',
            reply_markup=my_profiles_mlbb_server_keyboard(cancel_callback=CB_MY_PROFILES_EDIT_CANCEL),
        )
    await _remember_temp_notice(state, notice)


@router.message(StateFilter(ProfilesSectionStates.edit_waiting_about))
async def my_profiles_edit_about_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    user_id, _ = await ensure_user_and_locale(message.from_user, session)
    data = await state.get_data()
    active_game = _active_game_from_state(data)
    about = (message.text or '').strip()
    if len(about) < DESCRIPTION_MIN_LENGTH:
        notice = await message.answer(
            f'Описание должно быть минимум {DESCRIPTION_MIN_LENGTH} символов.',
            reply_markup=my_profiles_hide_notice_keyboard(),
        )
        await _remember_temp_notice(state, notice)
        return
    if len(about) > DESCRIPTION_MAX_LENGTH:
        notice = await message.answer(
            f'Описание слишком длинное. Максимум {DESCRIPTION_MAX_LENGTH} символов.',
            reply_markup=my_profiles_hide_notice_keyboard(),
        )
        await _remember_temp_notice(state, notice)
        return

    profile = await ProfileService(session).update_profile_fields_for_game(
        owner_id=user_id,
        game=active_game,
        description=about,
        about=about,
    )
    if profile is None:
        await message.answer('Анкета не найдена.', reply_markup=my_profiles_hide_notice_keyboard())
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
            f'❗ Ты уверен, что хочешь удалить анкету <b>{game_title}</b>?'
        ),
        reply_markup=my_profiles_delete_confirm_keyboard(),
        photo_file_id=MY_PROFILES_DELETE_IMAGE_FILE_ID,
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
            await callback.answer('Окей, отменил 👌', show_alert=False)
            await _render_profile_card(message=callback.message, state=state, user_id=user_id, game=game, session=session)
            return
        except ValueError:
            pass

    await callback.answer('Окей, отменил 👌', show_alert=False)
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
        try:
            deleted = await ProfileService(session).delete_owned_profile(user_id, UUID(profile_id_raw))
        except ValueError:
            deleted = False

    await callback.answer('Анкета удалена' if deleted else 'Анкета не найдена', show_alert=not deleted)
    await _render_dashboard(message=callback.message, state=state, user_id=user_id, session=session, use_edit=True)


def _moderation_command_name(raw_text: str | None) -> str | None:
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None
    token = raw_text.strip().split(maxsplit=1)[0]
    if not token.startswith('/'):
        return None
    return token[1:].split('@', 1)[0].lower()


async def _render_moderation_profile_message(
    *,
    message: Message,
    profile,
    owner,
    event_type: str,
) -> None:
    await message.answer_photo(
        photo=_photo_media(profile.profile_image_file_id),
        caption=_admin_profile_caption(profile, owner, event_type=event_type),
        parse_mode='HTML',
        reply_markup=admin_profile_review_keyboard(
            profile_id=profile.id,
            owner_id=profile.owner_id,
            game=profile.game,
        ),
    )


@router.message(Command(*MODERATION_SEARCH_COMMANDS.keys()))
async def moderator_random_profile_search_handler(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    if message.chat.id != MODERATION_REVIEW_CHAT_ID:
        return
    if not _is_admin(message.from_user.id):
        await message.answer('Нет доступа к модераторским командам.')
        return

    command_name = _moderation_command_name(message.text)
    if command_name is None:
        return
    game = MODERATION_SEARCH_COMMANDS.get(command_name)
    if game is None:
        return

    result = await ProfileService(session).random_profile_for_moderation(game)
    if result is None:
        await message.answer(f'Для игры {_game_title(game)} пока нет анкет для проверки.')
        return

    profile, owner = result
    await _render_moderation_profile_message(
        message=message,
        profile=profile,
        owner=owner,
        event_type='random',
    )


@router.callback_query(F.data.startswith(CB_ADMIN_PROFILE_APPROVE_PREFIX))
async def admin_profile_approve_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer('Нет доступа', show_alert=True)
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    payload = (callback.data or '').replace(CB_ADMIN_PROFILE_APPROVE_PREFIX, '', 1)
    parsed = _parse_admin_profile_payload(payload)
    if parsed is None:
        await callback.answer('Некорректные данные анкеты', show_alert=True)
        return
    profile_id, owner_id, payload_game = parsed
    profile_service = ProfileService(session)
    profile = await profile_service.get_owned_profile(owner_id, profile_id)
    if profile is None:
        await callback.answer('Этой анкеты уже нет', show_alert=False)
        await _send_moderation_group_log(
            callback,
            (
                f"⚠️ Модератор <b>{escape(_moderator_name(callback))}</b> "
                "попытался(ась) одобрить анкету, но такой анкеты уже нет."
            ),
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        return

    owner = await UserService(session).get_user(owner_id)
    await callback.answer('Анкета одобрена')
    await _send_moderation_group_log(
        callback,
        (
            f"✅ Модератор <b>{escape(_moderator_name(callback))}</b> одобрил(а) анкету "
            f"({escape(_game_title(profile.game if profile is not None else (payload_game or GameCode.MLBB)))})\n"
            f"{_owner_moderation_line(owner, owner_id)}"
        ),
    )
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith(CB_ADMIN_PROFILE_DELETE_PREFIX))
async def admin_profile_delete_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer('Нет доступа', show_alert=True)
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    payload = (callback.data or '').replace(CB_ADMIN_PROFILE_DELETE_PREFIX, '', 1)
    target = _parse_admin_profile_payload(payload)
    if target is None:
        await callback.answer('Некорректные данные анкеты', show_alert=True)
        return
    profile_id, owner_id, payload_game = target
    profile = await ProfileService(session).get_owned_profile(owner_id, profile_id)
    game_for_keyboard = profile.game if profile is not None else (payload_game or GameCode.MLBB)

    if profile is None:
        await callback.answer('Этой анкеты уже нет', show_alert=False)
        await _send_moderation_group_log(
            callback,
            (
                f"⚠️ Модератор <b>{escape(_moderator_name(callback))}</b> "
                "попытался(ась) удалить анкету, но такой анкеты уже нет."
            ),
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        return

    await callback.answer()
    try:
        await callback.message.edit_reply_markup(
            reply_markup=admin_profile_delete_reason_keyboard(
                profile_id=profile_id,
                owner_id=owner_id,
                game=game_for_keyboard,
            ),
        )
    except TelegramBadRequest as exc:
        if 'message is not modified' not in str(exc):
            raise


@router.callback_query(F.data.startswith(CB_ADMIN_PROFILE_DELETE_REASON_PREFIX))
async def admin_profile_delete_reason_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer('Нет доступа', show_alert=True)
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    payload = (callback.data or '').replace(CB_ADMIN_PROFILE_DELETE_REASON_PREFIX, '', 1)
    parsed = _parse_admin_reason_payload(payload)
    if parsed is None:
        await callback.answer('Некорректная причина удаления', show_alert=True)
        return
    reason_code, profile_id, owner_id, payload_game = parsed
    reason_text = ADMIN_DELETE_REASONS[reason_code]
    profile_service = ProfileService(session)
    profile = await profile_service.get_owned_profile(owner_id, profile_id)
    game_for_keyboard = profile.game if profile is not None else (payload_game or GameCode.MLBB)

    if profile is None:
        await callback.answer('Этой анкеты уже нет', show_alert=False)
        await _send_moderation_group_log(
            callback,
            (
                f"⚠️ Модератор <b>{escape(_moderator_name(callback))}</b> "
                "подтвердил(а) удаление, но такой анкеты уже нет."
            ),
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        return

    owner = await UserService(session).get_user(owner_id)
    deleted = await profile_service.delete_owned_profile(owner_id, profile_id)
    if not deleted:
        await callback.answer('Этой анкеты уже нет', show_alert=False)
        await _send_moderation_group_log(
            callback,
            (
                f"⚠️ Модератор <b>{escape(_moderator_name(callback))}</b> "
                "подтвердил(а) удаление, но такой анкеты уже нет."
            ),
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        return

    await callback.answer('Анкета удалена')
    await _send_moderation_group_log(
        callback,
        (
            f"❌ Модератор <b>{escape(_moderator_name(callback))}</b> "
            f"удалил(а) анкету ({escape(_game_title(profile.game))}) по причине: "
            f"<b>{escape(reason_text)}</b>\n"
            f"{_owner_moderation_line(owner, owner_id)}"
        ),
    )
    try:
        await callback.bot.send_message(
            chat_id=owner_id,
            text=(
                "🚫 <b>Анкета удалена модератором</b>\n\n"
                f"🎮 <b>Игра:</b> {escape(_game_title(profile.game))}\n"
                f"📌 <b>Причина:</b> {escape(reason_text)}\n\n"
                "🛠 Исправьте данные и создайте анкету заново."
            ),
            parse_mode='HTML',
            reply_markup=_recreate_profile_keyboard(profile.game),
        )
    except Exception:
        pass
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith(CB_ADMIN_PROFILE_REFRESH_PREFIX))
async def admin_profile_refresh_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer('Нет доступа', show_alert=True)
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    payload = (callback.data or '').replace(CB_ADMIN_PROFILE_REFRESH_PREFIX, '', 1)
    parsed = _parse_admin_profile_payload(payload)
    if parsed is None:
        await callback.answer('Некорректные данные анкеты', show_alert=True)
        return
    profile_id, owner_id, payload_game = parsed
    profile_service = ProfileService(session)
    profile = await profile_service.get_owned_profile(owner_id, profile_id)
    if profile is None and payload_game is not None:
        profile = await profile_service.get_profile_for_game(owner_id, payload_game)
    game_for_keyboard = profile.game if profile is not None else (payload_game or GameCode.MLBB)
    if profile is None:
        await callback.answer('Этой анкеты нет', show_alert=True)
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        return

    owner = await UserService(session).get_user(owner_id)
    media = InputMediaPhoto(
        media=_photo_media(profile.profile_image_file_id),
        caption=_admin_profile_caption(profile, owner, event_type='updated'),
        parse_mode='HTML',
    )
    try:
        await callback.message.edit_media(
            media=media,
            reply_markup=admin_profile_review_keyboard(
                profile_id=profile.id,
                owner_id=profile.owner_id,
                game=profile.game,
            ),
        )
    except TelegramBadRequest as exc:
        if 'message is not modified' in str(exc):
            await callback.message.edit_reply_markup(
                reply_markup=admin_profile_review_keyboard(
                    profile_id=profile.id,
                    owner_id=profile.owner_id,
                    game=profile.game,
                ),
            )
        else:
            raise
    await callback.answer('Анкета обновлена')


@router.callback_query(F.data.startswith(CB_ADMIN_PROFILE_HIDE_PREFIX))
async def admin_profile_hide_handler(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer('Нет доступа', show_alert=True)
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
