import uuid

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.constants import (
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
    CB_PROFILE_BACK,
    CB_PROFILE_EDIT,
    CB_PROFILE_EDIT_AVATAR,
    CB_PROFILE_EDIT_CANCEL,
    CB_PROFILE_EDIT_FULL_NAME,
    CB_PROFILE_EDIT_USERNAME,
    CB_PROFILE_LANG_SET_PREFIX,
    CB_PROFILE_LANGUAGE,
    CB_PROFILE_NOTIFICATIONS,
    CB_PROFILE_NOTIF_LIKES,
    CB_PROFILE_NOTIF_MESSAGES,
    CB_PROFILE_NOTIF_SUBS,
    CB_PROFILE_STATS,
    CB_PROFILE_STATS_REFRESH,
    CB_SEARCH_BACK_MAIN,
    CB_SEARCH_CANCEL_MESSAGE,
    CB_ACTIVITY_BACK,
    CB_ACTIVITY_OPEN,
    CB_ACTIVITY_PAGE_PREFIX,
    CB_ACTIVITY_SECTION_PREFIX,
    CB_CHATS_CANCEL_SEND_PREFIX,
    CB_CHATS_CANCEL_NEW,
    CB_CHATS_MESSAGES_PAGE_PREFIX,
    CB_CHATS_NEW,
    CB_CHATS_OPEN,
    CB_CHATS_OPEN_CHAT_PREFIX,
    CB_CHATS_PAGE_PREFIX,
    CB_CHATS_SEND_PREFIX,
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
    builder.button(text=i18n.t(locale, 'action.edit_data'), callback_data=CB_PROFILE_EDIT)
    builder.button(text=i18n.t(locale, 'action.notifications'), callback_data=CB_PROFILE_NOTIFICATIONS)
    builder.button(text=i18n.t(locale, 'action.language.short'), callback_data=CB_PROFILE_LANGUAGE)
    builder.button(text=i18n.t(locale, 'action.statistics'), callback_data=CB_PROFILE_STATS)
    builder.adjust(1, 2, 1)
    return builder.as_markup()


def profile_stats_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.refresh'), callback_data=CB_PROFILE_STATS_REFRESH)
    builder.button(text=i18n.t(locale, 'action.back_to_profile'), callback_data=CB_PROFILE_BACK)
    builder.adjust(1)
    return builder.as_markup()


def profile_edit_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.edit_avatar'), callback_data=CB_PROFILE_EDIT_AVATAR)
    builder.button(text=i18n.t(locale, 'action.edit_nickname'), callback_data=CB_PROFILE_EDIT_FULL_NAME)
    builder.button(text=i18n.t(locale, 'action.edit_username'), callback_data=CB_PROFILE_EDIT_USERNAME)
    builder.button(text=i18n.t(locale, 'action.back_to_profile'), callback_data=CB_PROFILE_BACK)
    builder.adjust(1)
    return builder.as_markup()


def profile_notifications_keyboard(i18n: LocalizationManager, locale: str, settings: dict[str, bool]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    likes_state = i18n.t(locale, 'state.on') if settings.get('likes', True) else i18n.t(locale, 'state.off')
    subs_state = i18n.t(locale, 'state.on') if settings.get('subscriptions', True) else i18n.t(locale, 'state.off')
    msg_state = i18n.t(locale, 'state.on') if settings.get('messages', True) else i18n.t(locale, 'state.off')
    builder.button(text=f"{i18n.t(locale, 'label.likes')} ({likes_state})", callback_data=CB_PROFILE_NOTIF_LIKES)
    builder.button(text=f"{i18n.t(locale, 'label.subscriptions')} ({subs_state})", callback_data=CB_PROFILE_NOTIF_SUBS)
    builder.button(text=f"{i18n.t(locale, 'label.messages')} ({msg_state})", callback_data=CB_PROFILE_NOTIF_MESSAGES)
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


def my_profiles_dashboard_keyboard(*, created_games: list[GameCode]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for game in created_games:
        title = 'Mobile Legends' if game == GameCode.MLBB else 'Неизвестная игра'
        builder.button(text=title, callback_data=f'{CB_MY_PROFILES_GAME_PREFIX}{game.value}')
    builder.button(text='➕ Добавить новую анкету', callback_data=CB_MY_PROFILES_CREATE_MENU)
    builder.adjust(1)
    return builder.as_markup()


def my_profile_details_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='✏️ Изменить анкету', callback_data=CB_MY_PROFILES_EDIT)
    builder.button(text='🔄 Заполнить заново', callback_data=CB_MY_PROFILES_REFILL)
    builder.button(text='🗑 Удалить анкету', callback_data=CB_MY_PROFILES_DELETE_ASK)
    builder.button(text='⬅ Назад', callback_data=CB_MY_PROFILES_BACK)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_create_game_keyboard(*, games: list[GameCode]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for game in games:
        title = 'Mobile Legends' if game == GameCode.MLBB else 'Неизвестная игра'
        builder.button(text=title, callback_data=f'{CB_MY_PROFILES_CREATE_PICK_PREFIX}{game.value}')
    builder.button(text='⬅ Назад', callback_data=CB_MY_PROFILES_BACK)
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
    builder.button(text='🖼 Фото анкеты', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}photo')
    builder.button(text='🆔 ID', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}id')
    builder.button(text='🌍 Регион', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}server')
    builder.button(text='🎖 Ранг', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}rank')
    builder.button(text='🛡 Роль', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}role')
    builder.button(text='🎯 Доп. линии', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}extra_lanes')
    builder.button(text='📝 О себе', callback_data=f'{CB_MY_PROFILES_EDIT_FIELD_PREFIX}about')
    builder.button(text='⬅ Назад к анкете', callback_data=CB_MY_PROFILES_CARD_BACK)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_create_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data=CB_MY_PROFILES_CREATE_CANCEL)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_edit_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data=CB_MY_PROFILES_EDIT_CANCEL)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_hide_notice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='🔺 Скрыть сообщение', callback_data=CB_MY_PROFILES_HIDE_NOTICE)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_mlbb_main_lane_keyboard(
    i18n: LocalizationManager,
    locale: str,
    *,
    cancel_callback: str = CB_MY_PROFILES_CREATE_CANCEL,
    excluded_lanes: set[MlbbLaneCode] | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    excluded_lanes = excluded_lanes or set()
    for lane in (
        MlbbLaneCode.GOLD,
        MlbbLaneCode.MID,
        MlbbLaneCode.EXP,
        MlbbLaneCode.JUNGLE,
        MlbbLaneCode.ROAM,
    ):
        if lane in excluded_lanes:
            continue
        builder.button(
            text=i18n.t(locale, f'mlbb.lane.{lane.value}'),
            callback_data=f'{CB_MY_PROFILES_MLBB_MAIN_PREFIX}{lane.value}',
        )
    builder.button(text='❌ Отмена', callback_data=cancel_callback)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_mlbb_extra_lanes_keyboard(
    i18n: LocalizationManager,
    locale: str,
    *,
    selected: set[MlbbLaneCode],
    cancel_callback: str = CB_MY_PROFILES_CREATE_CANCEL,
    excluded_lanes: set[MlbbLaneCode] | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    excluded_lanes = excluded_lanes or set()
    for lane in (
        MlbbLaneCode.GOLD,
        MlbbLaneCode.MID,
        MlbbLaneCode.EXP,
        MlbbLaneCode.JUNGLE,
        MlbbLaneCode.ROAM,
    ):
        if lane in excluded_lanes:
            continue
        prefix = '🔹 ' if lane in selected else ''
        builder.button(
            text=f"{prefix}{i18n.t(locale, f'mlbb.lane.{lane.value}')}",
            callback_data=f'{CB_MY_PROFILES_MLBB_EXTRA_PREFIX}{lane.value}',
        )
    builder.button(text='✅ Готово', callback_data=CB_MY_PROFILES_MLBB_EXTRA_DONE)
    builder.button(text='❌ Отмена', callback_data=cancel_callback)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_mlbb_rank_keyboard(*, cancel_callback: str = CB_MY_PROFILES_CREATE_CANCEL) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rank in ('Мастер', 'Грандмастер', 'Эпический', 'Легендарный', 'Мифический'):
        builder.button(text=rank, callback_data=f'{CB_MY_PROFILES_MLBB_RANK_PREFIX}{rank}')
    builder.button(text='❌ Отмена', callback_data=cancel_callback)
    builder.adjust(1)
    return builder.as_markup()


def my_profiles_mlbb_server_keyboard(*, cancel_callback: str = CB_MY_PROFILES_CREATE_CANCEL) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for server in ('🇺🇿 UZ', '🇷🇺 RU', '🇪🇺 EU'):
        code = server.split(' ', 1)[1]
        builder.button(text=server, callback_data=f'{CB_MY_PROFILES_MLBB_SERVER_PREFIX}{code}')
    builder.button(text='❌ Отмена', callback_data=cancel_callback)
    builder.adjust(3, 1)
    return builder.as_markup()


def search_need_profile_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'search.button.create_profile'), callback_data=CB_SEARCH_CREATE_PROFILE)
    builder.adjust(1)
    return builder.as_markup()


def search_game_pick_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'search.button.game.mlbb'), callback_data=f'{CB_SEARCH_GAME_PICK_PREFIX}{GameCode.MLBB.value}')
    builder.adjust(1)
    return builder.as_markup()


def search_profile_actions_keyboard(
    *,
    i18n: LocalizationManager,
    locale: str,
    target_user_id: int,
    game: GameCode,
    subscribed: bool,
    liked: bool = False,
    include_next: bool = True,
    include_previous: bool = False,
    include_hide: bool = False,
    back_to_profile_user_id: int | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'search.button.personal_profile'), callback_data=f'{CB_SEARCH_VIEW_PROFILE_PREFIX}{target_user_id}')
    like_text = i18n.t(locale, 'search.button.like_sent') if liked else i18n.t(locale, 'search.button.like')
    builder.button(text=like_text, callback_data=f'{CB_SEARCH_LIKE_PREFIX}{target_user_id}:{game.value}')
    builder.button(text=i18n.t(locale, 'search.button.message'), callback_data=f'{CB_SEARCH_MESSAGE_PREFIX}{target_user_id}')
    if back_to_profile_user_id is not None:
        builder.button(text=i18n.t(locale, 'search.button.back_to_personal_profile'), callback_data=f'{CB_SEARCH_BACK_TO_PROFILE_PREFIX}{back_to_profile_user_id}')
    if include_hide:
        builder.button(text=i18n.t(locale, 'search.button.hide_message'), callback_data=CB_SEARCH_HIDE_NOTICE)
    if include_previous:
        builder.button(text=i18n.t(locale, 'search.button.previous_profile'), callback_data=f'{CB_SEARCH_PREV_PREFIX}{game.value}')
    if include_next:
        builder.button(text=i18n.t(locale, 'search.button.next_profile'), callback_data=f'{CB_SEARCH_NEXT_PREFIX}{game.value}')

    row_pattern = [1, 2]
    if back_to_profile_user_id is not None:
        row_pattern.append(1)
    if include_hide:
        row_pattern.append(1)
    if include_previous and include_next:
        row_pattern.append(2)
    else:
        if include_previous:
            row_pattern.append(1)
        if include_next:
            row_pattern.append(1)
    builder.adjust(*row_pattern)
    return builder.as_markup()


def search_empty_keyboard(*, i18n: LocalizationManager, locale: str, game: GameCode) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'search.button.retry'), callback_data=f'{CB_SEARCH_RETRY_PREFIX}{game.value}')
    builder.adjust(1)
    return builder.as_markup()


def search_like_notice_keyboard(*, i18n: LocalizationManager, locale: str, liker_user_id: int, game: GameCode) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'search.button.show_profile_card'), callback_data=f'{CB_SEARCH_VIEW_LIKER_PREFIX}{liker_user_id}:{game.value}')
    builder.button(text=i18n.t(locale, 'search.button.hide_message'), callback_data=CB_SEARCH_HIDE_NOTICE)
    builder.adjust(1)
    return builder.as_markup()


def search_profile_notice_keyboard(
    *,
    i18n: LocalizationManager,
    locale: str,
    user_id: int,
    subscribed: bool,
    game: GameCode = GameCode.MLBB,
    include_back_to_card: bool = True,
    include_back_to_activity: bool = False,
    include_hide_notice: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'search.button.game_profiles'), callback_data=f'{CB_SEARCH_USER_PROFILES_PREFIX}{user_id}')
    builder.button(text=i18n.t(locale, 'search.button.write'), callback_data=f'{CB_SEARCH_MESSAGE_PREFIX}{user_id}')
    sub_text = i18n.t(locale, 'search.button.unsubscribe') if subscribed else i18n.t(locale, 'search.button.subscribe')
    builder.button(text=sub_text, callback_data=f'{CB_SEARCH_SUB_PREFIX}{user_id}')
    if include_back_to_card:
        builder.button(text=i18n.t(locale, 'search.button.back_to_game_profile'), callback_data=CB_SEARCH_BACK_TO_CARD)
    if include_back_to_activity:
        builder.button(text=i18n.t(locale, 'search.button.back_to_activity'), callback_data=CB_ACTIVITY_BACK)
    if include_hide_notice:
        builder.button(text=i18n.t(locale, 'search.button.hide_message'), callback_data=CB_SEARCH_HIDE_NOTICE)
    row_pattern = [1, 2]
    if include_back_to_card:
        row_pattern.append(1)
    if include_back_to_activity:
        row_pattern.append(1)
    if include_hide_notice:
        row_pattern.append(1)
    builder.adjust(*row_pattern)
    return builder.as_markup()


def search_user_profiles_games_keyboard(*, i18n: LocalizationManager, locale: str, user_id: int, games: list[GameCode]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for game in games:
        title = i18n.t(locale, 'search.button.game.mlbb') if game == GameCode.MLBB else f'🎮 {game.value}'
        builder.button(text=title, callback_data=f'{CB_SEARCH_USER_PROFILE_GAME_PREFIX}{user_id}:{game.value}')
    builder.button(text=i18n.t(locale, 'search.button.back_to_personal_profile'), callback_data=f'{CB_SEARCH_BACK_TO_PROFILE_PREFIX}{user_id}')
    builder.adjust(1)
    return builder.as_markup()


def activity_open_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'activity.button.my_subscriptions'), callback_data=f'{CB_ACTIVITY_SECTION_PREFIX}subscriptions:1')
    builder.button(text=i18n.t(locale, 'activity.button.my_subscribers'), callback_data=f'{CB_ACTIVITY_SECTION_PREFIX}subscribers:1')
    builder.button(text=i18n.t(locale, 'activity.button.my_likes'), callback_data=f'{CB_ACTIVITY_SECTION_PREFIX}likes:1')
    builder.button(text=i18n.t(locale, 'activity.button.who_liked_me'), callback_data=f'{CB_ACTIVITY_SECTION_PREFIX}liked_by:1')
    builder.button(text=i18n.t(locale, 'activity.button.friends'), callback_data=f'{CB_ACTIVITY_SECTION_PREFIX}friends:1')
    builder.adjust(1)
    return builder.as_markup()


def activity_section_keyboard(
    i18n: LocalizationManager,
    locale: str,
    *,
    section: str,
    page: int,
    items: list[dict[str, int | str | None]],
    has_previous: bool,
    has_next: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        user_id = item.get('user_id')
        if not isinstance(user_id, int):
            continue
        nickname_raw = item.get('full_name')
        if isinstance(nickname_raw, str) and nickname_raw.strip():
            nickname = nickname_raw.strip()
        else:
            nickname = i18n.t(locale, 'activity.user.fallback', user_id=user_id)
        builder.button(text=nickname, callback_data=f'{CB_SEARCH_VIEW_PROFILE_PREFIX}{user_id}:activity')

    if has_previous:
        builder.button(
            text=i18n.t(locale, 'activity.button.prev_page'),
            callback_data=f'{CB_ACTIVITY_PAGE_PREFIX}{section}:{page - 1}',
        )
    if has_next:
        builder.button(
            text=i18n.t(locale, 'activity.button.next_page'),
            callback_data=f'{CB_ACTIVITY_PAGE_PREFIX}{section}:{page + 1}',
        )
    builder.button(text=i18n.t(locale, 'activity.button.back_to_activity'), callback_data=CB_ACTIVITY_BACK)
    if has_previous and has_next:
        builder.adjust(*(1 for _ in items), 2, 1)
    elif has_previous or has_next:
        builder.adjust(*(1 for _ in items), 1, 1)
    else:
        builder.adjust(*(1 for _ in items), 1)
    return builder.as_markup()


def chats_list_keyboard(
    *,
    i18n: LocalizationManager,
    locale: str,
    chats: list[dict[str, int | str | None]],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in chats:
        chat_id = item.get('chat_id')
        title = item.get('display_title')
        unread_count = item.get('unread_count')
        if not isinstance(chat_id, int):
            continue
        if not isinstance(title, str) or not title.strip():
            title = f'Chat #{chat_id}'
        open_title = title.strip()
        if isinstance(unread_count, int) and unread_count > 0:
            open_title = f'🔴 {open_title}'
        builder.button(text=open_title, callback_data=f'{CB_CHATS_OPEN_CHAT_PREFIX}{chat_id}')

    if total_pages > 1 and page > 1:
        builder.button(text=i18n.t(locale, 'chat.button.page_back'), callback_data=f'{CB_CHATS_PAGE_PREFIX}{page - 1}')
    if total_pages > 1 and page < total_pages:
        builder.button(text=i18n.t(locale, 'chat.button.page_next'), callback_data=f'{CB_CHATS_PAGE_PREFIX}{page + 1}')

    builder.button(text=i18n.t(locale, 'chat.button.start_new'), callback_data=CB_CHATS_NEW)
    if total_pages > 1 and page > 1 and page < total_pages:
        builder.adjust(*(1 for _ in chats), 2, 1)
    elif total_pages > 1 and (page > 1 or page < total_pages):
        builder.adjust(*(1 for _ in chats), 1, 1)
    else:
        builder.adjust(*(1 for _ in chats), 1)
    return builder.as_markup()


def chat_view_keyboard(
    *,
    i18n: LocalizationManager,
    locale: str,
    chat_id: int,
    page: int,
    has_older: bool,
    has_newer: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'chat.button.send'), callback_data=f'{CB_CHATS_SEND_PREFIX}{chat_id}')
    if has_older:
        builder.button(
            text=i18n.t(locale, 'chat.button.older'),
            callback_data=f'{CB_CHATS_MESSAGES_PAGE_PREFIX}{chat_id}:{page + 1}',
        )
    if has_newer and page > 1:
        builder.button(
            text=i18n.t(locale, 'chat.button.newer'),
            callback_data=f'{CB_CHATS_MESSAGES_PAGE_PREFIX}{chat_id}:{page - 1}',
        )
    builder.button(text=i18n.t(locale, 'chat.button.back_to_chats'), callback_data=CB_CHATS_OPEN)

    if has_older and has_newer and page > 1:
        builder.adjust(2, 1, 1)
    elif has_older or (has_newer and page > 1):
        builder.adjust(1, 1, 1)
    else:
        builder.adjust(1, 1)
    return builder.as_markup()


def chat_send_cancel_keyboard(*, i18n: LocalizationManager, locale: str, chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'chat.button.cancel_send'), callback_data=f'{CB_CHATS_CANCEL_SEND_PREFIX}{chat_id}')
    builder.adjust(1)
    return builder.as_markup()


def chat_new_cancel_keyboard(*, i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'chat.button.cancel_new'), callback_data=CB_CHATS_CANCEL_NEW)
    builder.adjust(1)
    return builder.as_markup()


def chat_new_message_notice_keyboard(*, chat_id: int, nickname: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f'🔴 {nickname}', callback_data=f'{CB_CHATS_OPEN_CHAT_PREFIX}{chat_id}')
    builder.adjust(1)
    return builder.as_markup()


def search_message_notice_keyboard(*, i18n: LocalizationManager, locale: str, user_id: int, game: GameCode) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'search.button.reply'), callback_data=f'{CB_SEARCH_MESSAGE_PREFIX}{user_id}')
    builder.button(text=i18n.t(locale, 'search.button.profile_short'), callback_data=f'{CB_SEARCH_VIEW_PROFILE_PREFIX}{user_id}:msg')
    builder.button(text=i18n.t(locale, 'search.button.hide_message'), callback_data=CB_SEARCH_HIDE_NOTICE)
    builder.adjust(2, 1)
    return builder.as_markup()


def search_subscription_notice_keyboard(*, i18n: LocalizationManager, locale: str, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'search.button.view_profile'), callback_data=f'{CB_SEARCH_VIEW_PROFILE_PREFIX}{user_id}')
    builder.button(text=i18n.t(locale, 'search.button.hide_message'), callback_data=CB_SEARCH_HIDE_NOTICE)
    builder.adjust(1)
    return builder.as_markup()


def search_hide_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'search.button.hide_message'), callback_data=CB_SEARCH_HIDE_NOTICE)
    builder.adjust(1)
    return builder.as_markup()


def search_message_cancel_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.cancel'), callback_data=CB_SEARCH_CANCEL_MESSAGE)
    builder.adjust(1)
    return builder.as_markup()
