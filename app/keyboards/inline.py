import uuid

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database import GameCode
from app.locales import LocalizationManager


LANGUAGE_CHOICES = (
    ('ru', 'Русский'),
    ('en', 'English'),
    ('uz', 'O\'zbekcha'),
)


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, title in LANGUAGE_CHOICES:
        builder.button(text=title, callback_data=f'lang:set:{code}')
    builder.adjust(3)
    return builder.as_markup()


def game_select_keyboard(i18n: LocalizationManager, locale: str, callback_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for game in GameCode:
        builder.button(text=i18n.t(locale, f'game.{game.value}'), callback_data=f'{callback_prefix}:{game.value}')
    builder.adjust(2)
    return builder.as_markup()


def create_profile_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.create_profile'), callback_data='profile:add')
    return builder.as_markup()


def add_other_game_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=i18n.t(locale, 'action.add_profile_other_game'),
        callback_data='profile:add',
    )
    return builder.as_markup()


def profile_actions_keyboard(i18n: LocalizationManager, locale: str, profile_id: uuid.UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.refill'), callback_data=f'profile:reset:{profile_id}')
    builder.button(text=i18n.t(locale, 'action.delete'), callback_data=f'profile:delete:{profile_id}')
    builder.adjust(2)
    return builder.as_markup()


def existing_profile_keyboard(i18n: LocalizationManager, locale: str, game: GameCode) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.update_existing'), callback_data=f'profile:update_game:{game.value}')
    return builder.as_markup()


def profile_settings_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.settings'), callback_data='settings:open')
    return builder.as_markup()


def settings_keyboard(i18n: LocalizationManager, locale: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t(locale, 'action.change_language'), callback_data='settings:language')
    return builder.as_markup()
