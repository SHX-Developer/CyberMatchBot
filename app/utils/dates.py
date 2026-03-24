from datetime import datetime
from zoneinfo import ZoneInfo


def format_datetime(dt: datetime, locale: str, timezone: str = 'UTC') -> str:
    tz = ZoneInfo(timezone)
    local_dt = dt.astimezone(tz)

    if locale == 'en':
        return local_dt.strftime('%Y-%m-%d %H:%M')
    return local_dt.strftime('%d.%m.%Y %H:%M')
