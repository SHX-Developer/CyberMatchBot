from math import ceil

from app.models import User, UserChat
from app.repositories import ChatRepository, UserRepository


class ChatService:
    def __init__(self, session) -> None:
        self.chat_repo = ChatRepository(session)
        self.user_repo = UserRepository(session)

    async def list_user_chats_paginated(self, user_id: int, *, page: int, page_size: int = 10) -> dict[str, object]:
        total_items = await self.chat_repo.count_user_chats(user_id)
        total_pages = max(1, ceil(total_items / page_size))
        safe_page = max(1, min(page, total_pages))
        offset = (safe_page - 1) * page_size
        items = await self.chat_repo.list_user_chats(user_id, limit=page_size, offset=offset)
        return {
            'items': items,
            'page': safe_page,
            'total_pages': total_pages,
            'total_items': total_items,
        }

    async def find_user_by_nickname_or_username(self, value: str) -> User | None:
        return await self.user_repo.find_by_nickname_or_username(value)

    async def create_or_get_chat(self, user_id: int, target_user_id: int) -> tuple[UserChat, bool]:
        return await self.chat_repo.get_or_create_private_chat(user_id, target_user_id)

    async def get_chat_for_user(self, chat_id: int, user_id: int) -> UserChat | None:
        return await self.chat_repo.get_chat_for_user(chat_id, user_id)

    async def get_counterpart_user(self, chat: UserChat, user_id: int) -> User | None:
        counterpart_id = chat.participant_2_id if chat.participant_1_id == user_id else chat.participant_1_id
        return await self.user_repo.get_by_id(counterpart_id)

    async def delete_chat(self, chat_id: int, user_id: int) -> bool:
        chat = await self.chat_repo.get_chat_for_user(chat_id, user_id)
        if chat is None:
            return False
        await self.chat_repo.delete_chat(chat.id)
        return True
