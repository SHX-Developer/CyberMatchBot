import logging

from aiogram import F, Router
from aiogram.types import Message, ReplyKeyboardRemove


router = Router(name='group_guard')
logger = logging.getLogger(__name__)
_CLEANED_GROUP_CHATS: set[int] = set()


@router.message(F.chat.type.in_({'group', 'supergroup'}), F.text)
async def group_text_guard(message: Message) -> None:
    chat_id = message.chat.id
    logger.info('Group text message received: chat_id=%s', chat_id)

    if chat_id in _CLEANED_GROUP_CHATS:
        return
    _CLEANED_GROUP_CHATS.add(chat_id)
    try:
        cleanup = await message.bot.send_message(
            chat_id=chat_id,
            text='\u2063',
            reply_markup=ReplyKeyboardRemove(),
        )
        await cleanup.delete()
    except Exception:
        pass
