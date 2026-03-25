"""User settings endpoints for LLM key management."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import EncryptionError
from api.routes.auth import get_current_user
from core.llm.encryption import encrypt_api_key
from core.llm.provider import SUPPORTED_PROVIDERS
from db.database import get_db
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


class SetLLMKeyRequest(BaseModel):
    """Request body for setting an LLM API key."""

    api_key: str
    provider: str
    model: str | None = None


class LLMSettingsResponse(BaseModel):
    """Response for current LLM settings (never includes the actual key)."""

    provider: str | None
    model: str | None
    has_key: bool


class MessageResponse(BaseModel):
    """Generic success message response."""

    message: str


@router.post("/llm-key", response_model=MessageResponse)
async def set_llm_key(
    request: SetLLMKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Store an encrypted LLM API key for the current user.

    Validates the provider, encrypts the key, and stores it.
    Never returns or logs the actual API key.
    """
    if request.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: '{request.provider}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}",
        )

    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    try:
        encrypted = encrypt_api_key(request.api_key)
    except EncryptionError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    current_user.encrypted_llm_key = encrypted
    current_user.llm_provider = request.provider
    current_user.llm_model = request.model
    await db.flush()

    logger.info("LLM key updated for user %s (provider=%s)", current_user.id, request.provider)

    return MessageResponse(message="API key saved successfully")


@router.get("/llm", response_model=LLMSettingsResponse)
async def get_llm_settings(
    current_user: User = Depends(get_current_user),
) -> LLMSettingsResponse:
    """Get current LLM settings for the user.

    Returns the provider and model, plus whether a key is stored.
    Never returns the actual API key.
    """
    return LLMSettingsResponse(
        provider=current_user.llm_provider,
        model=current_user.llm_model,
        has_key=current_user.encrypted_llm_key is not None,
    )


@router.delete("/llm-key", response_model=MessageResponse)
async def delete_llm_key(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Remove the stored LLM API key for the current user."""
    current_user.encrypted_llm_key = None
    await db.flush()

    logger.info("LLM key removed for user %s", current_user.id)

    return MessageResponse(message="API key removed successfully")
