import asyncio
import logging
from pathlib import Path
from contextlib import suppress

logger = logging.getLogger(__name__)


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        force=True,
    )
    logger.info('Bootstrapping application...')

    from app.config import get_settings

    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        force=True,
    )
    logger.info('Starting CyberMate bot...')
    logger.info('Loading bot framework...')
    from app.bot import create_bot, create_dispatcher
    from aiogram.exceptions import TelegramNetworkError
    from app.database import create_engine, create_session_factory
    from app.locales import LocalizationManager
    logger.info('Bot framework loaded.')

    locales_dir = Path(__file__).resolve().parent / 'locales'
    i18n = LocalizationManager(locales_dir=locales_dir, default_locale='ru')

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    bot = create_bot(settings.bot_token)
    dp = create_dispatcher(session_factory, i18n)

    try:
        logger.info('Checking Telegram API connectivity...')
        me = await asyncio.wait_for(bot.get_me(), timeout=20)
        logger.info('Telegram authorization successful: @%s (id=%s)', me.username, me.id)
        logger.info('Polling started. Press Ctrl+C to stop.')
        await dp.start_polling(bot)
    except TimeoutError:
        logger.exception(
            'Telegram API check timed out. Verify internet connection, BOT_TOKEN, or VPN/proxy settings.'
        )
        return
    except TelegramNetworkError:
        logger.exception(
            'Telegram is unreachable (DNS/network error). Check internet, DNS, firewall, or VPN settings.'
        )
        return
    except Exception:
        logger.exception('Bot failed to start')
        raise
    finally:
        logger.info('Shutting down bot...')
        with suppress(Exception):
            await bot.session.close()
        try:
            await engine.dispose()
        except Exception:
            logger.warning('Database engine dispose skipped due to missing optional dependency.')


if __name__ == '__main__':
    asyncio.run(run())
