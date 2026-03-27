"""Multi-agent system for legal document analysis."""

from core.agents.research_agent import ResearchAgent
from core.agents.state import AgentState, RetrievedPassage

__all__ = ["AgentState", "ResearchAgent", "RetrievedPassage"]
