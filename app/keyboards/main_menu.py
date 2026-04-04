from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.locales import LocalizationManager


def main_menu_keyboard(i18n: LocalizationManager, locale: str) -> ReplyKeyboardMarkup:
    rows = (
        (i18n.t(locale, 'menu.find_teammate'),),
        (i18n.t(locale, 'menu.chat'), i18n.t(locale, 'menu.activity')),
        (i18n.t(locale, 'menu.my_profiles'), i18n.t(locale, 'menu.profile')),
    )
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=title) for title in row] for row in rows],
        resize_keyboard=True,
        is_persistent=False,
    )
