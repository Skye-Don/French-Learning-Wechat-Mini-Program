from .audit import router as audit_router
from .auth import router as admin_auth_router
from .flashcards import router as admin_flashcards_router
from .lessons import router as admin_lessons_router
from .settings import router as admin_settings_router
from .users import router as admin_users_router

__all__ = [
    "admin_auth_router",
    "admin_flashcards_router",
    "admin_lessons_router",
    "admin_users_router",
    "admin_settings_router",
    "audit_router",
]
