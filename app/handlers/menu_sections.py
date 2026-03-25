from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    BTN_BACK,
    BTN_CREATE_PROFILE,
    BTN_FIND_TEAMMATE,
    BTN_LIKES,
    BTN_MESSAGES,
    BTN_MY_PROFILES,
    BTN_SUBSCRIPTIONS,
)
from app.handlers.context import ensure_user_and_locale
from app.keyboards import (
    back_keyboard,
    find_teammate_without_profiles_keyboard,
    language_keyboard,
    main_menu_keyboard,
    my_profiles_empty_keyboard,
)
from app.locales import LocalizationManager
from app.services import ProfileService

router = Router(name='menu_sections')


async def _require_locale(message: Message, session: AsyncSession, i18n: LocalizationManager) -> tuple[int, str] | None:
    if message.from_user is None:
        return None

    user_id, locale = await ensure_user_and_locale(message.from_user, session)
    if locale is None:
        await message.answer(i18n.t(i18n.default_locale, 'language.select'), reply_markup=language_keyboard())
        return None

    return user_id, locale


async def _show_main_menu(message: Message, locale: str, i18n: LocalizationManager) -> None:
    await message.answer(i18n.t(locale, 'start.welcome'), reply_markup=main_menu_keyboard())


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


@router.message(F.text == BTN_FIND_TEAMMATE)
async def find_teammate_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    await state.clear()
    if payload is None:
        return

    user_id, _ = payload
    profile_service = ProfileService(session)
    if not await profile_service.has_any_profile(user_id):
        await message.answer(
            'Сначала создайте анкету, чтобы искать тиммейтов.',
            reply_markup=find_teammate_without_profiles_keyboard(),
        )
        return

    await message.answer('Раздел поиска тиммейтов.', reply_markup=back_keyboard())


@router.message(F.text == BTN_MESSAGES)
async def messages_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    await state.clear()
    if payload is None:
        return

    await message.answer('У вас пока нет сообщений.', reply_markup=back_keyboard())


@router.message(F.text == BTN_LIKES)
async def likes_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    await state.clear()
    if payload is None:
        return

    await message.answer('У вас пока нет лайков.', reply_markup=back_keyboard())


@router.message(F.text == BTN_SUBSCRIPTIONS)
async def subscriptions_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    await state.clear()
    if payload is None:
        return

    await message.answer('У вас пока нет подписок.', reply_markup=back_keyboard())


@router.message(F.text == BTN_MY_PROFILES)
async def my_profiles_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    i18n: LocalizationManager,
) -> None:
    payload = await _require_locale(message, session, i18n)
    await state.clear()
    if payload is None:
        return

    user_id, _ = payload
    profile_service = ProfileService(session)
    if not await profile_service.has_any_profile(user_id):
        await message.answer(
            'У вас пока нет анкет. Создайте первую анкету.',
            reply_markup=my_profiles_empty_keyboard(),
        )
        return

    await message.answer('Раздел анкет пользователя.', reply_markup=back_keyboard())


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

    await message.answer('Создание анкеты будет добавлено в следующем этапе.', reply_markup=back_keyboard())
