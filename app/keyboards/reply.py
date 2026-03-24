from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.locales import LocalizationManager


def main_menu_keyboard(i18n: LocalizationManager, locale: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.t(locale, 'menu.find_teammate'))],
            [
                KeyboardButton(text=i18n.t(locale, 'menu.my_profiles')),
                KeyboardButton(text=i18n.t(locale, 'menu.profile')),
            ],
        ],
        resize_keyboard=True,
    )
