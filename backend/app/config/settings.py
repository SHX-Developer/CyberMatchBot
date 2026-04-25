from functools import lru_cache
import os

from dotenv import dotenv_values


class Settings:
    def __init__(
        self,
        bot_token: str,
        database_url: str,
        log_level: str = 'INFO',
        webapp_auth_required: bool = True,
        webapp_dev_user_id: int | None = None,
        webapp_init_data_max_age: int = 24 * 60 * 60,
        webapp_url: str | None = None,
    ) -> None:
        self.bot_token = bot_token
        self.database_url = database_url
        self.log_level = log_level
        self.webapp_auth_required = webapp_auth_required
        self.webapp_dev_user_id = webapp_dev_user_id
        self.webapp_init_data_max_age = webapp_init_data_max_age
        self.webapp_url = webapp_url


def _require(name: str, env_data: dict[str, str]) -> str:
    value = os.getenv(name) or env_data.get(name)
    if not value:
        raise ValueError(f'Missing required environment variable: {name}')
    return value


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _int_or_none(value: str | None) -> int | None:
    if value is None or not str(value).strip():
        return None
    try:
        return int(value)
    except ValueError:
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env_data = dotenv_values('.env')
    bot_token = _require('BOT_TOKEN', env_data)
    database_url = _require('DATABASE_URL', env_data)
    log_level = (os.getenv('LOG_LEVEL') or env_data.get('LOG_LEVEL') or 'INFO').upper()
    webapp_auth_required = _bool(
        os.getenv('WEBAPP_AUTH_REQUIRED') or env_data.get('WEBAPP_AUTH_REQUIRED'),
        default=True,
    )
    webapp_dev_user_id = _int_or_none(
        os.getenv('WEBAPP_DEV_USER_ID') or env_data.get('WEBAPP_DEV_USER_ID'),
    )
    webapp_url_raw = os.getenv('WEBAPP_URL') or env_data.get('WEBAPP_URL') or ''
    webapp_url = webapp_url_raw.strip() or None
    return Settings(
        bot_token=bot_token,
        database_url=database_url,
        log_level=log_level,
        webapp_auth_required=webapp_auth_required,
        webapp_dev_user_id=webapp_dev_user_id,
        webapp_url=webapp_url,
    )
