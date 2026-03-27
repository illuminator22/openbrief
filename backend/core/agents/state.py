"""Shared state schema for the multi-agent pipeline.

All agents read from and write to this state as it flows through
the pipeline: Research → Analysis → Draft → Fact-Check.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class RetrievedPassage:
    """A single passage retrieved by the Research Agent."""

    chunk_id: str
    content: str
    page_number: Optional[int]
    section_title: Optional[str]
    similarity_score: float
    chunk_index: int


@dataclass
class AgentState:
    """Shared state flowing between all agents in the pipeline.

    Flow: Research → Analysis → Draft → Fact-Check
    Each agent reads from and writes to this state.
    """

    # Input (set at the start)
    document_id: UUID
    query: str
    query_type: str  # "targeted_question" or "full_review"
    model: Optional[str] = None

    # Research Agent output
    passages: list[RetrievedPassage] = field(default_factory=list)
    retrieval_time_ms: Optional[int] = None

    # Analysis Agent output
    findings: list = field(default_factory=list)
    analysis_time_ms: Optional[int] = None

    # Draft Agent output
    draft_answer: Optional[str] = None
    draft_citations: list = field(default_factory=list)
    draft_time_ms: Optional[int] = None

    # Fact-Check Agent output
    verified_answer: Optional[str] = None
    verified_citations: list = field(default_factory=list)
    confidence_score: Optional[float] = None
    factcheck_issues: list = field(default_factory=list)
    factcheck_time_ms: Optional[int] = None

    # Orchestration metadata
    current_agent: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    agent_trace: list = field(default_factory=list)
    started_at: Optional[datetime] = field(default=None)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        """Set started_at automatically if not provided."""
        if self.started_at is None:
            self.started_at = datetime.utcnow()
