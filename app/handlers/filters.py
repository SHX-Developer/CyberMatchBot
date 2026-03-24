from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.locales import LocalizationManager


class LocalizedTextFilter(BaseFilter):
    def __init__(self, key: str) -> None:
        self.key = key

    async def __call__(self, message: Message, i18n: LocalizationManager) -> bool:
        return i18n.match_key(self.key, message.text)
