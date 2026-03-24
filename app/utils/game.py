from app.database import GameCode, MlbbLaneCode
from app.locales import LocalizationManager


def game_label(i18n: LocalizationManager, locale: str, game: GameCode) -> str:
    return i18n.t(locale, f'game.{game.value}')


def lane_label(i18n: LocalizationManager, locale: str, lane: MlbbLaneCode | str) -> str:
    lane_code = lane.value if isinstance(lane, MlbbLaneCode) else lane
    return i18n.t(locale, f'mlbb.lane.{lane_code}')
