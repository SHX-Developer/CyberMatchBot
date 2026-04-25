"""WebSocket-эндпоинт для чата: реалтайм-сообщения, typing и presence.

Подключение:
    /ws/chat/{chat_id}?init_data=<TG webapp initData>
    /ws/chat/{chat_id}?dev_user_id=<id>   — только при WEBAPP_AUTH_REQUIRED=false

Сервер шлёт клиенту JSON-ивенты:
    {"type": "presence", "user_id": 123, "online": true}
    {"type": "typing",   "user_id": 123}
    {"type": "message",  "message": {...}}    # см. _serialize_message
    {"type": "read",     "user_id": 123, "up_to_id": 456}

Клиент шлёт серверу:
    {"type": "typing"}     — пинг при наборе текста (рейт-лимитим на стороне фронта)
    {"type": "ping"}       — keepalive (опционально)

Аутентификация переиспользует TelegramAuth из app.web.auth.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories import UserRepository
from app.services import ChatService
from app.web.auth import TelegramAuth, _verify_init_data


logger = logging.getLogger(__name__)


router = APIRouter()


@dataclass
class _Connection:
    websocket: WebSocket
    user_id: int


@dataclass
class _ChatRoom:
    connections: set[_Connection] = field(default_factory=set)


class ChatHub:
    """In-memory роутер событий по чатам.

    Не масштабируется на несколько процессов — для horizontal scaling нужен
    Redis pub/sub, но для текущего одно-инстансного деплоя этого достаточно.
    """

    def __init__(self) -> None:
        self._rooms: dict[int, _ChatRoom] = defaultdict(_ChatRoom)
        self._lock = asyncio.Lock()

    async def join(self, chat_id: int, conn: _Connection) -> None:
        async with self._lock:
            self._rooms[chat_id].connections.add(conn)

    async def leave(self, chat_id: int, conn: _Connection) -> None:
        async with self._lock:
            room = self._rooms.get(chat_id)
            if room is None:
                return
            room.connections.discard(conn)
            if not room.connections:
                self._rooms.pop(chat_id, None)

    def online_user_ids(self, chat_id: int) -> set[int]:
        room = self._rooms.get(chat_id)
        if room is None:
            return set()
        return {c.user_id for c in room.connections}

    async def broadcast(self, chat_id: int, payload: dict[str, Any], *, exclude_user_id: int | None = None) -> None:
        room = self._rooms.get(chat_id)
        if room is None:
            return
        # Снимем снапшот, чтобы не держать lock пока шлём.
        targets = list(room.connections)
        text = json.dumps(payload, ensure_ascii=False)
        dead: list[_Connection] = []
        for conn in targets:
            if exclude_user_id is not None and conn.user_id == exclude_user_id:
                continue
            try:
                await conn.websocket.send_text(text)
            except Exception as exc:  # noqa: BLE001
                logger.debug('WS send failed for chat=%s user=%s: %s', chat_id, conn.user_id, exc)
                dead.append(conn)
        for conn in dead:
            await self.leave(chat_id, conn)


hub = ChatHub()


def _serialize_message(entity, viewer_id: int) -> dict[str, Any]:
    return {
        'id': int(entity.id),
        'chat_id': int(entity.chat_id),
        'from_user_id': int(entity.from_user_id),
        'to_user_id': int(entity.to_user_id),
        'text': entity.text,
        'created_at': entity.created_at.isoformat() if getattr(entity, 'created_at', None) else None,
        'mine': int(entity.from_user_id) == viewer_id,
    }


async def broadcast_message(chat_id: int, message_entity) -> None:
    """Вызывается из HTTP-эндпоинта POST /api/chats/{id}/messages.

    Шлём событие всем подключенным к комнате (включая отправителя — фронт
    использует id для дедупликации с оптимистичным append).
    """
    payload = {
        'type': 'message',
        'message': {
            'id': int(message_entity.id),
            'chat_id': int(message_entity.chat_id),
            'from_user_id': int(message_entity.from_user_id),
            'to_user_id': int(message_entity.to_user_id),
            'text': message_entity.text,
            'created_at': message_entity.created_at.isoformat() if getattr(message_entity, 'created_at', None) else None,
        },
    }
    await hub.broadcast(chat_id, payload)


async def _authenticate_ws(websocket: WebSocket) -> TelegramAuth | None:
    settings = get_settings()
    init_data = websocket.query_params.get('init_data')
    dev_user_id = websocket.query_params.get('dev_user_id')

    if init_data:
        try:
            user_dict = _verify_init_data(
                init_data,
                settings.bot_token,
                settings.webapp_init_data_max_age,
            )
            return TelegramAuth.from_user_dict(user_dict)
        except Exception as exc:  # noqa: BLE001
            logger.info('WS auth via initData failed: %s', exc)

    if not settings.webapp_auth_required:
        candidate = dev_user_id or (
            str(settings.webapp_dev_user_id) if settings.webapp_dev_user_id else None
        )
        if candidate:
            try:
                return TelegramAuth(user_id=int(candidate))
            except ValueError:
                return None
    return None


def _session_factory_from_app(websocket: WebSocket):
    return websocket.app.state.session_factory


@router.websocket('/ws/chat/{chat_id}')
async def chat_socket(websocket: WebSocket, chat_id: int):
    auth = await _authenticate_ws(websocket)
    if auth is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Проверим, что пользователь — участник чата.
    session_factory = _session_factory_from_app(websocket)
    async with session_factory() as session:  # type: AsyncSession
        chat = await ChatService(session).get_chat_for_user(chat_id, auth.user_id)
        if chat is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket.accept()
    conn = _Connection(websocket=websocket, user_id=auth.user_id)
    await hub.join(chat_id, conn)

    # Сообщим этому клиенту, кто из участников сейчас онлайн (включая его самого),
    # и оповестим остальных, что мы зашли.
    online_now = hub.online_user_ids(chat_id)
    try:
        await websocket.send_text(json.dumps({
            'type': 'presence_state',
            'online_user_ids': sorted(online_now),
        }))
    except Exception:
        pass

    await hub.broadcast(
        chat_id,
        {'type': 'presence', 'user_id': auth.user_id, 'online': True},
        exclude_user_id=auth.user_id,
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mtype = msg.get('type')
            if mtype == 'typing':
                await hub.broadcast(
                    chat_id,
                    {'type': 'typing', 'user_id': auth.user_id},
                    exclude_user_id=auth.user_id,
                )
            elif mtype == 'ping':
                try:
                    await websocket.send_text(json.dumps({'type': 'pong'}))
                except Exception:
                    break
            else:
                # Игнорируем неизвестные типы — клиент может слать read-receipts позже.
                continue
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.debug('WS error chat=%s user=%s: %s', chat_id, auth.user_id, exc)
    finally:
        await hub.leave(chat_id, conn)
        await hub.broadcast(
            chat_id,
            {'type': 'presence', 'user_id': auth.user_id, 'online': False},
            exclude_user_id=auth.user_id,
        )
