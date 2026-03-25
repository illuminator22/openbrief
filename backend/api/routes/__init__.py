"""API route exports."""

from api.routes.documents import router as documents_router
from api.routes.settings import router as settings_router

__all__ = ["documents_router", "settings_router"]
