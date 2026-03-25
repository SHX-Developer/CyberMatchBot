from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.constants import MAIN_MENU_ROWS


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=title) for title in row] for row in MAIN_MENU_ROWS],
        resize_keyboard=True,
        is_persistent=True,
    )
