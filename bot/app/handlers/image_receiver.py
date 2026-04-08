from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

router = Router(name='image_receiver')
OWNER_USER_ID = 284929331


@router.message(StateFilter(None), F.photo, F.from_user.id == OWNER_USER_ID)
async def image_file_id_handler(message: Message) -> None:
    if not message.photo:
        return

    file_id = message.photo[-1].file_id
    await message.answer(
        f'🖼 ID картинки:\n<code>{escape(file_id)}</code>',
        parse_mode='HTML',
    )
