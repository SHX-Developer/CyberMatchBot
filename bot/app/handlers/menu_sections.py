import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    ACTIVITY_FRIENDS_IMAGE_FILE_ID,
    ACTIVITY_IMAGE_FILE_ID,
    ACTIVITY_LIKED_BY_IMAGE_FILE_ID,
    ACTIVITY_LIKES_IMAGE_FILE_ID,
    ACTIVITY_SUBSCRIBERS_IMAGE_FILE_ID,
    ACTIVITY_SUBSCRIPTIONS_IMAGE_FILE_ID,
    MAIN_MENU_IMAGE_FILE_ID,
    BTN_BACK,
    BTN_CREATE_PROFILE,
    CB_ACTIVITY_BACK,
    CB_ACTIVITY_OPEN,
    CB_ACTIVITY_PAGE_PREFIX,
    CB_ACTIVITY_SECTION_PREFIX,
)
from app.handlers.context import ensure_user_and_locale, main_menu_keyboard_with_counters, unread_activity_counters
from app.keyboards import (
    activity_open_keyboard,
    activity_section_keyboard,
    back_keyboard,
    language_keyboard,
)
from app.locales import LocalizationManager
from app.services import InteractionService, UserService

router = Router(name='menu_sections')

ACTIVITY_SECTIONS = {'subscriptions', 'subscribers', 'likes', 'liked_by', 'friends'}
ACTIVITY_PAGE_SIZE = 10
ACTIVITY_BUTTON_BASES = ('активность', 'activity', 'faollik')


def _is_activity_menu_button(text: str | None) -> bool:
    if not isinstance(text, str):
        return False
    normalized = text.strip()
    normalized = re.sub(r'\s*\(\d+\)\s*$', '', normalized)
    normalized = re.sub(r'^[^\wа-яА-Я]+', '', normalized).strip().lower()
    return normalized in ACTIVITY_BUTTON_BASES


async def _require_locale(message: Message, session: AsyncSession, i18n: LocalizationManager) -> tuple[int, str] | None:
    if message.from_user is None:
        return None

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return None

    return user_id, locale


async def _show_main_menu(
    message: Message,
    *,
    user_id: int,
    locale: str,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    await message.answer_photo(
        photo=MAIN_MENU_IMAGE_FILE_ID,
        caption=i18n.t(locale, 'start.welcome'),
        parse_mode='HTML',
        reply_markup=await main_menu_keyboard_with_counters(
            user_id=user_id,
            locale=locale,
            session=session,
            i18n=i18n,
        ),
    )


def _format_activity_list(items: list[dict[str, int | str | None]], locale: str, i18n: LocalizationManager) -> str:
    if not items:
        return i18n.t(locale, 'activity.list.empty')

    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        user_id = item.get('user_id')
        nickname = item.get('full_name')
        if isinstance(nickname, str) and nickname.strip():
            display_name = nickname.strip()
        elif isinstance(user_id, int):
            display_name = i18n.t(locale, 'activity.user.fallback', user_id=user_id)
        else:
            display_name = i18n.t(locale, 'activity.user.fallback', user_id=0)
        lines.append(f'{index}. {display_name}')
    return '\n'.join(lines)


def _paginate_items(items: list[dict[str, int | str | None]], page: int) -> tuple[list[dict[str, int | str | None]], int, int]:
    total = len(items)
    total_pages = max(1, (total + ACTIVITY_PAGE_SIZE - 1) // ACTIVITY_PAGE_SIZE)
    page_safe = max(1, min(page, total_pages))
    start = (page_safe - 1) * ACTIVITY_PAGE_SIZE
    end = start + ACTIVITY_PAGE_SIZE
    return items[start:end], page_safe, total_pages


def _parse_section_and_page(data: str) -> tuple[str, int] | None:
    payload = ''
    if data.startswith(CB_ACTIVITY_SECTION_PREFIX):
        payload = data.replace(CB_ACTIVITY_SECTION_PREFIX, '', 1)
    elif data.startswith(CB_ACTIVITY_PAGE_PREFIX):
        payload = data.replace(CB_ACTIVITY_PAGE_PREFIX, '', 1)
    elif data.startswith('activity:refresh:'):
        payload = data.replace('activity:refresh:', '', 1)
    else:
        return None

    if ':' in payload:
        section, page_raw = payload.split(':', 1)
    else:
        section, page_raw = payload, '1'

    try:
        page = int(page_raw)
    except ValueError:
        page = 1
    if page < 1:
        page = 1
    return section, page


def _activity_caption(
    *,
    title: str,
    page_items: list[dict[str, int | str | None]],
    page: int,
    total_pages: int,
    locale: str,
    i18n: LocalizationManager,
) -> str:
    list_text = _format_activity_list(page_items, locale, i18n)
    if page_items:
        list_text = f"{list_text}\n\n{i18n.t(locale, 'activity.list.page', page=page, total_pages=total_pages)}"
    return i18n.t(
        locale,
        'activity.section.card',
        title=title,
        list_text=list_text,
    )


def _normalize_activity_items(items: list[dict[str, int | str | None]], locale: str, i18n: LocalizationManager) -> list[dict[str, int | str | None]]:
    normalized: list[dict[str, int | str | None]] = []
    for item in items:
        user_id = item.get('user_id')
        if not isinstance(user_id, int):
            continue
        nickname = item.get('full_name')
        if not (isinstance(nickname, str) and nickname.strip()):
            nickname = i18n.t(locale, 'activity.user.fallback', user_id=user_id)
        normalized.append(
            {
                'user_id': user_id,
                'full_name': nickname,
            }
        )
    return normalized


async def _section_payload(
    *,
    section: str,
    interactions: InteractionService,
    user_id: int,
) -> tuple[str, str, list[dict[str, int | str | None]]]:
    if section == 'subscriptions':
        return 'activity.section.subscriptions.title', ACTIVITY_SUBSCRIPTIONS_IMAGE_FILE_ID, await interactions.list_subscriptions(user_id, limit=500)
    if section == 'subscribers':
        return 'activity.section.subscribers.title', ACTIVITY_SUBSCRIBERS_IMAGE_FILE_ID, await interactions.list_subscribers(user_id, limit=500)
    if section == 'likes':
        return 'activity.section.likes.title', ACTIVITY_LIKES_IMAGE_FILE_ID, await interactions.list_my_likes(user_id, limit=500)
    if section == 'liked_by':
        return 'activity.section.liked_by.title', ACTIVITY_LIKED_BY_IMAGE_FILE_ID, await interactions.list_who_liked_me(user_id, limit=500)
    return 'activity.section.friends.title', ACTIVITY_FRIENDS_IMAGE_FILE_ID, await interactions.list_friends(user_id, limit=500)


async def _render_activity_main(
    *,
    message: Message,
    user_id: int,
    locale: str,
    i18n: LocalizationManager,
    session: AsyncSession,
    use_edit: bool,
) -> None:
    caption = i18n.t(locale, 'activity.card')
    keyboard = activity_open_keyboard(
        i18n,
        locale,
        counters=await unread_activity_counters(user_id, session),
    )
    if not use_edit:
        await message.answer_photo(photo=ACTIVITY_IMAGE_FILE_ID, caption=caption, parse_mode='HTML', reply_markup=keyboard)
        return

    media = InputMediaPhoto(media=ACTIVITY_IMAGE_FILE_ID, caption=caption, parse_mode='HTML')
    try:
        await message.edit_media(media=media, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if 'message is not modified' in str(exc):
            return
        raise


async def _render_activity_section(
    *,
    message: Message,
    section: str,
    page: int,
    user_id: int,
    locale: str,
    i18n: LocalizationManager,
    session: AsyncSession,
) -> None:
    interactions = InteractionService(session)
    title_key, image_file_id, items = await _section_payload(section=section, interactions=interactions, user_id=user_id)
    normalized_items = _normalize_activity_items(items, locale, i18n)
    page_items, safe_page, total_pages = _paginate_items(normalized_items, page)
    caption = _activity_caption(
        title=i18n.t(locale, title_key),
        page_items=page_items,
        page=safe_page,
        total_pages=total_pages,
        locale=locale,
        i18n=i18n,
    )
    keyboard = activity_section_keyboard(
        i18n,
        locale,
        section=section,
        page=safe_page,
        items=page_items,
        has_previous=safe_page > 1,
        has_next=safe_page < total_pages,
    )
    media = InputMediaPhoto(media=image_file_id, caption=caption, parse_mode='HTML')
    try:
        await message.edit_media(media=media, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if 'message is not modified' in str(exc):
            return
        raise


@router.message(F.text == BTN_BACK)
async def back_to_main_menu_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    await state.clear()
    if payload is None:
        return

    user_id, locale = payload
    await _show_main_menu(
        message,
        user_id=user_id,
        locale=locale,
        session=session,
        i18n=i18n,
    )


@router.message(F.text.func(_is_activity_menu_button))
@router.message(Command('actions'))
async def activity_menu_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    await state.clear()
    if payload is None:
        return

    user_id, locale = payload
    await _render_activity_main(
        message=message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        use_edit=False,
    )


@router.callback_query(F.data == CB_ACTIVITY_OPEN)
@router.callback_query(F.data == CB_ACTIVITY_BACK)
async def activity_open_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    await _render_activity_main(
        message=callback.message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        use_edit=True,
    )


@router.callback_query(F.data.startswith(CB_ACTIVITY_SECTION_PREFIX))
@router.callback_query(F.data.startswith(CB_ACTIVITY_PAGE_PREFIX))
@router.callback_query(F.data.startswith('activity:refresh:'))
async def activity_section_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return

    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return

    parsed = _parse_section_and_page(callback.data or '')
    if parsed is None:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return
    section, page = parsed

    if section not in ACTIVITY_SECTIONS:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    await UserService(session).mark_activity_section_seen(user_id, section)
    await callback.answer()
    await _render_activity_section(
        message=callback.message,
        section=section,
        page=page,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
    )


@router.message(F.text == BTN_CREATE_PROFILE)
async def create_profile_stub_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    await state.clear()
    if payload is None:
        return

    _, locale = payload
    await message.answer(i18n.t(locale, 'profiles.create.stub'), reply_markup=back_keyboard())
