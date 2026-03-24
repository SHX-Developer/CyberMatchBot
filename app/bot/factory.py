from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.handlers import setup_routers
from app.locales import LocalizationManager
from app.middlewares import DBSessionMiddleware


def create_bot(token: str) -> Bot:
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_dispatcher(session_factory: async_sessionmaker, i18n: LocalizationManager) -> Dispatcher:
    dp = Dispatcher()
    dp.update.middleware(DBSessionMiddleware(session_factory))
    dp['i18n'] = i18n
    setup_routers(dp)
    return dp
