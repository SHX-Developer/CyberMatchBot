from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import AsyncGenerator
from uuid import UUID

import re

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import (
    GameCode,
    LanguageCode,
    MlbbLaneCode,
    ProfileStatus,
    UserGenderCode,
    create_engine,
    create_session_factory,
)
from app.models import PlayerProfile, User
from app.repositories import ProfileRepository, UserRepository
from app.services import (
    ChatService,
    InteractionService,
    MessageService,
    ProfileService,
    UserService,
)
from app.web.auth import TelegramAuth, get_telegram_auth
from app.web.ws import broadcast_message, router as ws_router


# ────────────────────────────────────────────────────────────────────────────
# Pydantic payloads
# ────────────────────────────────────────────────────────────────────────────


NICKNAME_RE = re.compile(r'^[a-z0-9](?:[a-z0-9_]{1,18}[a-z0-9])$')
NICKNAME_FORBIDDEN = {
    'admin', 'support', 'moderator', 'system', 'cybermate', 'cyber', 'mate',
    'help', 'info', 'official', 'staff',
}


def _normalize_nickname(value: str) -> str:
    return value.strip().lower()


def _validate_nickname(value: str) -> tuple[str | None, str | None]:
    """Return (nickname, error_code). Error codes mirror frontend."""
    n = _normalize_nickname(value or '')
    if not n:
        return None, 'empty'
    if len(n) < 3:
        return None, 'too_short'
    if len(n) > 20:
        return None, 'too_long'
    if not re.fullmatch(r'[a-z0-9_]+', n):
        return None, 'bad_chars'
    if n.startswith('_'):
        return None, 'leading_underscore'
    if n.endswith('_'):
        return None, 'trailing_underscore'
    if '__' in n:
        return None, 'double_underscore'
    if not NICKNAME_RE.fullmatch(n):
        return None, 'bad_format'
    if n in NICKNAME_FORBIDDEN:
        return None, 'forbidden'
    return n, None


class RegisterPayload(BaseModel):
    language: LanguageCode
    birth_date: date | None = None
    gender: UserGenderCode
    nickname: str

    @field_validator('gender')
    @classmethod
    def gender_not_default(cls, v: UserGenderCode) -> UserGenderCode:
        if v == UserGenderCode.NOT_SPECIFIED:
            raise ValueError('Gender must be male, female, or hidden')
        return v


class CreateGameProfilePayload(BaseModel):
    game: GameCode
    game_nickname: str = Field(min_length=2, max_length=64)
    game_id: str = Field(min_length=3, max_length=32)
    server_id: str | None = Field(default=None, max_length=32)
    region: str | None = Field(default=None, max_length=32)
    rank: str | None = Field(default=None, max_length=64)
    main_role: str = Field(min_length=2, max_length=64)
    secondary_roles: list[str] = Field(default_factory=list)
    looking_for: list[str] = Field(default_factory=list)
    play_style: str | None = Field(default=None, max_length=32)
    microphone: str | None = Field(default=None, max_length=16)
    play_time_slots: list[str] = Field(default_factory=list)
    about: str = Field(min_length=10, max_length=300)
    # data:image/...;base64,... — после сжатия на фронте обычно 80–250 КБ,
    # лимит ~3 МБ как у аватара.
    screenshot_url: str | None = Field(default=None, max_length=3_000_000)


class UpdateGameProfileStatusPayload(BaseModel):
    status: ProfileStatus


class ApiStartChatPayload(BaseModel):
    target_user_id: int


class ApiSendMessagePayload(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class ApiLikePayload(BaseModel):
    target_user_id: int
    game: GameCode = GameCode.MLBB


class ApiSubscribePayload(BaseModel):
    target_user_id: int


class ApiDirectMessagePayload(BaseModel):
    target_user_id: int
    text: str = Field(min_length=1, max_length=1000)


class UpdateMePayload(BaseModel):
    language: LanguageCode | None = None
    gender: UserGenderCode | None = None
    birth_date: date | None = None
    nickname: str | None = None
    # пустая строка → очистить аватар, data URL ≤ ~2 МБ.
    avatar_data_url: str | None = Field(default=None, max_length=3_000_000)

    @field_validator('gender')
    @classmethod
    def gender_not_default(cls, v: UserGenderCode | None) -> UserGenderCode | None:
        if v is not None and v == UserGenderCode.NOT_SPECIFIED:
            raise ValueError('Gender cannot be reset to not_specified')
        return v


# ────────────────────────────────────────────────────────────────────────────
# App + lifespan + DB session dep
# ────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory
    yield
    await engine.dispose()


app = FastAPI(title='CyberMate Web API', version='0.2.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(ws_router)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ────────────────────────────────────────────────────────────────────────────
# Serializers
# ────────────────────────────────────────────────────────────────────────────


def _profile_to_dict(profile: PlayerProfile) -> dict[str, object]:
    return {
        'id': str(profile.id),
        'owner_id': int(profile.owner_id),
        'game': profile.game.value,
        'status': profile.status.value if profile.status else 'active',
        'game_nickname': profile.game_nickname,
        'game_id': profile.game_player_id,
        'server_id': profile.server_id,
        'region': profile.region,
        'rank': profile.rank,
        'main_role': profile.main_role or profile.role,
        'secondary_roles': profile.secondary_roles or [],
        'looking_for': profile.looking_for or [],
        'play_style': profile.play_style,
        'microphone': profile.microphone,
        'play_time_slots': profile.play_time_slots or [],
        'about': profile.about or profile.description,
        'screenshot_url': profile.screenshot_url,
        # legacy fields preserved
        'role': profile.role,
        'description': profile.description,
        'main_lane': profile.main_lane.value if profile.main_lane else None,
        'extra_lanes': profile.extra_lanes or [],
        'mythic_stars': profile.mythic_stars,
        'profile_image_file_id': profile.profile_image_file_id,
        'created_at': _iso(profile.created_at),
        'updated_at': _iso(profile.updated_at),
    }


def _user_to_dict(user: User | None) -> dict[str, object] | None:
    if user is None:
        return None
    return {
        'id': int(user.id),
        'username': user.username,
        'full_name': user.full_name,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'nickname': user.nickname,
        'language': user.language_code.value if user.language_code else None,
        'gender': user.gender.value if user.gender else None,
        'birth_date': user.birth_date.isoformat() if user.birth_date else None,
        'is_registered': bool(user.is_registered),
        'telegram_photo_url': user.telegram_photo_url,
        'avatar_data_url': user.avatar_data_url,
        'registered_at': _iso(user.registered_at),
    }


# ────────────────────────────────────────────────────────────────────────────
# Health
# ────────────────────────────────────────────────────────────────────────────


@app.get('/api/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


# ────────────────────────────────────────────────────────────────────────────
# WebApp authenticated endpoints — registration / nickname / me / profiles
# ────────────────────────────────────────────────────────────────────────────


@app.get('/api/me')
async def get_me(
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    user = await repo.get_by_id(auth.user_id)
    if user is None or not user.is_registered:
        # пользователь либо не существует, либо ещё не прошёл онбординг
        return {
            'user': None,
            'is_registered': False,
            'has_profiles': False,
            'telegram': {
                'id': auth.user_id,
                'username': auth.username,
                'first_name': auth.first_name,
                'last_name': auth.last_name,
                'photo_url': auth.photo_url,
            },
        }

    profile_repo = ProfileRepository(session)
    profiles_count = await profile_repo.count_by_owner(user.id)
    return {
        'user': _user_to_dict(user),
        'is_registered': True,
        'has_profiles': profiles_count > 0,
        'telegram': {
            'id': auth.user_id,
            'username': auth.username,
            'first_name': auth.first_name,
            'last_name': auth.last_name,
            'photo_url': auth.photo_url,
        },
    }


@app.get('/api/nickname/check')
async def check_nickname(
    nickname: str = Query(..., min_length=1, max_length=64),
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    nick, err = _validate_nickname(nickname)
    if err is not None:
        return {'available': False, 'reason': err}
    repo = UserRepository(session)
    taken = await repo.nickname_exists(nick, exclude_user_id=auth.user_id)
    if taken:
        return {'available': False, 'reason': 'taken'}
    return {'available': True, 'normalized': nick}


@app.post('/api/register')
async def register(
    payload: RegisterPayload,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    nick, err = _validate_nickname(payload.nickname)
    if err is not None:
        raise HTTPException(status_code=400, detail={'field': 'nickname', 'reason': err})

    # Дата рождения опциональна — если задана, валидируем 13–100 лет.
    if payload.birth_date is not None:
        today = date.today()
        age = today.year - payload.birth_date.year - (
            (today.month, today.day) < (payload.birth_date.month, payload.birth_date.day)
        )
        if payload.birth_date > today or age < 13 or age > 100:
            raise HTTPException(status_code=400, detail={'field': 'birth_date', 'reason': 'invalid'})

    repo = UserRepository(session)
    if await repo.nickname_exists(nick, exclude_user_id=auth.user_id):
        raise HTTPException(status_code=409, detail={'field': 'nickname', 'reason': 'taken'})

    user = await repo.register_webapp_user(
        user_id=auth.user_id,
        username=auth.username,
        first_name=auth.first_name,
        last_name=auth.last_name,
        photo_url=auth.photo_url,
        language=payload.language,
        gender=payload.gender,
        nickname=nick,
        birth_date=payload.birth_date,
    )
    return {
        'user': _user_to_dict(user),
        'is_registered': True,
        'has_profiles': False,
    }


@app.get('/api/me/stats')
async def my_stats(
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    payload = await UserService(session).get_profile_stats(auth.user_id)
    user = payload.get('user')
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    return {
        'profiles_count': int(payload.get('profiles_count', 0) or 0),
        'likes_count': int(payload.get('likes_count', 0) or 0),
        'followers_count': int(payload.get('followers_count', 0) or 0),
        'subscriptions_count': int(payload.get('subscriptions_count', 0) or 0),
        'friends_count': int(payload.get('friends_count', 0) or 0),
        'profile_views_count': int(payload.get('profile_views_count', 0) or 0),
        'profile_visits_count': int(payload.get('profile_visits_count', 0) or 0),
    }


@app.patch('/api/me')
async def update_me(
    payload: UpdateMePayload,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    user = _ensure_registered(await repo.get_by_id(auth.user_id))

    # Никнейм — валидируем и проверяем уникальность.
    if payload.nickname is not None and payload.nickname.strip().lower() != (user.nickname or ''):
        nick, err = _validate_nickname(payload.nickname)
        if err is not None:
            raise HTTPException(status_code=400, detail={'field': 'nickname', 'reason': err})
        if await repo.nickname_exists(nick, exclude_user_id=auth.user_id):
            raise HTTPException(status_code=409, detail={'field': 'nickname', 'reason': 'taken'})
        user.nickname = nick

    if payload.language is not None:
        user.language_code = payload.language

    if payload.gender is not None:
        user.gender = payload.gender

    if payload.birth_date is not None:
        today = date.today()
        age = today.year - payload.birth_date.year - (
            (today.month, today.day) < (payload.birth_date.month, payload.birth_date.day)
        )
        if payload.birth_date > today or age < 13 or age > 100:
            raise HTTPException(status_code=400, detail={'field': 'birth_date', 'reason': 'invalid'})
        user.birth_date = payload.birth_date

    if payload.avatar_data_url is not None:
        # пустая строка = очистить
        url = payload.avatar_data_url.strip()
        if url == '':
            user.avatar_data_url = None
        else:
            if not url.startswith('data:image/'):
                raise HTTPException(status_code=400, detail={'field': 'avatar_data_url', 'reason': 'bad_format'})
            user.avatar_data_url = url

    await session.flush()
    await session.refresh(user)
    return {'user': _user_to_dict(user)}


@app.delete('/api/me')
async def delete_me(
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    user = await UserRepository(session).get_by_id(auth.user_id)
    if user is None:
        return {'ok': True}
    await session.delete(user)
    await session.flush()
    return {'ok': True}


@app.get('/api/game-profiles/me')
async def my_game_profiles(
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    profiles = await ProfileRepository(session).list_by_owner(auth.user_id)
    return {'items': [_profile_to_dict(p) for p in profiles]}


def _ensure_registered(user: User | None) -> User:
    if user is None or not user.is_registered:
        raise HTTPException(status_code=403, detail='User is not registered')
    return user


@app.post('/api/game-profiles')
async def create_or_update_game_profile(
    payload: CreateGameProfilePayload,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    user_repo = UserRepository(session)
    user = _ensure_registered(await user_repo.get_by_id(auth.user_id))

    profile_repo = ProfileRepository(session)
    profile = await profile_repo.get_by_owner_and_game(user.id, payload.game)
    if profile is None:
        profile = await profile_repo.create_profile(user.id, payload.game)

    profile.game_nickname = payload.game_nickname
    profile.game_player_id = payload.game_id
    profile.server_id = payload.server_id
    profile.region = payload.region
    profile.rank = payload.rank
    profile.main_role = payload.main_role
    profile.role = payload.main_role  # legacy mirror
    profile.secondary_roles = payload.secondary_roles or None
    profile.looking_for = payload.looking_for or None
    profile.play_style = payload.play_style
    profile.microphone = payload.microphone
    profile.play_time_slots = payload.play_time_slots or None
    profile.about = payload.about
    profile.description = payload.about  # legacy mirror
    profile.screenshot_url = payload.screenshot_url
    profile.status = ProfileStatus.ACTIVE
    if profile.profile_image_file_id is None:
        profile.profile_image_file_id = 'webapp-placeholder'

    await session.flush()
    await session.refresh(profile)
    return {'item': _profile_to_dict(profile)}


@app.patch('/api/game-profiles/{profile_id}/status')
async def update_game_profile_status(
    profile_id: UUID,
    payload: UpdateGameProfileStatusPayload,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    repo = ProfileRepository(session)
    profile = await repo.get_owned_profile(auth.user_id, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail='Profile not found')
    profile.status = payload.status
    await session.flush()
    await session.refresh(profile)
    return {'item': _profile_to_dict(profile)}


@app.delete('/api/game-profiles/{profile_id}')
async def delete_game_profile(
    profile_id: UUID,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    ok = await ProfileService(session).delete_owned_profile(auth.user_id, profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Profile not found')
    return {'ok': True}


# ────────────────────────────────────────────────────────────────────────────
# Users search (для начала чата по нику)
# ────────────────────────────────────────────────────────────────────────────


@app.get('/api/users/search')
async def api_search_users(
    q: str = Query(..., min_length=2, max_length=64),
    limit: int = Query(20, ge=1, le=50),
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    users = await repo.search_by_query(q, exclude_user_id=auth.user_id, limit=limit)
    return {'items': [_user_to_dict(u) for u in users]}


@app.get('/api/users/{user_id}')
async def api_get_user(
    user_id: int,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_registered:
        raise HTTPException(status_code=404, detail={'reason': 'user_not_found'})

    profile_repo = ProfileRepository(session)
    profiles = await profile_repo.list_by_owner(user.id)

    age = None
    if user.birth_date:
        today = date.today()
        age = today.year - user.birth_date.year - (
            (today.month, today.day) < (user.birth_date.month, user.birth_date.day)
        )

    interactions = InteractionService(session)
    is_subscribed = await interactions.is_subscribed(auth.user_id, int(user.id))
    has_like = await interactions.has_like(auth.user_id, int(user.id), GameCode.MLBB)

    user_dict = _user_to_dict(user) or {}
    return {
        'user': {**user_dict, 'age': age},
        'profiles': [
            _profile_to_dict(p)
            for p in profiles
            if p.status is None or p.status == ProfileStatus.ACTIVE
        ],
        'is_subscribed': bool(is_subscribed),
        'has_like': bool(has_like),
        'is_self': int(user.id) == auth.user_id,
    }


# ────────────────────────────────────────────────────────────────────────────
# Search (свайп-карточки тиммейтов по выбранной игре)
# ────────────────────────────────────────────────────────────────────────────


@app.get('/api/search')
async def api_search(
    game: GameCode = Query(GameCode.MLBB),
    region: str | None = Query(default=None, max_length=32),
    rank: str | None = Query(default=None, max_length=64),
    skip_liked: bool = Query(default=True),
    limit: int = Query(default=30, ge=1, le=100),
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    profile_service = ProfileService(session)
    interactions = InteractionService(session)
    rows = await profile_service.search_profiles(auth.user_id, game)
    user_repo = UserRepository(session)

    items: list[dict[str, object]] = []
    for profile, owner in rows:
        if owner is None or not getattr(owner, 'is_registered', False):
            continue
        # active профили — анкета не на паузе/драфте
        if profile.status is not None and profile.status != ProfileStatus.ACTIVE:
            continue
        if region and (profile.region or '') != region:
            continue
        if rank and (profile.rank or '') != rank:
            continue
        liked = await interactions.has_like(auth.user_id, int(owner.id), game)
        if skip_liked and liked:
            continue
        # Аватар берём из user.avatar_data_url; если нет — None.
        owner_dict = _user_to_dict(owner) or {}
        # Возраст для UI.
        age = None
        if owner.birth_date:
            today = date.today()
            age = today.year - owner.birth_date.year - (
                (today.month, today.day) < (owner.birth_date.month, owner.birth_date.day)
            )
        items.append({
            'profile': _profile_to_dict(profile),
            'owner': {
                **owner_dict,
                'age': age,
            },
            'liked': liked,
            'subscribed': await interactions.is_subscribed(auth.user_id, int(owner.id)),
        })
        if len(items) >= limit:
            break

    return {'items': items, 'total': len(items)}


# ────────────────────────────────────────────────────────────────────────────
# Activity (auth)
# ────────────────────────────────────────────────────────────────────────────

_ACTIVITY_SECTIONS = {'subscriptions', 'subscribers', 'likes', 'liked_by', 'friends'}


@app.get('/api/activity/{section}')
async def api_activity(
    section: str,
    limit: int = Query(50, ge=1, le=200),
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    if section not in _ACTIVITY_SECTIONS:
        raise HTTPException(status_code=400, detail={'reason': 'unknown_section'})
    interactions = InteractionService(session)
    method = {
        'subscriptions': interactions.list_subscriptions,
        'subscribers': interactions.list_subscribers,
        'likes': interactions.list_my_likes,
        'liked_by': interactions.list_who_liked_me,
        'friends': interactions.list_friends,
    }[section]
    items = await method(auth.user_id, limit=limit)
    # отметить, на каких пользователей я уже подписан / кого лайкнул — для UI;
    # подтянуть актуальный nickname и аватар.
    user_repo = UserRepository(session)
    enriched = []
    for item in items:
        target_id = item.get('user_id')
        try:
            target_id = int(target_id) if target_id is not None else None
        except (TypeError, ValueError):
            target_id = None
        is_subscribed = False
        has_like = False
        nickname = item.get('nickname')
        avatar_data_url = None
        if target_id is not None:
            is_subscribed = await interactions.is_subscribed(auth.user_id, target_id)
            has_like = await interactions.has_like(auth.user_id, target_id, GameCode.MLBB)
            target = await user_repo.get_by_id(target_id)
            if target is not None:
                nickname = nickname or target.nickname or target.full_name
                avatar_data_url = target.avatar_data_url
        enriched.append({
            **item,
            'nickname': nickname,
            'avatar_data_url': avatar_data_url,
            'is_subscribed': is_subscribed,
            'has_like': has_like,
        })
    return {'items': enriched}


# ────────────────────────────────────────────────────────────────────────────
# Chats (auth)
# ────────────────────────────────────────────────────────────────────────────


@app.get('/api/chats')
async def api_list_chats(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    payload = await ChatService(session).list_user_chats_paginated(
        auth.user_id, page=page, page_size=page_size,
    )
    items = list(payload.get('items') or [])
    enriched = []
    user_repo = UserRepository(session)
    msg_service = MessageService(session)

    for item in items:
        chat_id = int(item['chat_id']) if 'chat_id' in item else None
        counterpart_id = int(item.get('counterpart_id') or 0) or None

        counterpart = None
        if counterpart_id is not None:
            counterpart = await user_repo.get_by_id(counterpart_id)

        last_message = None
        last_at = None
        last_from_me = False
        if chat_id is not None:
            msg_payload = await msg_service.list_chat_messages_paginated(
                chat_id=chat_id, user_id=auth.user_id, page=1, page_size=1,
            )
            if msg_payload:
                msgs = msg_payload.get('items') or []
                if msgs:
                    last = msgs[0]
                    last_message = last.text
                    last_at = last.created_at
                    last_from_me = int(last.from_user_id) == auth.user_id

        enriched.append({
            'chat_id': chat_id,
            'counterpart': _user_to_dict(counterpart) if counterpart else {
                'id': counterpart_id,
                'nickname': item.get('username'),
                'full_name': item.get('full_name'),
            },
            'last_message_text': last_message,
            'last_message_at': _iso(last_at),
            'last_from_me': last_from_me,
            'unread_count': int(item.get('unread_count') or 0),
        })

    return {
        'items': enriched,
        'page': int(payload.get('page', 1) or 1),
        'total_pages': int(payload.get('total_pages', 1) or 1),
        'total_items': int(payload.get('total_items', len(enriched)) or 0),
    }


@app.post('/api/chats/start')
async def api_start_chat(
    payload: ApiStartChatPayload,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    if int(payload.target_user_id) == auth.user_id:
        raise HTTPException(status_code=400, detail={'reason': 'self'})
    chat_service = ChatService(session)
    target = await UserRepository(session).get_by_id(payload.target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail={'reason': 'target_not_found'})
    chat, created = await chat_service.create_or_get_chat(auth.user_id, payload.target_user_id)
    counterpart = await chat_service.get_counterpart_user(chat, auth.user_id)
    return {
        'chat_id': int(chat.id),
        'created': bool(created),
        'counterpart': _user_to_dict(counterpart),
    }


@app.get('/api/chats/{chat_id}/messages')
async def api_chat_messages(
    chat_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    chat_service = ChatService(session)
    chat = await chat_service.get_chat_for_user(chat_id, auth.user_id)
    if chat is None:
        raise HTTPException(status_code=404, detail={'reason': 'chat_not_found'})
    counterpart = await chat_service.get_counterpart_user(chat, auth.user_id)
    payload = await MessageService(session).list_chat_messages_paginated(
        chat_id=chat_id,
        user_id=auth.user_id,
        page=page,
        page_size=page_size,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail={'reason': 'chat_not_found'})

    items = []
    for item in payload.get('items', []):
        items.append({
            'id': int(item.id),
            'from_user_id': int(item.from_user_id),
            'to_user_id': int(item.to_user_id),
            'text': item.text,
            'is_read': bool(item.is_read),
            'created_at': _iso(item.created_at),
            'mine': int(item.from_user_id) == auth.user_id,
        })
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


@app.post('/api/chats/{chat_id}/messages')
async def api_send_message(
    chat_id: int,
    payload: ApiSendMessagePayload,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    entity, error = await MessageService(session).send_message_in_chat(
        chat_id=chat_id,
        sender_id=auth.user_id,
        text=payload.text,
    )
    if entity is None:
        raise HTTPException(status_code=400, detail={'reason': error or 'message_send_failed'})
    # Закоммитим до broadcast — иначе подписчики получат ивент раньше, чем сообщение
    # станет видно в БД (читатель сразу запросит свежий список).
    await session.commit()
    try:
        await broadcast_message(int(entity.chat_id), entity)
    except Exception:
        # broadcast — best effort, ошибка не должна валить запрос.
        pass
    return {
        'id': int(entity.id),
        'chat_id': int(entity.chat_id),
        'from_user_id': int(entity.from_user_id),
        'to_user_id': int(entity.to_user_id),
        'text': entity.text,
        'created_at': _iso(entity.created_at),
        'mine': True,
    }


@app.delete('/api/chats/{chat_id}')
async def api_delete_chat(
    chat_id: int,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    ok = await ChatService(session).delete_chat(chat_id, auth.user_id)
    if not ok:
        raise HTTPException(status_code=404, detail={'reason': 'chat_not_found'})
    return {'ok': True}


# ────────────────────────────────────────────────────────────────────────────
# Interactions (auth)
# ────────────────────────────────────────────────────────────────────────────


@app.post('/api/interactions/like')
async def api_like(
    payload: ApiLikePayload,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    if int(payload.target_user_id) == auth.user_id:
        raise HTTPException(status_code=400, detail={'reason': 'self'})
    interactions = InteractionService(session)
    ok = await interactions.add_like(auth.user_id, payload.target_user_id, payload.game)
    mutual = await interactions.is_mutual_like(auth.user_id, payload.target_user_id, payload.game)
    return {'ok': bool(ok), 'mutual': bool(mutual)}


@app.post('/api/interactions/subscription/toggle')
async def api_toggle_subscription(
    payload: ApiSubscribePayload,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    if int(payload.target_user_id) == auth.user_id:
        raise HTTPException(status_code=400, detail={'reason': 'self'})
    subscribed = await InteractionService(session).toggle_subscription(
        auth.user_id, payload.target_user_id,
    )
    return {'subscribed': bool(subscribed)}


@app.post('/api/interactions/message')
async def api_direct_message(
    payload: ApiDirectMessagePayload,
    auth: TelegramAuth = Depends(get_telegram_auth),
    session: AsyncSession = Depends(get_session),
):
    if int(payload.target_user_id) == auth.user_id:
        raise HTTPException(status_code=400, detail={'reason': 'self'})
    try:
        entity = await InteractionService(session).create_message(
            auth.user_id, payload.target_user_id, payload.text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={'reason': str(exc)}) from exc
    return {'id': int(entity.id), 'chat_id': int(entity.chat_id)}


