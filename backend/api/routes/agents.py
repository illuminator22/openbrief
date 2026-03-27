# TEMPORARY — test endpoints for individual agents. Remove after LangGraph orchestration is built.

"""Test endpoints for verifying individual agents work independently."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user
from core.agents import AgentState, ResearchAgent
from db.database import get_db
from db.models import User

router = APIRouter()


class TestResearchRequest(BaseModel):
    """Request body for testing the Research Agent."""

    document_id: uuid.UUID
    query: str = Field(..., min_length=1, max_length=2000)
    reformulate: bool = True


@router.post("/test-research")
async def test_research_agent(
    request: TestResearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Test the Research Agent independently.

    Creates an AgentState, runs the Research Agent, and returns
    the full state including passages, timing, and trace.
    """
    state = AgentState(
        document_id=request.document_id,
        query=request.query,
        query_type="targeted_question",
    )

    agent = ResearchAgent()
    state = await agent.run(
        state,
        db,
        reformulate_queries=request.reformulate,
        user=current_user,
    )

    return {
        "document_id": str(state.document_id),
        "query": state.query,
        "passages": [
            {
                "chunk_id": p.chunk_id,
                "content": p.content[:200] + "..." if len(p.content) > 200 else p.content,
                "page_number": p.page_number,
                "section_title": p.section_title,
                "similarity_score": p.similarity_score,
                "chunk_index": p.chunk_index,
            }
            for p in state.passages
        ],
        "retrieval_time_ms": state.retrieval_time_ms,
        "agent_trace": state.agent_trace,
        "error": state.error,
    }
