from app.database import GameCode
from app.models import UserMessage
from app.repositories import InteractionRepository


class InteractionService:
    def __init__(self, session) -> None:
        self.repo = InteractionRepository(session)

    async def add_like(self, from_user_id: int, to_user_id: int, game: GameCode) -> bool:
        return await self.repo.add_like(from_user_id, to_user_id, game)

    async def has_like(self, from_user_id: int, to_user_id: int, game: GameCode) -> bool:
        return await self.repo.has_like(from_user_id, to_user_id, game)

    async def is_mutual_like(self, user_a: int, user_b: int, game: GameCode) -> bool:
        return await self.repo.is_mutual_like(user_a, user_b, game)

    async def is_subscribed(self, follower_user_id: int, followed_user_id: int) -> bool:
        return await self.repo.is_subscribed(follower_user_id, followed_user_id)

    async def toggle_subscription(self, follower_user_id: int, followed_user_id: int) -> bool:
        return await self.repo.toggle_subscription(follower_user_id, followed_user_id)

    async def create_message(self, from_user_id: int, to_user_id: int, text: str) -> UserMessage:
        return await self.repo.create_message(from_user_id, to_user_id, text)

    async def list_subscriptions(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        return await self.repo.list_subscriptions(user_id, limit=limit)

    async def list_subscribers(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        return await self.repo.list_subscribers(user_id, limit=limit)

    async def list_my_likes(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        return await self.repo.list_my_likes(user_id, limit=limit)

    async def list_who_liked_me(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        return await self.repo.list_who_liked_me(user_id, limit=limit)

    async def list_friends(self, user_id: int, *, limit: int = 50) -> list[dict[str, int | str | None]]:
        return await self.repo.list_friends(user_id, limit=limit)
