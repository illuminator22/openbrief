"""Routing endpoint for classifying user input intent."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.routing.semantic_router import get_semantic_router

router = APIRouter()


class ClassifyRequest(BaseModel):
    """Request body for text classification."""

    text: str = Field(..., min_length=1, max_length=2000)


class ClassifyResponse(BaseModel):
    """Classification result from semantic routing."""

    route: str
    confidence: float
    full_review_score: float
    targeted_score: float
    low_confidence: bool


@router.post("/classify", response_model=ClassifyResponse)
async def classify_text(request: ClassifyRequest) -> ClassifyResponse:
    """Classify user text as targeted question or full review request.

    Free endpoint — uses local embedding model, no LLM call.
    """
    semantic_router = get_semantic_router()
    result = semantic_router.classify(request.text)
    return ClassifyResponse(**result)
