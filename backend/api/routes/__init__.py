"""API route exports."""

from api.routes.analysis import router as analysis_router
from api.routes.documents import router as documents_router
from api.routes.evaluation import router as evaluation_router
from api.routes.settings import router as settings_router

__all__ = ["analysis_router", "documents_router", "evaluation_router", "settings_router"]
