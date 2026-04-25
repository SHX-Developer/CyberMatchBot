"""Telegram WebApp initData validation + FastAPI dependency."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, status

from app.config import get_settings


@dataclass
class TelegramAuth:
    user_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    language_code: str | None = None
    raw_user: dict | None = None

    @classmethod
    def from_user_dict(cls, data: dict) -> 'TelegramAuth':
        return cls(
            user_id=int(data['id']),
            username=data.get('username'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            photo_url=data.get('photo_url'),
            language_code=data.get('language_code'),
            raw_user=data,
        )


def _verify_init_data(init_data: str, bot_token: str, max_age_seconds: int) -> dict:
    """Возвращает dict с user-полями или бросает HTTPException."""
    if not init_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing initData')

    pairs = list(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    if not pairs:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid initData')

    data = dict(pairs)
    received_hash = data.pop('hash', None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing hash')

    auth_date = data.get('auth_date')
    if auth_date:
        try:
            auth_ts = int(auth_date)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Bad auth_date')
        if max_age_seconds > 0 and (time.time() - auth_ts) > max_age_seconds:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='initData expired')

    data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
    secret_key = hmac.new(b'WebAppData', bot_token.encode('utf-8'), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid initData signature')

    user_raw = data.get('user')
    if not user_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='No user in initData')

    try:
        user_dict = json.loads(user_raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Bad user payload')

    return user_dict


def get_telegram_auth(
    x_telegram_init_data: Optional[str] = Header(default=None, alias='X-Telegram-Init-Data'),
    x_dev_user_id: Optional[str] = Header(default=None, alias='X-Dev-User-Id'),
) -> TelegramAuth:
    settings = get_settings()

    # Dev bypass: при WEBAPP_AUTH_REQUIRED=false доверяем заголовку X-Dev-User-Id или WEBAPP_DEV_USER_ID.
    if not settings.webapp_auth_required:
        dev_id_raw = x_dev_user_id or (str(settings.webapp_dev_user_id) if settings.webapp_dev_user_id else None)
        if dev_id_raw:
            try:
                return TelegramAuth(user_id=int(dev_id_raw))
            except ValueError:
                pass
        # пустой initData в dev — нельзя продолжать
        if x_telegram_init_data:
            try:
                user_dict = _verify_init_data(
                    x_telegram_init_data,
                    settings.bot_token,
                    settings.webapp_init_data_max_age,
                )
                return TelegramAuth.from_user_dict(user_dict)
            except HTTPException:
                pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Provide X-Dev-User-Id header or set WEBAPP_DEV_USER_ID',
        )

    user_dict = _verify_init_data(
        x_telegram_init_data or '',
        settings.bot_token,
        settings.webapp_init_data_max_age,
    )
    return TelegramAuth.from_user_dict(user_dict)
