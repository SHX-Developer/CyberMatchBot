from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.constants import (
    CB_ADMIN_PANEL_BACK,
    CB_ADMIN_PANEL_HIDE,
    CB_ADMIN_PANEL_REFRESH,
    CB_ADMIN_PANEL_STATS,
)
from app.database import LanguageCode
from app.keyboards import admin_panel_keyboard, admin_stats_keyboard
from app.models import PlayerProfile, User, UserLike, UserSubscription

router = Router(name='admin_panel')

ADMIN_USER_IDS = {
    284929331,
    1340041796,
    622781320,
}


def _is_admin(user_id: int | None) -> bool:
    return isinstance(user_id, int) and user_id in ADMIN_USER_IDS


def _bar(value: int, max_value: int, *, width: int = 14) -> str:
    if max_value <= 0:
        return '░' * width
    filled = int(round((value / max_value) * width))
    if value > 0 and filled == 0:
        filled = 1
    if filled > width:
        filled = width
    return ('█' * filled) + ('░' * (width - filled))


def _render_chart(rows: list[tuple[str, int]]) -> str:
    max_value = max((value for _, value in rows), default=0)
    return '\n'.join(
        f'{title:<16} {_bar(value, max_value)} {value}'
        for title, value in rows
    )


async def _collect_admin_stats(session: AsyncSession) -> dict[str, int]:
    users_total = int((await session.scalar(select(func.count(User.id)))) or 0)
    profiles_total = int((await session.scalar(select(func.count(PlayerProfile.id)))) or 0)
    likes_total = int((await session.scalar(select(func.count(UserLike.id)))) or 0)
    subscriptions_total = int((await session.scalar(select(func.count(UserSubscription.id)))) or 0)
    subscribers_total = int(
        (
            await session.scalar(
                select(func.count(func.distinct(UserSubscription.followed_user_id)))
            )
        )
        or 0
    )

    reciprocal_sub = aliased(UserSubscription)
    friends_total = int(
        (
            await session.scalar(
                select(func.count())
                .select_from(UserSubscription)
                .where(UserSubscription.follower_user_id < UserSubscription.followed_user_id)
                .where(
                    exists(
                        select(1).where(
                            and_(
                                reciprocal_sub.follower_user_id == UserSubscription.followed_user_id,
                                reciprocal_sub.followed_user_id == UserSubscription.follower_user_id,
                            )
                        )
                    )
                )
            )
        )
        or 0
    )

    reciprocal_like = aliased(UserLike)
    mutual_likes_total = int(
        (
            await session.scalar(
                select(func.count())
                .select_from(UserLike)
                .where(UserLike.from_user_id < UserLike.to_user_id)
                .where(
                    exists(
                        select(1).where(
                            and_(
                                reciprocal_like.from_user_id == UserLike.to_user_id,
                                reciprocal_like.to_user_id == UserLike.from_user_id,
                                reciprocal_like.game == UserLike.game,
                            )
                        )
                    )
                )
            )
        )
        or 0
    )

    languages = {'ru': 0, 'en': 0, 'uz': 0, 'none': 0}
    language_rows = (
        await session.execute(
            select(User.language_code, func.count(User.id))
            .group_by(User.language_code)
        )
    ).all()
    for language_code, total in language_rows:
        count_value = int(total or 0)
        if language_code is None:
            languages['none'] += count_value
            continue
        raw_code = language_code.value if isinstance(language_code, LanguageCode) else str(language_code)
        if raw_code in languages:
            languages[raw_code] += count_value
        else:
            languages['none'] += count_value

    return {
        'users_total': users_total,
        'profiles_total': profiles_total,
        'likes_total': likes_total,
        'subscriptions_total': subscriptions_total,
        'subscribers_total': subscribers_total,
        'friends_total': friends_total,
        'mutual_likes_total': mutual_likes_total,
        'lang_ru': languages['ru'],
        'lang_en': languages['en'],
        'lang_uz': languages['uz'],
        'lang_none': languages['none'],
    }


async def _stats_text(session: AsyncSession) -> str:
    stats = await _collect_admin_stats(session)

    metrics_chart = _render_chart(
        [
            ('Пользователи', stats['users_total']),
            ('Анкеты', stats['profiles_total']),
            ('Лайки', stats['likes_total']),
            ('Подписки', stats['subscriptions_total']),
            ('Подписчики', stats['subscribers_total']),
            ('Друзья', stats['friends_total']),
            ('Взаимные лайки', stats['mutual_likes_total']),
        ]
    )
    languages_chart = _render_chart(
        [
            ('RU', stats['lang_ru']),
            ('EN', stats['lang_en']),
            ('UZ', stats['lang_uz']),
            ('Без языка', stats['lang_none']),
        ]
    )

    return (
        '📊 <b>Статистика бота</b>\n\n'
        f"👥 <b>Пользователи:</b> {stats['users_total']}\n"
        f"🌐 <b>Языки:</b> RU {stats['lang_ru']} | EN {stats['lang_en']} | UZ {stats['lang_uz']} | Без языка {stats['lang_none']}\n"
        f"🎮 <b>Количество анкет:</b> {stats['profiles_total']}\n"
        f"❤️ <b>Общие лайки:</b> {stats['likes_total']}\n"
        f"⭐ <b>Подписки:</b> {stats['subscriptions_total']}\n"
        f"👤 <b>Подписчики:</b> {stats['subscribers_total']}\n"
        f"🤝 <b>Друзья:</b> {stats['friends_total']}\n"
        f"💞 <b>Взаимные лайки:</b> {stats['mutual_likes_total']}\n\n"
        '<b>📈 Диаграмма метрик</b>\n'
        f'<pre>{escape(metrics_chart)}</pre>\n'
        '<b>🌍 Диаграмма языков</b>\n'
        f'<pre>{escape(languages_chart)}</pre>'
    )


def _panel_text() -> str:
    return (
        '🛠 <b>Админ-панель</b>\n\n'
        'Нажмите кнопку ниже, чтобы открыть статистику бота.'
    )


@router.message(Command('admin'))
async def admin_panel_open(message: Message) -> None:
    if message.from_user is None:
        return
    if not _is_admin(message.from_user.id):
        await message.answer('⛔ Нет доступа к админ-панели.')
        return

    await message.answer(
        _panel_text(),
        parse_mode='HTML',
        reply_markup=admin_panel_keyboard(),
    )


async def _edit_panel_message(callback: CallbackQuery, *, text: str, stats_mode: bool) -> None:
    if not isinstance(callback.message, Message):
        return
    keyboard = admin_stats_keyboard() if stats_mode else admin_panel_keyboard()
    try:
        await callback.message.edit_text(
            text=text,
            parse_mode='HTML',
            reply_markup=keyboard,
        )
    except TelegramBadRequest as exc:
        if 'message is not modified' not in str(exc):
            raise


@router.callback_query(F.data == CB_ADMIN_PANEL_STATS)
async def admin_stats_open(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer('Нет доступа', show_alert=True)
        return
    await callback.answer()
    await _edit_panel_message(callback, text=await _stats_text(session), stats_mode=True)


@router.callback_query(F.data == CB_ADMIN_PANEL_REFRESH)
async def admin_stats_refresh(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer('Нет доступа', show_alert=True)
        return
    await _edit_panel_message(callback, text=await _stats_text(session), stats_mode=True)
    await callback.answer('Статистика обновлена')


@router.callback_query(F.data == CB_ADMIN_PANEL_BACK)
async def admin_panel_back(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer('Нет доступа', show_alert=True)
        return
    await callback.answer()
    await _edit_panel_message(callback, text=_panel_text(), stats_mode=False)


@router.callback_query(F.data == CB_ADMIN_PANEL_HIDE)
async def admin_panel_hide(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer('Нет доступа', show_alert=True)
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
