from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    BTN_MESSAGES_TEXTS,
    CB_CHATS_CANCEL_NEW,
    CB_CHATS_CANCEL_SEND_PREFIX,
    CB_CHATS_DELETE_PREFIX,
    CB_CHATS_MESSAGES_PAGE_PREFIX,
    CB_CHATS_NEW,
    CB_CHATS_OPEN,
    CB_CHATS_OPEN_CHAT_PREFIX,
    CB_CHATS_PAGE_PREFIX,
    CB_CHATS_SEND_PREFIX,
    CHAT_IMAGE_FILE_ID,
)
from app.handlers.context import ensure_user_and_locale
from app.handlers.states import ChatStates
from app.keyboards import (
    chat_new_cancel_keyboard,
    chat_new_message_notice_keyboard,
    chat_send_cancel_keyboard,
    chat_view_keyboard,
    chats_list_keyboard,
)
from app.locales import LocalizationManager
from app.services import ChatService, MessageService, UserService

router = Router(name='chats')

CHAT_PAGE_SIZE = 10
MESSAGE_PAGE_SIZE = 10


def _display_title(*, full_name: str | None, username: str | None, user_id: int, locale: str, i18n: LocalizationManager) -> str:
    if isinstance(full_name, str) and full_name.strip():
        return full_name.strip()
    if isinstance(username, str) and username.strip():
        return f"@{username.strip()}"
    return i18n.t(locale, 'chat.user.fallback', user_id=user_id)


def _safe_page(raw: str | None, default: int = 1) -> int:
    if raw is None:
        return default
    try:
        page = int(raw)
    except ValueError:
        return default
    return page if page >= 1 else default


def _safe_chat_id(raw: str | None) -> int:
    if raw is None:
        return 0
    try:
        value = int(raw)
    except ValueError:
        return 0
    return value if value > 0 else 0


async def _render_chats_list(
    *,
    message: Message,
    user_id: int,
    locale: str,
    i18n: LocalizationManager,
    session: AsyncSession,
    page: int = 1,
    use_edit: bool,
) -> None:
    payload = await ChatService(session).list_user_chats_paginated(user_id, page=page, page_size=CHAT_PAGE_SIZE)
    items_raw = payload['items'] if isinstance(payload.get('items'), list) else []
    safe_page = int(payload.get('page', 1) or 1)
    total_pages = int(payload.get('total_pages', 1) or 1)

    items: list[dict[str, int | str | None]] = []
    for item in items_raw:
        chat_id = item.get('chat_id')
        counterpart_id = item.get('counterpart_id')
        if not isinstance(chat_id, int) or not isinstance(counterpart_id, int):
            continue
        title = _display_title(
            full_name=item.get('full_name') if isinstance(item.get('full_name'), str) else None,
            username=item.get('username') if isinstance(item.get('username'), str) else None,
            user_id=counterpart_id,
            locale=locale,
            i18n=i18n,
        )
        unread_count_raw = item.get('unread_count')
        unread_count = unread_count_raw if isinstance(unread_count_raw, int) else 0
        items.append(
            {
                'chat_id': chat_id,
                'counterpart_id': counterpart_id,
                'display_title': title,
                'unread_count': unread_count,
            }
        )

    text_lines = [f"<b>{i18n.t(locale, 'chat.list.title')}</b>"]
    if not items:
        text_lines.extend(['', i18n.t(locale, 'chat.list.empty')])
    if total_pages > 1:
        text_lines.extend(['', i18n.t(locale, 'chat.list.page', page=safe_page, total_pages=total_pages)])
    text = '\n'.join(text_lines)

    keyboard = chats_list_keyboard(
        i18n=i18n,
        locale=locale,
        chats=items,
        page=safe_page,
        total_pages=total_pages,
    )

    if not use_edit:
        await message.answer_photo(
            photo=CHAT_IMAGE_FILE_ID,
            caption=text,
            parse_mode='HTML',
            reply_markup=keyboard,
        )
        return

    media = InputMediaPhoto(media=CHAT_IMAGE_FILE_ID, caption=text, parse_mode='HTML')
    try:
        await message.edit_media(media=media, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if 'message is not modified' in str(exc):
            return
        await message.answer_photo(
            photo=CHAT_IMAGE_FILE_ID,
            caption=text,
            parse_mode='HTML',
            reply_markup=keyboard,
        )


async def _notify_about_new_message(
    *,
    message: Message,
    session: AsyncSession,
    i18n: LocalizationManager,
    sender_id: int,
    receiver_id: int,
    chat_id: int,
    fallback_locale: str,
) -> None:
    users = UserService(session)
    settings = await users.notification_settings(receiver_id)
    if not settings.get('messages', True):
        return

    sender = await users.get_user(sender_id)
    receiver = await users.get_user(receiver_id)
    receiver_locale = getattr(getattr(receiver, 'language', None), 'value', None) or fallback_locale
    sender_name = _display_title(
        full_name=getattr(sender, 'full_name', None),
        username=getattr(sender, 'username', None),
        user_id=sender_id,
        locale=receiver_locale,
        i18n=i18n,
    )
    try:
        await message.bot.send_message(
            receiver_id,
            i18n.t(receiver_locale, 'chat.notify.new_in_chat'),
            parse_mode='HTML',
            reply_markup=chat_new_message_notice_keyboard(chat_id=chat_id, nickname=sender_name),
        )
    except Exception:
        pass


async def _render_chat_view(
    *,
    message: Message,
    user_id: int,
    locale: str,
    i18n: LocalizationManager,
    session: AsyncSession,
    chat_id: int,
    page: int = 1,
    use_edit: bool,
) -> bool:
    chat_service = ChatService(session)
    chat = await chat_service.get_chat_for_user(chat_id, user_id)
    if chat is None:
        return False

    counterpart = await chat_service.get_counterpart_user(chat, user_id)
    counterpart_name = _display_title(
        full_name=getattr(counterpart, 'full_name', None),
        username=getattr(counterpart, 'username', None),
        user_id=chat.participant_2_id if chat.participant_1_id == user_id else chat.participant_1_id,
        locale=locale,
        i18n=i18n,
    )

    messages_payload = await MessageService(session).list_chat_messages_paginated(
        chat_id=chat.id,
        user_id=user_id,
        page=page,
        page_size=MESSAGE_PAGE_SIZE,
    )
    if messages_payload is None:
        return False

    items = messages_payload['items'] if isinstance(messages_payload.get('items'), list) else []
    safe_page = int(messages_payload.get('page', 1) or 1)
    total_pages = int(messages_payload.get('total_pages', 1) or 1)
    has_older = bool(messages_payload.get('has_older', False))
    has_newer = bool(messages_payload.get('has_newer', False))

    lines: list[str] = [f"<b>{i18n.t(locale, 'chat.open.title', nickname=escape(counterpart_name))}</b>", '']
    if not items:
        lines.append(i18n.t(locale, 'chat.open.empty'))
    else:
        for entity in items:
            text = escape((entity.text or '').strip())
            speaker = i18n.t(locale, 'chat.label.you') if int(entity.from_user_id) == user_id else counterpart_name
            lines.append(f"<b>{escape(speaker)}:</b>")
            lines.append(f'- {text}')
            lines.append('')
    if total_pages > 1:
        lines.append(i18n.t(locale, 'chat.list.page', page=safe_page, total_pages=total_pages))
    text = '\n'.join(lines).strip()

    keyboard = chat_view_keyboard(
        i18n=i18n,
        locale=locale,
        chat_id=chat.id,
        page=safe_page,
        has_older=has_older,
        has_newer=has_newer,
    )

    if not use_edit:
        await message.answer(text, reply_markup=keyboard)
        return True

    try:
        await message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if 'message is not modified' in str(exc):
            return True
        await message.answer(text, reply_markup=keyboard)
    return True


@router.message(F.text.in_(BTN_MESSAGES_TEXTS))
async def chats_open_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return
    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        return
    await state.clear()
    await _render_chats_list(
        message=message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        page=1,
        use_edit=False,
    )


@router.callback_query(F.data == CB_CHATS_OPEN)
async def chats_open_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await _render_chats_list(
        message=callback.message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        page=1,
        use_edit=True,
    )


@router.callback_query(F.data.startswith(CB_CHATS_PAGE_PREFIX))
async def chats_page_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return
    await state.clear()
    raw = (callback.data or '').replace(CB_CHATS_PAGE_PREFIX, '', 1)
    page = _safe_page(raw, 1)
    await callback.answer()
    await _render_chats_list(
        message=callback.message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        page=page,
        use_edit=True,
    )


@router.callback_query(F.data == CB_CHATS_NEW)
async def chats_start_new_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    _, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return
    await state.set_state(ChatStates.waiting_for_new_chat_target)
    await callback.answer()
    await callback.message.answer(
        i18n.t(locale, 'chat.start.prompt'),
        parse_mode='HTML',
        reply_markup=chat_new_cancel_keyboard(i18n=i18n, locale=locale),
    )


@router.callback_query(F.data == CB_CHATS_CANCEL_NEW)
async def chats_cancel_new_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.message(StateFilter(ChatStates.waiting_for_new_chat_target))
async def chats_start_new_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return
    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    locale = locale or i18n.default_locale
    raw = (message.text or '').strip()
    if not raw:
        await message.answer(i18n.t(locale, 'chat.start.invalid'))
        return

    chat_service = ChatService(session)
    target_user = await chat_service.find_user_by_nickname_or_username(raw)
    if target_user is None:
        await message.answer(i18n.t(locale, 'chat.start.not_found'))
        return
    if int(target_user.id) == user_id:
        await message.answer(i18n.t(locale, 'chat.start.self'))
        return

    chat, _ = await chat_service.create_or_get_chat(user_id, int(target_user.id))
    await state.clear()
    await _render_chat_view(
        message=message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        chat_id=chat.id,
        page=1,
        use_edit=False,
    )


@router.callback_query(F.data.startswith(CB_CHATS_OPEN_CHAT_PREFIX))
async def chats_open_chat_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return
    await state.clear()
    raw = (callback.data or '').replace(CB_CHATS_OPEN_CHAT_PREFIX, '', 1)
    chat_id = _safe_chat_id(raw)
    if chat_id <= 0:
        await callback.answer(i18n.t(locale, 'chat.not_found'), show_alert=True)
        return
    await callback.answer()
    rendered = await _render_chat_view(
        message=callback.message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        chat_id=chat_id,
        page=1,
        use_edit=True,
    )
    if not rendered:
        await callback.answer(i18n.t(locale, 'chat.not_found'), show_alert=True)
        await _render_chats_list(
            message=callback.message,
            user_id=user_id,
            locale=locale,
            i18n=i18n,
            session=session,
            page=1,
            use_edit=True,
        )


@router.callback_query(F.data.startswith(CB_CHATS_MESSAGES_PAGE_PREFIX))
async def chats_messages_page_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    if locale is None:
        await callback.answer()
        return
    await state.clear()
    payload = (callback.data or '').replace(CB_CHATS_MESSAGES_PAGE_PREFIX, '', 1)
    if ':' not in payload:
        await callback.answer(i18n.t(locale, 'chat.not_found'), show_alert=True)
        return
    chat_raw, page_raw = payload.split(':', 1)
    chat_id = _safe_chat_id(chat_raw)
    page = _safe_page(page_raw, 1)
    if chat_id <= 0:
        await callback.answer(i18n.t(locale, 'chat.not_found'), show_alert=True)
        return
    await callback.answer()
    rendered = await _render_chat_view(
        message=callback.message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        chat_id=chat_id,
        page=page,
        use_edit=True,
    )
    if not rendered:
        await callback.answer(i18n.t(locale, 'chat.not_found'), show_alert=True)


@router.callback_query(F.data.startswith(CB_CHATS_SEND_PREFIX))
async def chats_send_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    raw = (callback.data or '').replace(CB_CHATS_SEND_PREFIX, '', 1)
    chat_id = _safe_chat_id(raw)
    if chat_id <= 0:
        await callback.answer(i18n.t(locale, 'chat.not_found'), show_alert=True)
        return
    chat = await ChatService(session).get_chat_for_user(chat_id, user_id)
    if chat is None:
        await callback.answer(i18n.t(locale, 'chat.not_found'), show_alert=True)
        return

    await state.set_state(ChatStates.waiting_for_chat_message)
    await state.update_data(chat_send_chat_id=chat.id)
    await callback.answer()
    prompt = await callback.message.answer(
        i18n.t(locale, 'chat.send.prompt'),
        parse_mode='HTML',
        reply_markup=chat_send_cancel_keyboard(i18n=i18n, locale=locale, chat_id=chat.id),
    )
    await state.update_data(
        chat_send_prompt_chat_id=prompt.chat.id,
        chat_send_prompt_message_id=prompt.message_id,
    )


@router.callback_query(F.data.startswith(CB_CHATS_CANCEL_SEND_PREFIX))
async def chats_cancel_send_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.message(StateFilter(ChatStates.waiting_for_chat_message))
async def chats_send_message_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return
    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    locale = locale or i18n.default_locale
    text = (message.text or '').strip()
    data = await state.get_data()
    chat_id_raw = data.get('chat_send_chat_id')
    prompt_chat_id = data.get('chat_send_prompt_chat_id')
    prompt_message_id = data.get('chat_send_prompt_message_id')
    if not isinstance(chat_id_raw, int):
        await state.clear()
        await message.answer(i18n.t(locale, 'chat.not_found'))
        return

    message_entity, error = await MessageService(session).send_message_in_chat(
        chat_id=chat_id_raw,
        sender_id=user_id,
        text=text,
    )
    if message_entity is None:
        if error == 'empty_message':
            await message.answer(
                i18n.t(locale, 'chat.send.empty'),
                reply_markup=chat_send_cancel_keyboard(i18n=i18n, locale=locale, chat_id=chat_id_raw),
            )
            return
        if error == 'too_long':
            await message.answer(
                i18n.t(locale, 'chat.send.too_long', max_len=1000),
                reply_markup=chat_send_cancel_keyboard(i18n=i18n, locale=locale, chat_id=chat_id_raw),
            )
            return
        await state.clear()
        await message.answer(i18n.t(locale, 'chat.not_found'))
        await _render_chats_list(
            message=message,
            user_id=user_id,
            locale=locale,
            i18n=i18n,
            session=session,
            page=1,
            use_edit=False,
        )
        return

    if isinstance(prompt_chat_id, int) and isinstance(prompt_message_id, int):
        try:
            await message.bot.delete_message(chat_id=prompt_chat_id, message_id=prompt_message_id)
        except TelegramBadRequest:
            pass

    await _notify_about_new_message(
        message=message,
        session=session,
        i18n=i18n,
        sender_id=user_id,
        receiver_id=int(message_entity.to_user_id),
        chat_id=int(message_entity.chat_id),
        fallback_locale=locale,
    )

    await state.clear()
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _render_chat_view(
        message=message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        chat_id=chat_id_raw,
        page=1,
        use_edit=False,
    )


@router.callback_query(F.data.startswith(CB_CHATS_DELETE_PREFIX))
async def chats_delete_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        return
    user_id, locale = await ensure_user_and_locale(callback.from_user, session)
    locale = locale or i18n.default_locale
    raw = (callback.data or '').replace(CB_CHATS_DELETE_PREFIX, '', 1)
    chat_id = _safe_chat_id(raw)
    await state.clear()
    if chat_id <= 0:
        await callback.answer(i18n.t(locale, 'chat.not_found'), show_alert=True)
        return

    deleted = await ChatService(session).delete_chat(chat_id, user_id)
    if not deleted:
        await callback.answer(i18n.t(locale, 'chat.not_found'), show_alert=True)
        return

    await callback.answer(i18n.t(locale, 'chat.delete.success'))
    await _render_chats_list(
        message=callback.message,
        user_id=user_id,
        locale=locale,
        i18n=i18n,
        session=session,
        page=1,
        use_edit=True,
    )
