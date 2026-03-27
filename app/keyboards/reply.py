from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.constants import BTN_BACK, BTN_CREATE_PROFILE, BTN_MY_PROFILES, BTN_SETTINGS


def _reply_markup(rows: tuple[tuple[str, ...], ...]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=title) for title in row] for row in rows],
        resize_keyboard=True,
        is_persistent=False,
    )


def back_keyboard() -> ReplyKeyboardMarkup:
    return _reply_markup(((BTN_BACK,),))


def find_teammate_without_profiles_keyboard() -> ReplyKeyboardMarkup:
    return _reply_markup(((BTN_MY_PROFILES,), (BTN_BACK,)))


def my_profiles_empty_keyboard() -> ReplyKeyboardMarkup:
    return _reply_markup(((BTN_CREATE_PROFILE,), (BTN_BACK,)))


def profile_section_keyboard() -> ReplyKeyboardMarkup:
    return _reply_markup(((BTN_SETTINGS,), (BTN_BACK,)))
