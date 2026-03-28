from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
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
    BTN_ACTIVITY_TEXTS,
    BTN_BACK,
    BTN_CREATE_PROFILE,
    CB_ACTIVITY_BACK,
    CB_ACTIVITY_OPEN,
    CB_ACTIVITY_REFRESH_PREFIX,
    CB_ACTIVITY_SECTION_PREFIX,
)
from app.handlers.context import ensure_user_and_locale
from app.keyboards import (
    activity_open_keyboard,
    activity_section_keyboard,
    back_keyboard,
    language_keyboard,
    main_menu_keyboard,
)
from app.locales import LocalizationManager
from app.services import InteractionService

router = Router(name='menu_sections')

ACTIVITY_SECTIONS = {'subscriptions', 'subscribers', 'likes', 'liked_by', 'friends'}


async def _require_locale(message: Message, session: AsyncSession, i18n: LocalizationManager) -> tuple[int, str] | None:
    if message.from_user is None:
        return None

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return None

    return user_id, locale


async def _show_main_menu(message: Message, locale: str, i18n: LocalizationManager) -> None:
    await message.answer(i18n.t(locale, 'start.welcome'), reply_markup=main_menu_keyboard(i18n, locale))


def _format_activity_list(items: list[dict[str, int | str | None]], locale: str, i18n: LocalizationManager) -> str:
    usernames: list[str] = []
    for item in items:
        username = item.get('username')
        if isinstance(username, str) and username:
            usernames.append(f'@{username}')

    if not usernames:
        return i18n.t(locale, 'activity.list.empty')

    lines: list[str] = []
    for index, username in enumerate(usernames, start=1):
        lines.append(f'{index}. {username}')
    return '\n'.join(lines)


async def _section_payload(
    *,
    section: str,
    interactions: InteractionService,
    user_id: int,
) -> tuple[str, str, list[dict[str, int | str | None]]]:
    if section == 'subscriptions':
        return 'activity.section.subscriptions.title', ACTIVITY_SUBSCRIPTIONS_IMAGE_FILE_ID, await interactions.list_subscriptions(user_id)
    if section == 'subscribers':
        return 'activity.section.subscribers.title', ACTIVITY_SUBSCRIBERS_IMAGE_FILE_ID, await interactions.list_subscribers(user_id)
    if section == 'likes':
        return 'activity.section.likes.title', ACTIVITY_LIKES_IMAGE_FILE_ID, await interactions.list_my_likes(user_id)
    if section == 'liked_by':
        return 'activity.section.liked_by.title', ACTIVITY_LIKED_BY_IMAGE_FILE_ID, await interactions.list_who_liked_me(user_id)
    return 'activity.section.friends.title', ACTIVITY_FRIENDS_IMAGE_FILE_ID, await interactions.list_friends(user_id)


async def _render_activity_main(
    *,
    message: Message,
    locale: str,
    i18n: LocalizationManager,
    use_edit: bool,
) -> None:
    caption = i18n.t(locale, 'activity.card')
    keyboard = activity_open_keyboard(i18n, locale)
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
    user_id: int,
    locale: str,
    i18n: LocalizationManager,
    session: AsyncSession,
) -> None:
    interactions = InteractionService(session)
    title_key, image_file_id, items = await _section_payload(section=section, interactions=interactions, user_id=user_id)
    caption = i18n.t(
        locale,
        'activity.section.card',
        title=i18n.t(locale, title_key),
        list_text=_format_activity_list(items, locale, i18n),
    )
    keyboard = activity_section_keyboard(i18n, locale, section)
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

    _, locale = payload
    await _show_main_menu(message, locale, i18n)


@router.message(F.text.in_(BTN_ACTIVITY_TEXTS))
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

    _, locale = payload
    await _render_activity_main(message=message, locale=locale, i18n=i18n, use_edit=False)


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

    _, locale = await ensure_user_and_locale(callback.from_user, session)
    await state.clear()
    if locale is None:
        await callback.answer()
        return

    await callback.answer()
    await _render_activity_main(message=callback.message, locale=locale, i18n=i18n, use_edit=True)


@router.callback_query(F.data.startswith(CB_ACTIVITY_SECTION_PREFIX))
@router.callback_query(F.data.startswith(CB_ACTIVITY_REFRESH_PREFIX))
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

    data = callback.data or ''
    if data.startswith(CB_ACTIVITY_SECTION_PREFIX):
        section = data.replace(CB_ACTIVITY_SECTION_PREFIX, '', 1)
    else:
        section = data.replace(CB_ACTIVITY_REFRESH_PREFIX, '', 1)

    if section not in ACTIVITY_SECTIONS:
        await callback.answer(i18n.t(locale, 'error.unknown'), show_alert=True)
        return

    await callback.answer()
    await _render_activity_section(
        message=callback.message,
        section=section,
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
