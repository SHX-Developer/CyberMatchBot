from functools import lru_cache
import os

from dotenv import dotenv_values


class Settings:
    def __init__(self, bot_token: str, database_url: str, log_level: str = 'INFO') -> None:
        self.bot_token = bot_token
        self.database_url = database_url
        self.log_level = log_level


def _require(name: str, env_data: dict[str, str]) -> str:
    value = os.getenv(name) or env_data.get(name)
    if not value:
        raise ValueError(f'Missing required environment variable: {name}')
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env_data = dotenv_values('.env')
    bot_token = _require('BOT_TOKEN', env_data)
    database_url = _require('DATABASE_URL', env_data)
    log_level = (os.getenv('LOG_LEVEL') or env_data.get('LOG_LEVEL') or 'INFO').upper()
    return Settings(bot_token=bot_token, database_url=database_url, log_level=log_level)
