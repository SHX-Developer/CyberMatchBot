MODERATION_REVIEW_CHAT_ID = -5122358580

MODERATOR_USER_IDS = {
    284929331,
    1340041796,
    622781320,
    8392395155,
}

ACTION_LOG_GROUP_PEER_ID = 5056732401
ACTION_LOG_CHAT_ID = int(f'-100{ACTION_LOG_GROUP_PEER_ID}')


def is_moderator(user_id: int | None) -> bool:
    return isinstance(user_id, int) and user_id in MODERATOR_USER_IDS
