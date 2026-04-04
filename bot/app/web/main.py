from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import GameCode, MlbbLaneCode, create_engine, create_session_factory
from app.services import ChatService, InteractionService, MessageService, ProfileService, UserService


class StartChatPayload(BaseModel):
    user_id: int
    target: str


class SendChatMessagePayload(BaseModel):
    user_id: int
    text: str = Field(min_length=1, max_length=1000)


class ToggleSubscriptionPayload(BaseModel):
    user_id: int
    target_user_id: int


class LikePayload(BaseModel):
    user_id: int
    target_user_id: int
    game: GameCode = GameCode.MLBB


class DirectMessagePayload(BaseModel):
    user_id: int
    target_user_id: int
    text: str = Field(min_length=1, max_length=1000)


class SaveMlbbProfilePayload(BaseModel):
    user_id: int
    game_player_id: str = Field(min_length=3, max_length=64)
    rank: str | None = Field(default=None, max_length=64)
    role: str | None = Field(default=None, max_length=64)
    server: str | None = Field(default=None, max_length=64)
    main_lane: MlbbLaneCode = MlbbLaneCode.ALL
    extra_lanes: list[MlbbLaneCode] = Field(default_factory=list)
    description: str = Field(min_length=1, max_length=500)
    mythic_stars: int | None = Field(default=None, ge=0, le=1000)
    profile_image_file_id: str | None = Field(default=None, max_length=255)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory
    yield
    await engine.dispose()


app = FastAPI(title='CyberMatch Web API', version='0.1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _profile_to_dict(profile) -> dict[str, object]:
    return {
        'id': str(profile.id),
        'owner_id': int(profile.owner_id),
        'game': profile.game.value,
        'game_player_id': profile.game_player_id,
        'rank': profile.rank,
        'role': profile.role,
        'play_time': profile.play_time,
        'about': profile.about,
        'description': profile.description,
        'main_lane': profile.main_lane.value if profile.main_lane else None,
        'extra_lanes': profile.extra_lanes or [],
        'mythic_stars': profile.mythic_stars,
        'profile_image_file_id': profile.profile_image_file_id,
        'created_at': _iso(profile.created_at),
        'updated_at': _iso(profile.updated_at),
    }


def _user_to_dict(user) -> dict[str, object] | None:
    if user is None:
        return None
    return {
        'id': int(user.id),
        'username': user.username,
        'full_name': user.full_name,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language': user.language_code.value if user.language_code else None,
        'registered_at': _iso(user.registered_at),
    }


@app.get('/v1/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/v1/profile')
async def get_profile(user_id: int = Query(...), session: AsyncSession = Depends(get_session)):
    payload = await UserService(session).get_profile_stats(user_id)
    user = payload.get('user')
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    return {
        'user': _user_to_dict(user),
        'profiles_count': int(payload.get('profiles_count', 0) or 0),
        'likes_count': int(payload.get('likes_count', 0) or 0),
        'followers_count': int(payload.get('followers_count', 0) or 0),
        'subscriptions_count': int(payload.get('subscriptions_count', 0) or 0),
        'friends_count': int(payload.get('friends_count', 0) or 0),
    }


@app.get('/v1/profiles')
async def list_my_profiles(user_id: int = Query(...), session: AsyncSession = Depends(get_session)):
    items = await ProfileService(session).list_my_profiles(user_id)
    return {'items': [_profile_to_dict(item) for item in items]}


@app.post('/v1/profiles/mlbb')
async def save_mlbb_profile(payload: SaveMlbbProfilePayload, session: AsyncSession = Depends(get_session)):
    profile = await ProfileService(session).save_mlbb_profile(
        owner_id=payload.user_id,
        game_player_id=payload.game_player_id,
        profile_image_file_id=payload.profile_image_file_id or 'webapp-placeholder',
        rank=payload.rank,
        role=payload.role,
        server=payload.server,
        main_lane=payload.main_lane,
        extra_lanes=payload.extra_lanes,
        description=payload.description,
        mythic_stars=payload.mythic_stars,
    )
    return {'item': _profile_to_dict(profile)}


@app.post('/v1/profiles/{profile_id}/reset')
async def reset_profile(
    profile_id: UUID,
    user_id: int = Query(...),
    session: AsyncSession = Depends(get_session),
):
    ok = await ProfileService(session).reset_owned_profile(user_id, profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Profile not found')
    return {'ok': True}


@app.delete('/v1/profiles/{profile_id}')
async def delete_profile(
    profile_id: UUID,
    user_id: int = Query(...),
    session: AsyncSession = Depends(get_session),
):
    ok = await ProfileService(session).delete_owned_profile(user_id, profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Profile not found')
    return {'ok': True}


@app.get('/v1/search')
async def search_profiles(
    user_id: int = Query(...),
    game: GameCode = Query(GameCode.MLBB),
    session: AsyncSession = Depends(get_session),
):
    profile_service = ProfileService(session)
    interaction_service = InteractionService(session)
    rows = await profile_service.search_profiles(user_id, game)
    items: list[dict[str, object]] = []
    for profile, owner in rows:
        items.append(
            {
                'profile': _profile_to_dict(profile),
                'owner': _user_to_dict(owner),
                'liked': await interaction_service.has_like(user_id, int(owner.id), game),
                'subscribed': await interaction_service.is_subscribed(user_id, int(owner.id)),
            }
        )
    return {'items': items}


@app.post('/v1/interactions/like')
async def like_user(payload: LikePayload, session: AsyncSession = Depends(get_session)):
    ok = await InteractionService(session).add_like(payload.user_id, payload.target_user_id, payload.game)
    return {'ok': ok}


@app.post('/v1/interactions/subscription/toggle')
async def toggle_subscription(payload: ToggleSubscriptionPayload, session: AsyncSession = Depends(get_session)):
    subscribed = await InteractionService(session).toggle_subscription(payload.user_id, payload.target_user_id)
    return {'subscribed': bool(subscribed)}


@app.post('/v1/interactions/message')
async def send_direct_message(payload: DirectMessagePayload, session: AsyncSession = Depends(get_session)):
    try:
        entity = await InteractionService(session).create_message(payload.user_id, payload.target_user_id, payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'id': int(entity.id), 'chat_id': int(entity.chat_id)}


@app.get('/v1/activity/{section}')
async def activity(
    section: str,
    user_id: int = Query(...),
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    interactions = InteractionService(session)
    if section == 'subscriptions':
        items = await interactions.list_subscriptions(user_id, limit=limit)
    elif section == 'subscribers':
        items = await interactions.list_subscribers(user_id, limit=limit)
    elif section == 'likes':
        items = await interactions.list_my_likes(user_id, limit=limit)
    elif section == 'liked_by':
        items = await interactions.list_who_liked_me(user_id, limit=limit)
    elif section == 'friends':
        items = await interactions.list_friends(user_id, limit=limit)
    else:
        raise HTTPException(status_code=400, detail='Unknown section')
    return {'items': items}


@app.get('/v1/chats')
async def list_chats(
    user_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    payload = await ChatService(session).list_user_chats_paginated(user_id, page=page, page_size=page_size)
    return payload


@app.post('/v1/chats/start')
async def start_chat(payload: StartChatPayload, session: AsyncSession = Depends(get_session)):
    service = ChatService(session)
    target_user = await service.find_user_by_nickname_or_username(payload.target)
    if target_user is None:
        raise HTTPException(status_code=404, detail='Target user not found')
    if int(target_user.id) == payload.user_id:
        raise HTTPException(status_code=400, detail='Cannot create chat with self')
    chat, created = await service.create_or_get_chat(payload.user_id, int(target_user.id))
    return {'chat_id': int(chat.id), 'created': bool(created), 'target_user_id': int(target_user.id)}


@app.get('/v1/chats/{chat_id}/messages')
async def list_chat_messages(
    chat_id: int,
    user_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    chat_service = ChatService(session)
    chat = await chat_service.get_chat_for_user(chat_id, user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail='Chat not found')
    counterpart = await chat_service.get_counterpart_user(chat, user_id)
    payload = await MessageService(session).list_chat_messages_paginated(
        chat_id=chat_id,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail='Chat not found')

    items = []
    for item in payload.get('items', []):
        items.append(
            {
                'id': int(item.id),
                'from_user_id': int(item.from_user_id),
                'to_user_id': int(item.to_user_id),
                'text': item.text,
                'is_read': bool(item.is_read),
                'created_at': _iso(item.created_at),
            }
        )

    return {
        'chat_id': int(chat.id),
        'counterpart': _user_to_dict(counterpart),
        'page': int(payload.get('page', 1)),
        'total_pages': int(payload.get('total_pages', 1)),
        'total_items': int(payload.get('total_items', 0)),
        'has_older': bool(payload.get('has_older', False)),
        'has_newer': bool(payload.get('has_newer', False)),
        'items': items,
    }


@app.post('/v1/chats/{chat_id}/messages')
async def send_chat_message(
    chat_id: int,
    payload: SendChatMessagePayload,
    session: AsyncSession = Depends(get_session),
):
    entity, error = await MessageService(session).send_message_in_chat(
        chat_id=chat_id,
        sender_id=payload.user_id,
        text=payload.text,
    )
    if entity is None:
        raise HTTPException(status_code=400, detail=error or 'message_send_failed')
    return {
        'id': int(entity.id),
        'chat_id': int(entity.chat_id),
        'from_user_id': int(entity.from_user_id),
        'to_user_id': int(entity.to_user_id),
        'text': entity.text,
        'created_at': _iso(entity.created_at),
    }


@app.delete('/v1/chats/{chat_id}')
async def delete_chat(
    chat_id: int,
    user_id: int = Query(...),
    session: AsyncSession = Depends(get_session),
):
    ok = await ChatService(session).delete_chat(chat_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Chat not found')
    return {'ok': True}
