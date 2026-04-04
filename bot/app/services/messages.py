from math import ceil

from app.models import UserMessage
from app.repositories import ChatRepository


MESSAGE_MAX_LENGTH = 1000


class MessageService:
    def __init__(self, session) -> None:
        self.chat_repo = ChatRepository(session)

    async def list_chat_messages_paginated(
        self,
        *,
        chat_id: int,
        user_id: int,
        page: int,
        page_size: int = 10,
    ) -> dict[str, object] | None:
        chat = await self.chat_repo.get_chat_for_user(chat_id, user_id)
        if chat is None:
            return None

        await self.chat_repo.mark_chat_messages_read(chat_id=chat.id, user_id=user_id)
        total_items = await self.chat_repo.count_messages(chat.id)
        total_pages = max(1, ceil(total_items / page_size))
        safe_page = max(1, min(page, total_pages))
        offset_from_latest = (safe_page - 1) * page_size
        items = await self.chat_repo.list_messages_from_latest(chat.id, limit=page_size, offset_from_latest=offset_from_latest)
        return {
            'chat': chat,
            'items': items,
            'page': safe_page,
            'total_pages': total_pages,
            'total_items': total_items,
            'has_older': safe_page < total_pages,
            'has_newer': safe_page > 1,
        }

    async def send_message_in_chat(self, *, chat_id: int, sender_id: int, text: str) -> tuple[UserMessage | None, str | None]:
        chat = await self.chat_repo.get_chat_for_user(chat_id, sender_id)
        if chat is None:
            return None, 'chat_not_found'

        cleaned = text.strip()
        if not cleaned:
            return None, 'empty_message'
        if len(cleaned) > MESSAGE_MAX_LENGTH:
            return None, 'too_long'

        receiver_id = chat.participant_2_id if chat.participant_1_id == sender_id else chat.participant_1_id
        entity = await self.chat_repo.create_message(
            chat_id=chat.id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            text=cleaned,
            message_type='text',
        )
        return entity, None

    async def send_direct_message(self, *, sender_id: int, receiver_id: int, text: str) -> tuple[UserMessage | None, str | None]:
        if sender_id == receiver_id:
            return None, 'cannot_message_self'

        cleaned = text.strip()
        if not cleaned:
            return None, 'empty_message'
        if len(cleaned) > MESSAGE_MAX_LENGTH:
            return None, 'too_long'

        chat, _ = await self.chat_repo.get_or_create_private_chat(sender_id, receiver_id)
        entity = await self.chat_repo.create_message(
            chat_id=chat.id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            text=cleaned,
            message_type='text',
        )
        return entity, None
