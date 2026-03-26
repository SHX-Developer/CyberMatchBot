from sqlalchemy import and_, delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode
from app.models import UserLike, UserMessage, UserSubscription


class InteractionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def has_like(self, from_user_id: int, to_user_id: int, game: GameCode) -> bool:
        stmt = select(
            exists().where(
                and_(
                    UserLike.from_user_id == from_user_id,
                    UserLike.to_user_id == to_user_id,
                    UserLike.game == game,
                )
            )
        )
        return bool(await self.session.scalar(stmt))

    async def add_like(self, from_user_id: int, to_user_id: int, game: GameCode) -> bool:
        if await self.has_like(from_user_id, to_user_id, game):
            return False
        self.session.add(UserLike(from_user_id=from_user_id, to_user_id=to_user_id, game=game))
        await self.session.flush()
        return True

    async def is_mutual_like(self, user_a: int, user_b: int, game: GameCode) -> bool:
        return await self.has_like(user_a, user_b, game) and await self.has_like(user_b, user_a, game)

    async def is_subscribed(self, follower_user_id: int, followed_user_id: int) -> bool:
        stmt = select(
            exists().where(
                and_(
                    UserSubscription.follower_user_id == follower_user_id,
                    UserSubscription.followed_user_id == followed_user_id,
                )
            )
        )
        return bool(await self.session.scalar(stmt))

    async def subscribe(self, follower_user_id: int, followed_user_id: int) -> bool:
        if await self.is_subscribed(follower_user_id, followed_user_id):
            return False
        self.session.add(UserSubscription(follower_user_id=follower_user_id, followed_user_id=followed_user_id))
        await self.session.flush()
        return True

    async def unsubscribe(self, follower_user_id: int, followed_user_id: int) -> bool:
        if not await self.is_subscribed(follower_user_id, followed_user_id):
            return False
        stmt = delete(UserSubscription).where(
            and_(
                UserSubscription.follower_user_id == follower_user_id,
                UserSubscription.followed_user_id == followed_user_id,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return True

    async def toggle_subscription(self, follower_user_id: int, followed_user_id: int) -> bool:
        if await self.is_subscribed(follower_user_id, followed_user_id):
            await self.unsubscribe(follower_user_id, followed_user_id)
            return False
        await self.subscribe(follower_user_id, followed_user_id)
        return True

    async def create_message(self, from_user_id: int, to_user_id: int, text: str) -> UserMessage:
        entity = UserMessage(from_user_id=from_user_id, to_user_id=to_user_id, text=text)
        self.session.add(entity)
        await self.session.flush()
        return entity
