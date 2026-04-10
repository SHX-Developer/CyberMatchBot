from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.locales import LocalizationManager


def _with_count(text: str, count: int) -> str:
    return f'{text} ({count})' if count > 0 else text


def main_menu_keyboard(
    i18n: LocalizationManager,
    locale: str,
    *,
    unread_messages: int = 0,
    unread_activity: int = 0,
) -> ReplyKeyboardMarkup:
    messages_button = _with_count(i18n.t(locale, 'menu.chat'), unread_messages)
    activity_button = _with_count(i18n.t(locale, 'menu.activity'), unread_activity)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.t(locale, 'menu.find_teammate'), style='primary')],
            [KeyboardButton(text=messages_button), KeyboardButton(text=activity_button)],
            [KeyboardButton(text=i18n.t(locale, 'menu.my_profiles')), KeyboardButton(text=i18n.t(locale, 'menu.profile'))],
        ],
        resize_keyboard=True,
        is_persistent=False,
    )
