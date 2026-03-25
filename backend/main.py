"""OpenBrief - Multi-Agent Legal Document Intelligence Platform."""
import logging
logging.basicConfig(level=logging.INFO)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import analysis_router, documents_router, settings_router
from config import settings

app = FastAPI(
    title="OpenBrief",
    description="Open-source multi-agent legal document intelligence platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
