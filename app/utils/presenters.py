from html import escape

from app.database import GameCode, MlbbLaneCode
from app.locales import LocalizationManager
from app.models import PlayerProfile
from app.utils.dates import format_datetime
from app.utils.game import game_label, lane_label


def parse_mlbb_lanes(raw_lanes: list[str] | None) -> list[MlbbLaneCode]:
    if not raw_lanes:
        return []

    parsed: list[MlbbLaneCode] = []
    for value in raw_lanes:
        try:
            parsed.append(MlbbLaneCode(value))
        except ValueError:
            continue
    return parsed


def format_profiles_status(
    i18n: LocalizationManager,
    locale: str,
    profiles_by_game: dict[GameCode, PlayerProfile],
) -> str:
    lines = [
        i18n.t(locale, 'profiles.status.title'),
        '',
        i18n.t(locale, 'profiles.status.subtitle'),
        '',
    ]

    for game in GameCode:
        if game in profiles_by_game:
            lines.append(
                i18n.t(
                    locale,
                    'profiles.status.line.created',
                    game=game_label(i18n, locale, game),
                )
            )
        else:
            lines.append(
                i18n.t(
                    locale,
                    'profiles.status.line.missing',
                    game=game_label(i18n, locale, game),
                )
            )

    return '\n'.join(lines)


def format_generic_profile_card(i18n: LocalizationManager, locale: str, profile: PlayerProfile) -> str:
    return i18n.t(
        locale,
        'profiles.card.generic',
        game=game_label(i18n, locale, profile.game),
        created_at=format_datetime(profile.created_at, locale),
        updated_at=format_datetime(profile.updated_at, locale),
    )


def format_mlbb_profile_card(
    i18n: LocalizationManager,
    locale: str,
    profile: PlayerProfile,
    *,
    title_key: str,
    player_name: str | None = None,
) -> str:
    main_lane = lane_label(i18n, locale, profile.main_lane) if profile.main_lane else i18n.t(locale, 'value.not_set')

    extra_lanes_values = parse_mlbb_lanes(profile.extra_lanes)
    if extra_lanes_values:
        extra_lanes = ', '.join(lane_label(i18n, locale, lane) for lane in extra_lanes_values)
    else:
        extra_lanes = i18n.t(locale, 'value.not_set')

    description = profile.description or i18n.t(locale, 'value.not_set')
    game_player_id = profile.game_player_id or i18n.t(locale, 'value.not_set')

    return i18n.t(
        locale,
        title_key,
        game=game_label(i18n, locale, GameCode.MLBB),
        player_name=player_name or i18n.t(locale, 'value.not_set'),
        game_player_id=escape(game_player_id),
        main_lane=main_lane,
        extra_lanes=extra_lanes,
        description=escape(description),
        updated_at=format_datetime(profile.updated_at, locale),
    )
