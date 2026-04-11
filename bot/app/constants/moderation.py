MODERATION_REVIEW_CHAT_ID = -3987748527

MODERATOR_USER_IDS = {
    284929331,
    1340041796,
    622781320,
    8392395155,
}

ACTION_LOG_CHAT_ID = -5056732401


def is_moderator(user_id: int | None) -> bool:
    return isinstance(user_id, int) and user_id in MODERATOR_USER_IDS


def _chat_id_variants(raw_chat_id: int) -> set[int]:
    variants = {int(raw_chat_id)}
    abs_value = str(abs(int(raw_chat_id)))
    if abs_value.startswith('100') and len(abs_value) > 3:
        variants.add(-int(abs_value[3:]))
    else:
        variants.add(-int(f'100{abs_value}'))
    return variants


def is_moderation_chat(chat_id: int | None) -> bool:
    if not isinstance(chat_id, int):
        return False
    return chat_id in _chat_id_variants(MODERATION_REVIEW_CHAT_ID)


def moderation_chat_target_ids() -> tuple[int, ...]:
    return tuple(sorted(_chat_id_variants(MODERATION_REVIEW_CHAT_ID)))
