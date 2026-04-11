from enum import Enum


class LanguageCode(str, Enum):
    RU = 'ru'
    EN = 'en'
    UZ = 'uz'


class UserGenderCode(str, Enum):
    NOT_SPECIFIED = 'not_specified'
    MALE = 'male'
    FEMALE = 'female'


class GameCode(str, Enum):
    MLBB = 'mlbb'
    GENSHIN_IMPACT = 'genshin_impact'
    PUBG_MOBILE = 'pubg_mobile'
    CS_GO = 'cs_go'


class MlbbLaneCode(str, Enum):
    GOLD = 'gold_lane'
    MID = 'mid_lane'
    EXP = 'exp_lane'
    JUNGLE = 'jungler'
    ROAM = 'roamer'
    ALL = 'all_lanes'
