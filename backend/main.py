"""OpenBrief - Multi-Agent Legal Document Intelligence Platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
