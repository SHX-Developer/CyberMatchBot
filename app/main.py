import asyncio
import logging
from pathlib import Path

from app.bot import create_bot, create_dispatcher
from app.config import get_settings
from app.database import create_engine, create_session_factory
from app.locales import LocalizationManager


async def run() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    locales_dir = Path(__file__).resolve().parent / 'locales'
    i18n = LocalizationManager(locales_dir=locales_dir, default_locale='ru')

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    bot = create_bot(settings.bot_token)
    dp = create_dispatcher(session_factory, i18n)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(run())
