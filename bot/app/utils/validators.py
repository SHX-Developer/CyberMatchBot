import re

MLBB_ID_PATTERN = re.compile(r'^\d{8,20}$')
DESCRIPTION_MIN_LENGTH = 10
DESCRIPTION_MAX_LENGTH = 500


def is_valid_mlbb_player_id(value: str) -> bool:
    return bool(MLBB_ID_PATTERN.fullmatch(value.strip()))


def is_valid_profile_description(value: str) -> bool:
    length = len(value.strip())
    return DESCRIPTION_MIN_LENGTH <= length <= DESCRIPTION_MAX_LENGTH
