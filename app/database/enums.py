from enum import Enum


class LanguageCode(str, Enum):
    RU = 'ru'
    EN = 'en'
    UZ = 'uz'


class GameCode(str, Enum):
    MLBB = 'mlbb'
    CS_GO = 'cs_go'
