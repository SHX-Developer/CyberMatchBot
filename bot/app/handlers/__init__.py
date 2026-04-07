from app.handlers.chats import router as chats_router
from aiogram import Dispatcher

from app.handlers.fallback import router as fallback_router
from app.handlers.group_guard import router as group_guard_router
from app.handlers.image_receiver import router as image_receiver_router
from app.handlers.menu_sections import router as menu_sections_router
from app.handlers.profile import router as profile_router
from app.handlers.profiles import router as profiles_router
from app.handlers.search import router as search_router
from app.handlers.start import router as start_router


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(group_guard_router)
    dp.include_router(start_router)
    dp.include_router(image_receiver_router)
    dp.include_router(profile_router)
    dp.include_router(profiles_router)
    dp.include_router(search_router)
    dp.include_router(chats_router)
    dp.include_router(menu_sections_router)
    dp.include_router(fallback_router)
