from sqlalchemy import and_, case, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserChat, UserMessage


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _normalize_pair(user_a_id: int, user_b_id: int) -> tuple[int, int]:
        if user_a_id == user_b_id:
            raise ValueError('Cannot create chat with self')
        return (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)

    async def get_chat_by_pair(self, user_a_id: int, user_b_id: int) -> UserChat | None:
        participant_1_id, participant_2_id = self._normalize_pair(user_a_id, user_b_id)
        stmt = select(UserChat).where(
            and_(
                UserChat.participant_1_id == participant_1_id,
                UserChat.participant_2_id == participant_2_id,
            )
        )
        return await self.session.scalar(stmt)

    async def get_or_create_private_chat(self, user_a_id: int, user_b_id: int) -> tuple[UserChat, bool]:
        existing = await self.get_chat_by_pair(user_a_id, user_b_id)
        if existing is not None:
            return existing, False

        participant_1_id, participant_2_id = self._normalize_pair(user_a_id, user_b_id)
        entity = UserChat(participant_1_id=participant_1_id, participant_2_id=participant_2_id)
        self.session.add(entity)
        await self.session.flush()
        return entity, True

    async def get_chat_for_user(self, chat_id: int, user_id: int) -> UserChat | None:
        stmt = select(UserChat).where(
            and_(
                UserChat.id == chat_id,
                or_(UserChat.participant_1_id == user_id, UserChat.participant_2_id == user_id),
            )
        )
        return await self.session.scalar(stmt)

    async def count_user_chats(self, user_id: int) -> int:
        stmt = select(func.count(UserChat.id)).where(
            or_(UserChat.participant_1_id == user_id, UserChat.participant_2_id == user_id)
        )
        return int((await self.session.scalar(stmt)) or 0)

    async def list_user_chats(self, user_id: int, *, limit: int, offset: int) -> list[dict[str, int | str | None]]:
        counterpart_id_expr = case(
            (UserChat.participant_1_id == user_id, UserChat.participant_2_id),
            else_=UserChat.participant_1_id,
        )
        unread_count_subquery = (
            select(func.count(UserMessage.id))
            .where(
                and_(
                    UserMessage.chat_id == UserChat.id,
                    UserMessage.to_user_id == user_id,
                    UserMessage.is_read.is_(False),
                )
            )
            .correlate(UserChat)
            .scalar_subquery()
        )
        stmt = (
            select(
                UserChat.id.label('chat_id'),
                User.id.label('counterpart_id'),
                User.full_name,
                User.username,
                UserChat.last_message_at,
                unread_count_subquery.label('unread_count'),
            )
            .join(User, User.id == counterpart_id_expr)
            .where(or_(UserChat.participant_1_id == user_id, UserChat.participant_2_id == user_id))
            .order_by(desc(UserChat.last_message_at), desc(UserChat.id))
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                'chat_id': int(row.chat_id),
                'counterpart_id': int(row.counterpart_id),
                'full_name': row.full_name,
                'username': row.username,
                'unread_count': int(row.unread_count or 0),
            }
            for row in rows
        ]

    async def mark_chat_messages_read(self, *, chat_id: int, user_id: int) -> None:
        stmt = (
            update(UserMessage)
            .where(
                and_(
                    UserMessage.chat_id == chat_id,
                    UserMessage.to_user_id == user_id,
                    UserMessage.is_read.is_(False),
                )
            )
            .values(is_read=True)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_chat(self, chat_id: int) -> None:
        entity = await self.session.get(UserChat, chat_id)
        if entity is None:
            return
        await self.session.delete(entity)
        await self.session.flush()

    async def count_messages(self, chat_id: int) -> int:
        stmt = select(func.count(UserMessage.id)).where(UserMessage.chat_id == chat_id)
        return int((await self.session.scalar(stmt)) or 0)

    async def list_messages_from_latest(self, chat_id: int, *, limit: int, offset_from_latest: int) -> list[UserMessage]:
        stmt = (
            select(UserMessage)
            .where(UserMessage.chat_id == chat_id)
            .order_by(desc(UserMessage.created_at), desc(UserMessage.id))
            .offset(offset_from_latest)
            .limit(limit)
        )
        rows = list((await self.session.scalars(stmt)).all())
        rows.reverse()
        return rows

    async def create_message(
        self,
        *,
        chat_id: int,
        sender_id: int,
        receiver_id: int,
        text: str,
        message_type: str = 'text',
    ) -> UserMessage:
        entity = UserMessage(
            chat_id=chat_id,
            from_user_id=sender_id,
            to_user_id=receiver_id,
            text=text,
            message_type=message_type,
        )
        self.session.add(entity)

        chat = await self.session.get(UserChat, chat_id)
        if chat is not None:
            chat.last_message_at = func.now()

        await self.session.flush()
        return entity
