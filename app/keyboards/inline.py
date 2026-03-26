import uuid

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.constants import (
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
    CB_PROFILE_BACK,
    CB_PROFILE_EDIT,
    CB_PROFILE_EDIT_AVATAR,
    CB_PROFILE_EDIT_CANCEL,
    CB_PROFILE_EDIT_FULL_NAME,
    CB_PROFILE_EDIT_USERNAME,
    CB_PROFILE_LANG_SET_PREFIX,
    CB_PROFILE_LANGUAGE,
    CB_PROFILE_STATS,
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
from app.locales import LocalizationManager


LANGUAGE_CHOICES = (
    ('ru', 'Русский'),
    ('en', 'English'),
    ('uz', "O'zbekcha"),
)


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, title in LANGUAGE_CHOICES:
        builder.button(text=title, callback_data=f'lang:set:{code}')
    builder.adjust(3)
    return builder.as_markup()


def game_select_keyboard(
    i18n: LocalizationManager,
    locale: str,
    callback_prefix: str,
    *,
    one_per_row: bool = True,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for game in (GameCode.MLBB,):
        builder.button(
            text=i18n.t(locale, f'game.button.{game.value}'),
            callback_data=f'{callback_prefix}:{game.value}',
        )
    if one_per_row:
        builder.adjust(1)
    else:
        builder.adjust(2)
    return builder.as_markup()


def my_profiles_games_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    return game_select_keyboard(i18n, locale, 'my_profiles:game', one_per_row=True)


def create_profile_for_game_keyboard(i18n: LocalizationManager, locale: str, game: GameCode) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=i18n.t(locale, 'action.create_profile_for_game'),
        callback_data=f'my_profiles:create:{game.value}',
    )
    return builder.as_markup()


def my_profile_actions_keyboard(
    i18n: LocalizationManager,
    locale: str,
    *,
    game: GameCode,
    profile_id: uuid.UUID,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.edit_data'), callback_data=f'my_profiles:edit:{game.value}')
    builder.button(text=i18n.t(locale, 'action.refill'), callback_data=f'my_profiles:refill:{game.value}')
    builder.button(
        text=i18n.t(locale, 'action.delete_profile'),
        callback_data=f'my_profiles:delete_ask:{profile_id}',
    )
    builder.adjust(1)
    return builder.as_markup()


def delete_confirmation_keyboard(
    i18n: LocalizationManager,
    locale: str,
    *,
    profile_id: uuid.UUID,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=i18n.t(locale, 'action.delete_confirm_yes'),
        callback_data=f'my_profiles:delete_yes:{profile_id}',
    )
    builder.button(
        text=i18n.t(locale, 'action.delete_confirm_no'),
        callback_data='my_profiles:delete_no',
    )
    builder.adjust(2)
    return builder.as_markup()


def profile_panel_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.settings'), callback_data='settings:open')
    builder.button(text=i18n.t(locale, 'action.statistics'), callback_data='profile:stats')
    builder.adjust(2)
    return builder.as_markup()


def settings_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.change_language'), callback_data='settings:language')
    builder.adjust(1)
    return builder.as_markup()


def mlbb_main_lane_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for lane in (
        MlbbLaneCode.GOLD,
        MlbbLaneCode.MID,
        MlbbLaneCode.EXP,
        MlbbLaneCode.JUNGLE,
        MlbbLaneCode.ROAM,
    ):
        builder.button(
            text=i18n.t(locale, f'mlbb.lane.{lane.value}'),
            callback_data=f'mlbb:main_lane:{lane.value}',
        )
    builder.adjust(1)
    return builder.as_markup()


def mlbb_extra_lanes_keyboard(
    i18n: LocalizationManager,
    locale: str,
    *,
    selected: set[MlbbLaneCode],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    all_options = (
        MlbbLaneCode.GOLD,
        MlbbLaneCode.MID,
        MlbbLaneCode.EXP,
        MlbbLaneCode.JUNGLE,
        MlbbLaneCode.ROAM,
        MlbbLaneCode.ALL,
    )

    for lane in all_options:
        marker = '✅ ' if lane in selected else ''
        builder.button(
            text=f"{marker}{i18n.t(locale, f'mlbb.lane.{lane.value}')}",
            callback_data=f'mlbb:extra_toggle:{lane.value}',
        )

    builder.button(text=i18n.t(locale, 'action.done'), callback_data='mlbb:extra_done')
    builder.adjust(1)
    return builder.as_markup()


def open_my_profiles_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'menu.my_profiles'), callback_data='my_profiles:open')
    builder.adjust(1)
    return builder.as_markup()


def profile_actions_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.statistics'), callback_data=CB_PROFILE_STATS)
    builder.button(text=i18n.t(locale, 'action.edit_data'), callback_data=CB_PROFILE_EDIT)
    builder.button(text=i18n.t(locale, 'action.change_language'), callback_data=CB_PROFILE_LANGUAGE)
    builder.adjust(1, 2)
    return builder.as_markup()


def profile_stats_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.back_to_profile'), callback_data=CB_PROFILE_BACK)
    builder.adjust(1)
    return builder.as_markup()


def profile_edit_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.edit_avatar'), callback_data=CB_PROFILE_EDIT_AVATAR)
    builder.button(text=i18n.t(locale, 'action.edit_full_name'), callback_data=CB_PROFILE_EDIT_FULL_NAME)
    builder.button(text=i18n.t(locale, 'action.edit_username'), callback_data=CB_PROFILE_EDIT_USERNAME)
    builder.button(text=i18n.t(locale, 'action.back_to_profile'), callback_data=CB_PROFILE_BACK)
    builder.adjust(1)
    return builder.as_markup()


def profile_edit_cancel_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.cancel'), callback_data=CB_PROFILE_EDIT_CANCEL)
    builder.adjust(1)
    return builder.as_markup()


def profile_language_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, title in (
        ('ru', '🇷🇺 Русский'),
        ('uz', "🇺🇿 O'zbekcha"),
        ('en', '🇬🇧 English'),
    ):
        builder.button(text=title, callback_data=f'{CB_PROFILE_LANG_SET_PREFIX}{code}')
    builder.button(text=i18n.t(locale, 'action.back_to_profile'), callback_data=CB_PROFILE_BACK)
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def my_profiles_dashboard_keyboard(*, created_games: list[GameCode], has_missing: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for game in created_games:
        title = 'Mobile Legends' if game == GameCode.MLBB else 'Неизвестная игра'
        builder.button(text=title, callback_data=f'{CB_MY_PROFILES_GAME_PREFIX}{game.value}')
    if has_missing:
        builder.button(text='➕ Создать анкету', callback_data=CB_MY_PROFILES_CREATE_MENU)
    builder.adjust(1)
    return builder.as_markup()


def my_profile_details_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='✏️ Изменить данные', callback_data=CB_MY_PROFILES_EDIT)
    builder.button(text='🗑 Удалить анкету', callback_data=CB_MY_PROFILES_DELETE_ASK)
    builder.button(text='⬅️ Назад', callback_data=CB_MY_PROFILES_BACK)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_create_game_keyboard(*, games: list[GameCode]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for game in games:
        title = 'Mobile Legends' if game == GameCode.MLBB else 'Неизвестная игра'
        builder.button(text=title, callback_data=f'{CB_MY_PROFILES_CREATE_PICK_PREFIX}{game.value}')
    builder.button(text='⬅️ Назад', callback_data=CB_MY_PROFILES_BACK)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_delete_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Да, удалить', callback_data=CB_MY_PROFILES_DELETE_CONFIRM)
    builder.button(text='❌ Отмена', callback_data=CB_MY_PROFILES_DELETE_CANCEL)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_edit_fields_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='🏷 Изменить ник', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}nick')
    builder.button(text='🎖 Изменить ранг', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}rank')
    builder.button(text='🛡 Изменить роль', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}role')
    builder.button(text='🌍 Изменить сервер', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}server')
    builder.button(text='📝 Изменить описание', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}about')
    builder.button(text='⬅️ Назад', callback_data=CB_MY_PROFILES_BACK)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_create_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data=CB_MY_PROFILES_CREATE_CANCEL)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_mlbb_main_lane_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for lane in (
        MlbbLaneCode.GOLD,
        MlbbLaneCode.MID,
        MlbbLaneCode.EXP,
        MlbbLaneCode.JUNGLE,
        MlbbLaneCode.ROAM,
    ):
        builder.button(
            text=i18n.t(locale, f'mlbb.lane.{lane.value}'),
            callback_data=f'{CB_MY_PROFILES_MLBB_MAIN_PREFIX}{lane.value}',
        )
    builder.button(text='❌ Отмена', callback_data=CB_MY_PROFILES_CREATE_CANCEL)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_mlbb_extra_lanes_keyboard(
    i18n: LocalizationManager,
    locale: str,
    *,
    selected: set[MlbbLaneCode],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for lane in (
        MlbbLaneCode.GOLD,
        MlbbLaneCode.MID,
        MlbbLaneCode.EXP,
        MlbbLaneCode.JUNGLE,
        MlbbLaneCode.ROAM,
    ):
        prefix = '✅ ' if lane in selected else ''
        builder.button(
            text=f"{prefix}{i18n.t(locale, f'mlbb.lane.{lane.value}')}",
            callback_data=f'{CB_MY_PROFILES_MLBB_EXTRA_PREFIX}{lane.value}',
        )
    builder.button(text='Готово', callback_data=CB_MY_PROFILES_MLBB_EXTRA_DONE)
    builder.button(text='❌ Отмена', callback_data=CB_MY_PROFILES_CREATE_CANCEL)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_mlbb_rank_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rank in ('Мастер', 'Грандмастер', 'Эпический', 'Легендарный', 'Мифический'):
        builder.button(text=rank, callback_data=f'{CB_MY_PROFILES_MLBB_RANK_PREFIX}{rank}')
    builder.button(text='❌ Отмена', callback_data=CB_MY_PROFILES_CREATE_CANCEL)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_mlbb_server_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for server in ('UZ', 'RU', 'EU'):
        builder.button(text=server, callback_data=f'{CB_MY_PROFILES_MLBB_SERVER_PREFIX}{server}')
    builder.button(text='❌ Отмена', callback_data=CB_MY_PROFILES_CREATE_CANCEL)
    builder.adjust(1)
    return builder.as_markup()


def search_need_profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='➕ Создать анкету', callback_data=CB_SEARCH_CREATE_PROFILE)
    builder.button(text='⬅️ Назад', callback_data=CB_SEARCH_BACK_MAIN)
    builder.adjust(1)
    return builder.as_markup()


def search_game_pick_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='🎮 Mobile Legends', callback_data=f'{CB_SEARCH_GAME_PICK_PREFIX}{GameCode.MLBB.value}')
    builder.button(text='⬅️ Назад', callback_data=CB_SEARCH_BACK_MAIN)
    builder.adjust(1)
    return builder.as_markup()


def search_profile_actions_keyboard(
    *,
    target_user_id: int,
    game: GameCode,
    subscribed: bool,
    include_next: bool = True,
    include_hide: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='❤️ Лайк', callback_data=f'{CB_SEARCH_LIKE_PREFIX}{target_user_id}:{game.value}')
    builder.button(text='💬 Сообщение', callback_data=f'{CB_SEARCH_MESSAGE_PREFIX}{target_user_id}')
    sub_text = '🔕 Отписаться' if subscribed else '⭐ Подписаться'
    builder.button(text=sub_text, callback_data=f'{CB_SEARCH_SUB_PREFIX}{target_user_id}')
    if include_next:
        builder.button(text='➡️ Следующая анкета', callback_data=f'{CB_SEARCH_NEXT_PREFIX}{game.value}')
    if include_hide:
        builder.button(text='🙈 Скрыть уведомление', callback_data=CB_SEARCH_HIDE_NOTICE)
    builder.adjust(3, 1, 1)
    return builder.as_markup()


def search_empty_keyboard(*, game: GameCode) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='🔄 Искать заново', callback_data=f'{CB_SEARCH_RETRY_PREFIX}{game.value}')
    builder.button(text='⬅️ Назад', callback_data=CB_SEARCH_BACK_MAIN)
    builder.adjust(1)
    return builder.as_markup()


def search_like_notice_keyboard(*, liker_user_id: int, game: GameCode) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='👀 Посмотреть', callback_data=f'{CB_SEARCH_VIEW_LIKER_PREFIX}{liker_user_id}:{game.value}')
    builder.button(text='🙈 Скрыть уведомление', callback_data=CB_SEARCH_HIDE_NOTICE)
    builder.adjust(1)
    return builder.as_markup()


def search_profile_notice_keyboard(*, user_id: int, subscribed: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='👤 Показать профиль', callback_data=f'{CB_SEARCH_VIEW_PROFILE_PREFIX}{user_id}')
    sub_text = '🔕 Отписаться' if subscribed else '⭐ Подписаться'
    builder.button(text=sub_text, callback_data=f'{CB_SEARCH_SUB_PREFIX}{user_id}')
    builder.button(text='💬 Сообщение', callback_data=f'{CB_SEARCH_MESSAGE_PREFIX}{user_id}')
    builder.button(text='🙈 Скрыть уведомление', callback_data=CB_SEARCH_HIDE_NOTICE)
    builder.adjust(1, 2, 1)
    return builder.as_markup()


def search_message_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отменить', callback_data=CB_SEARCH_CANCEL_MESSAGE)
    builder.adjust(1)
    return builder.as_markup()
