import re

from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import LanguageCode
from app.handlers.context import ensure_user_and_locale
from app.handlers.states import OnboardingStates
from app.keyboards import language_keyboard, main_menu_keyboard
from app.locales import LocalizationManager
from app.constants import MAIN_MENU_IMAGE_FILE_ID
from app.services import UserService

router = Router(name='start')

NICKNAME_PATTERN = re.compile(r'^[a-z]{4,}$')


async def _sync_avatar_from_telegram(user_id: int, message: Message, user_service: UserService) -> None:
    try:
        photos = await message.bot.get_user_profile_photos(user_id=user_id, limit=1)
    except Exception:
        return
    if not photos.photos:
        return
    avatar_file_id = photos.photos[0][-1].file_id
    await user_service.set_avatar_file_id(user_id, avatar_file_id)


async def _prompt_nickname(message: Message) -> None:
    await message.answer(
        '🎯 <b>Создайте никнейм для личного профиля</b>\n\n'
        '✅ <b>Требования:</b>\n'
        '• только английские буквы\n'
        '• минимум 4 символа\n'
        '• сохраняется в нижнем регистре\n\n'
        '💡 <b>Пример:</b> <code>cybermate</code>',
        parse_mode='HTML',
    )


async def _needs_nickname(user_service: UserService, user_id: int) -> bool:
    user = await user_service.get_user(user_id)
    return user is None or not (user.full_name and user.full_name.strip())


async def _send_main_menu(message: Message, locale: str, i18n: LocalizationManager) -> None:
    await message.answer_photo(
        photo=MAIN_MENU_IMAGE_FILE_ID,
        caption=i18n.t(locale, 'start.welcome'),
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(i18n, locale),
    )


@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    user_service = UserService(session)
    await _sync_avatar_from_telegram(user_id, message, user_service)
    await state.clear()

    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return

    if await _needs_nickname(user_service, user_id):
        await state.set_state(OnboardingStates.waiting_for_nickname)
        await _prompt_nickname(message)
        return

    await _send_main_menu(message, locale, i18n)


@router.callback_query(F.data.startswith('lang:set:'))
async def set_language_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, i18n: LocalizationManager) -> None:
    if callback.from_user is None:
        return

    data = callback.data or ''
    language_raw = data.split(':')[-1]
    try:
        language = LanguageCode(language_raw)
    except ValueError:
        await callback.answer(i18n.t(i18n.default_locale, 'error.unknown'), show_alert=True)
        return

    user_service = UserService(session)
    await user_service.ensure_user(callback.from_user)
    await user_service.set_language(callback.from_user.id, language)

    locale = language.value
    await callback.answer(i18n.t(locale, 'language.changed'))

    if callback.message:
        await state.clear()
        if await _needs_nickname(user_service, callback.from_user.id):
            await state.set_state(OnboardingStates.waiting_for_nickname)
            await _prompt_nickname(callback.message)
            return
        await _send_main_menu(callback.message, locale, i18n)


@router.message(StateFilter(OnboardingStates.waiting_for_nickname))
async def onboarding_nickname_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    if message.from_user is None:
        return

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    locale = locale or i18n.default_locale
    raw = (message.text or '').strip().lower()

    if not NICKNAME_PATTERN.fullmatch(raw):
        await message.answer(
            '❌ <b>Неверный формат никнейма</b>\n\n'
            'Используйте только английские буквы и минимум 4 символа.\n'
            '💡 Пример: <code>cybermate</code>',
            parse_mode='HTML',
        )
        return

    user_service = UserService(session)
    if await user_service.nickname_exists(raw, exclude_user_id=user_id):
        await message.answer('❌ Этот никнейм уже занят. Введите другой.')
        return

    await user_service.set_full_name(user_id, raw)
    await state.clear()
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer(
        f'✅ Никнейм <b>{raw}</b> сохранен.',
        parse_mode='HTML',
    )
    await _send_main_menu(message, locale, i18n)
