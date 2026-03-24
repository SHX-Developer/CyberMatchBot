import uuid

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    for game in GameCode:
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
