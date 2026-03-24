from app.database import GameCode
from app.locales import LocalizationManager


def game_label(i18n: LocalizationManager, locale: str, game: GameCode) -> str:
    return i18n.t(locale, f'game.{game.value}')
