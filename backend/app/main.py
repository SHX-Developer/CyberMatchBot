"""Минимальный Telegram-бот: /start → главное меню с кнопкой Web App."""
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
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

# Картинка главного меню. assets/games.png — готовый промо-баннер из ассетов проекта.
ASSETS_DIR = Path(__file__).resolve().parent / 'assets'
WELCOME_IMAGE = ASSETS_DIR / 'games.png'

# URL Web App. Когда задеплоим фронт — пропишем сюда (env WEBAPP_URL).
# Пустая строка = кнопка не добавляется.
def _build_keyboard(webapp_url: str | None) -> InlineKeyboardMarkup | None:
    if not webapp_url:
        return None
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
    keyboard = _build_keyboard(getattr(settings, 'webapp_url', None))

    photo = FSInputFile(WELCOME_IMAGE) if WELCOME_IMAGE.exists() else None
    if photo is not None:
        await message.answer_photo(photo=photo, caption=WELCOME_TEXT, reply_markup=keyboard)
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
