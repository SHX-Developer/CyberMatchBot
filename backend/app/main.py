"""Минимальный Telegram-бот: /start → главное меню с кнопкой Web App."""
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.config import get_settings


logger = logging.getLogger(__name__)


WELCOME_TEXT = (
    '<b>Cyber Mate</b> — найди тиммейта за пару секунд.\n\n'
    'Создавай игровые анкеты, лайкай игроков и собирай команду для катки.\n\n'
    'Открой мини-приложение по кнопке ниже 👇'
)

# Старый логотип Cyber Mate, уже залитый в Telegram CDN — переиспользуем file_id.
WELCOME_PHOTO_FILE_ID = 'AgACAgIAAxkBAAILumnWAv0c6uSQOECSBFlaA7bPvM4jAALoFWsb43OwSmaQzA3VTpunAQADAgADeAADOwQ'

# Запасной локальный файл — если Telegram отвергнет file_id (например, бот сменили).
ASSETS_DIR = Path(__file__).resolve().parent / 'assets'
WELCOME_IMAGE_FALLBACK = ASSETS_DIR / 'games.png'

# Прямой URL Web App — используем всегда, даже если settings.webapp_url не задан.
WEBAPP_URL_DEFAULT = 'https://shx-cybermate.duckdns.org'


def _build_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='🎮 Открыть Cyber Mate',
                    web_app=WebAppInfo(url=webapp_url),
                ),
            ],
        ],
    )


async def cmd_start(message: Message) -> None:
    settings = get_settings()
    webapp_url = (getattr(settings, 'webapp_url', None) or WEBAPP_URL_DEFAULT).strip()
    keyboard = _build_keyboard(webapp_url)

    try:
        await message.answer_photo(
            photo=WELCOME_PHOTO_FILE_ID,
            caption=WELCOME_TEXT,
            reply_markup=keyboard,
        )
        return
    except TelegramBadRequest as exc:
        logger.warning('Failed to send welcome by file_id: %s; falling back to local file', exc)

    if WELCOME_IMAGE_FALLBACK.exists():
        await message.answer_photo(
            photo=FSInputFile(WELCOME_IMAGE_FALLBACK),
            caption=WELCOME_TEXT,
            reply_markup=keyboard,
        )
    else:
        await message.answer(WELCOME_TEXT, reply_markup=keyboard)


def create_bot(token: str) -> Bot:
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.register(cmd_start, CommandStart())
    return dp


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        force=True,
    )
    settings = get_settings()
    bot = create_bot(settings.bot_token)
    dp = create_dispatcher()
    logger.info('Bot started. Press Ctrl+C to stop.')
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(run())
