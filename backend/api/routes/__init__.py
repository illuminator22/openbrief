"""API route exports."""

from api.routes.analysis import router as analysis_router
from api.routes.documents import router as documents_router
from api.routes.settings import router as settings_router

__all__ = ["analysis_router", "documents_router", "settings_router"]
