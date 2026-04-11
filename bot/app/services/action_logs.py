from html import escape

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.moderation import ACTION_LOG_CHAT_ID, moderation_chat_target_ids
from app.database import GameCode
from app.services.users import UserService


def _game_title(game: GameCode) -> str:
    if game == GameCode.MLBB:
        return 'Mobile Legends'
    if game == GameCode.GENSHIN_IMPACT:
        return 'Genshin Impact'
    if game == GameCode.PUBG_MOBILE:
        return 'PUBG Mobile'
    return 'Неизвестная игра'


def _nickname(user) -> str:
    if user is None:
        return 'Не указан'
    full_name = getattr(user, 'full_name', None)
    if isinstance(full_name, str) and full_name.strip():
        return full_name.strip()
    first_name = getattr(user, 'first_name', None)
    last_name = getattr(user, 'last_name', None)
    parts = [part.strip() for part in (first_name, last_name) if isinstance(part, str) and part.strip()]
    if parts:
        return ' '.join(parts)
    return 'Не указан'


def _username(user) -> str:
    if user is None:
        return 'Не указан'
    value = getattr(user, 'username', None)
    if isinstance(value, str) and value.strip():
        return f"@{value.strip()}"
    return 'Не указан'


def _person_block(title: str, *, user_id: int, user) -> str:
    return (
        f"<b>{title}</b>\n"
        f"🏷 Ник: <code>{escape(_nickname(user))}</code>\n"
        f"🔗 Username: {escape(_username(user))}\n"
        f"🆔 ID: <code>{user_id}</code>"
    )


async def _send_log_to_chat(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML',
        )
    except Exception:
        pass


async def _send_log(bot: Bot, text: str) -> None:
    await _send_log_to_chat(bot, ACTION_LOG_CHAT_ID, text)


async def log_registration_action(*, bot: Bot, session: AsyncSession, user_id: int) -> None:
    users = UserService(session)
    user = await users.get_user(user_id)
    text = (
        "🆕 <b>Регистрация пользователя</b>\n\n"
        f"{_person_block('Кто зарегистрировался', user_id=user_id, user=user)}"
    )
    await _send_log(bot, text)
    for chat_id in moderation_chat_target_ids():
        await _send_log_to_chat(bot, chat_id, text)


async def log_like_action(
    *,
    bot: Bot,
    session: AsyncSession,
    from_user_id: int,
    to_user_id: int,
    game: GameCode,
) -> None:
    users = UserService(session)
    from_user = await users.get_user(from_user_id)
    to_user = await users.get_user(to_user_id)
    await _send_log(
        bot,
        (
            "❤️ <b>Лайк</b>\n\n"
            f"🎮 Игра: <b>{escape(_game_title(game))}</b>\n\n"
            f"{_person_block('Кто лайкнул', user_id=from_user_id, user=from_user)}\n\n"
            f"{_person_block('Кого лайкнули', user_id=to_user_id, user=to_user)}"
        ),
    )


async def log_subscription_action(
    *,
    bot: Bot,
    session: AsyncSession,
    follower_user_id: int,
    followed_user_id: int,
    subscribed_now: bool,
) -> None:
    users = UserService(session)
    follower = await users.get_user(follower_user_id)
    followed = await users.get_user(followed_user_id)
    action_title = '⭐ <b>Подписка</b>' if subscribed_now else '❎ <b>Отписка</b>'
    await _send_log(
        bot,
        (
            f"{action_title}\n\n"
            f"{_person_block('Кто сделал действие', user_id=follower_user_id, user=follower)}\n\n"
            f"{_person_block('Кого это касается', user_id=followed_user_id, user=followed)}"
        ),
    )


async def log_message_action(
    *,
    bot: Bot,
    session: AsyncSession,
    from_user_id: int,
    to_user_id: int,
    text: str,
) -> None:
    users = UserService(session)
    from_user = await users.get_user(from_user_id)
    to_user = await users.get_user(to_user_id)
    await _send_log(
        bot,
        (
            "💬 <b>Сообщение</b>\n\n"
            f"{_person_block('Кто написал', user_id=from_user_id, user=from_user)}\n\n"
            f"{_person_block('Кому написал', user_id=to_user_id, user=to_user)}\n\n"
            f"📝 Текст:\n<code>{escape(text.strip())}</code>"
        ),
    )


async def log_mutual_like_action(
    *,
    bot: Bot,
    session: AsyncSession,
    user_a_id: int,
    user_b_id: int,
    game: GameCode,
) -> None:
    users = UserService(session)
    user_a = await users.get_user(user_a_id)
    user_b = await users.get_user(user_b_id)
    await _send_log(
        bot,
        (
            "💞 <b>Взаимный лайк</b>\n\n"
            f"🎮 Игра: <b>{escape(_game_title(game))}</b>\n\n"
            f"{_person_block('Пользователь 1', user_id=user_a_id, user=user_a)}\n\n"
            f"{_person_block('Пользователь 2', user_id=user_b_id, user=user_b)}"
        ),
    )
