from sqlalchemy import and_, delete, exists, func, select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import GameCode
from app.models import User, UserLike, UserMessage, UserSubscription


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

    async def profile_counters(self, user_id: int) -> dict[str, int]:
        likes_stmt = select(func.count(UserLike.id)).where(UserLike.to_user_id == user_id)
        followers_stmt = select(func.count(UserSubscription.id)).where(UserSubscription.followed_user_id == user_id)
        subscriptions_stmt = select(func.count(UserSubscription.id)).where(UserSubscription.follower_user_id == user_id)

        reciprocal_like = aliased(UserLike)
        friends_stmt = (
            select(func.count(func.distinct(UserLike.from_user_id)))
            .where(UserLike.to_user_id == user_id)
            .where(
                exists(
                    select(1).where(
                        and_(
                            reciprocal_like.from_user_id == user_id,
                            reciprocal_like.to_user_id == UserLike.from_user_id,
                            reciprocal_like.game == UserLike.game,
                        )
                    )
                )
            )
        )

        likes = int((await self.session.scalar(likes_stmt)) or 0)
        followers = int((await self.session.scalar(followers_stmt)) or 0)
        subscriptions = int((await self.session.scalar(subscriptions_stmt)) or 0)
        friends = int((await self.session.scalar(friends_stmt)) or 0)

        return {
            'likes_count': likes,
            'followers_count': followers,
            'subscriptions_count': subscriptions,
            'friends_count': friends,
        }

    @staticmethod
    def _rows_to_items(rows) -> list[dict[str, int | str | None]]:
        items: list[dict[str, int | str | None]] = []
        for row in rows:
            items.append(
                {
                    'user_id': int(row.user_id),
                    'username': row.username,
                    'full_name': row.full_name,
                }
            )
        return items

    async def list_subscriptions(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        stmt = (
            select(User.id.label('user_id'), User.username, User.full_name)
            .join(UserSubscription, UserSubscription.followed_user_id == User.id)
            .where(UserSubscription.follower_user_id == user_id)
            .order_by(UserSubscription.created_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return self._rows_to_items(rows)

    async def list_subscribers(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        stmt = (
            select(User.id.label('user_id'), User.username, User.full_name)
            .join(UserSubscription, UserSubscription.follower_user_id == User.id)
            .where(UserSubscription.followed_user_id == user_id)
            .order_by(UserSubscription.created_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return self._rows_to_items(rows)

    async def list_my_likes(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        stmt = (
            select(User.id.label('user_id'), User.username, User.full_name)
            .join(UserLike, UserLike.to_user_id == User.id)
            .where(UserLike.from_user_id == user_id)
            .group_by(User.id, User.username, User.full_name)
            .order_by(func.max(UserLike.created_at).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return self._rows_to_items(rows)

    async def list_who_liked_me(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        stmt = (
            select(User.id.label('user_id'), User.username, User.full_name)
            .join(UserLike, UserLike.from_user_id == User.id)
            .where(UserLike.to_user_id == user_id)
            .group_by(User.id, User.username, User.full_name)
            .order_by(func.max(UserLike.created_at).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return self._rows_to_items(rows)

    async def list_friends(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        reciprocal_like = aliased(UserLike)
        stmt = (
            select(User.id.label('user_id'), User.username, User.full_name)
            .join(UserLike, UserLike.from_user_id == User.id)
            .where(UserLike.to_user_id == user_id)
            .where(
                exists(
                    select(1).where(
                        and_(
                            reciprocal_like.from_user_id == user_id,
                            reciprocal_like.to_user_id == UserLike.from_user_id,
                            reciprocal_like.game == UserLike.game,
                        )
                    )
                )
            )
            .group_by(User.id, User.username, User.full_name)
            .order_by(func.max(UserLike.created_at).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return self._rows_to_items(rows)
