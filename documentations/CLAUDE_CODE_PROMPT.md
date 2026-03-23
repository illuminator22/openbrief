# OpenBrief - Claude Code Agent Prompt
## Use this file when working with Claude Code on the OpenBrief project

---

## Project Context

You are helping Ivan Arshakyan build **OpenBrief**, an open-source multi-agent legal document intelligence platform. This is a real product being launched under BrainX Corp, not a tutorial or demo.

**What OpenBrief does:** Users upload legal documents (contracts, briefs, case filings) and a team of AI agents collaborates to analyze them. The platform features a production RAG pipeline with transparent evaluation metrics, multi-agent orchestration, a QLoRA fine-tuned entity extraction model, and an MCP server.

**Ivan's background:**
- Full-stack engineer experienced with FastAPI, PostgreSQL, Next.js, TypeScript, Python
- Has a DigitalOcean Ubuntu server already running other projects
- Currently learning AI engineering (RAG, QLoRA, AI Agents course)
- New to: LangChain/LangGraph, pgvector, Sentence Transformers, MCP SDK, DeepEval
- Prefers clean, well-documented code. Will challenge any AI-generated code that makes assumptions without verification.

---

## Critical Rules for Claude Code

1. **Never assume a file exists. Always check first.** Ivan will call you out on this.
2. **Never install packages without asking or explaining why.**
3. **Always verify imports against actual installed packages.**
4. **When writing database queries, always check the actual schema first.**
5. **Use type hints in all Python code.**
6. **Use TypeScript strict mode in all frontend code.**
7. **Every new endpoint needs error handling and input validation.**
8. **No dummy/placeholder implementations.** If something is not ready, raise a NotImplementedError with a clear message.
9. **Write docstrings for all classes and public functions.**
10. **Keep environment variables in .env, never hardcode secrets.**

---

## Tech Stack Reference

### Backend
- **Python 3.11+**
- **FastAPI** - REST API
- **PostgreSQL 15+ with pgvector extension** - Database + vector search
- **SQLAlchemy 2.0+** - ORM (async)
- **Alembic** - Database migrations
- **LangChain + LangGraph** - Agent orchestration
- **sentence-transformers** - Embedding generation (model: BAAI/bge-small-en-v1.5, 384 dims, 512 token max)
- **DeepEval** - RAG evaluation
- **PyMuPDF (fitz) + pdfplumber** - PDF parsing
- **Hugging Face transformers + peft + bitsandbytes** - QLoRA (training only)
- **MCP Python SDK (modelcontext)** - MCP server
- **httpx** - Async HTTP client for LLM API calls
- **python-multipart** - File upload handling
- **python-jose + passlib** - Auth/encryption

### Frontend
- **Next.js 14+ (App Router)**
- **TypeScript (strict)**
- **Tailwind CSS**
- **Recharts** - Charts for evaluation dashboard
- **React Query (TanStack Query)** - Data fetching

### Development
- **pytest + pytest-asyncio** - Testing
- **Ruff** - Linting
- **Black** - Formatting

---

## Architecture Rules

### BYOK (Bring Your Own Key) System
Users provide their own LLM API keys. The backend must:
- Accept API keys via settings endpoint (POST /api/settings/llm-key)
- Encrypt keys at rest using Fernet encryption
- Never log or print API keys
- Support at minimum: Anthropic (Claude), OpenAI (GPT)
- Use a provider abstraction layer so adding new providers is easy

```python
# Example provider abstraction
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], model: str) -> str: ...

class AnthropicProvider(LLMProvider): ...
class OpenAIProvider(LLMProvider): ...
```

### Entity Extraction Swappable Backend
The entity extraction system must support swapping between:
- **Option 3 (development):** Frontier model with detailed prompt
- **Option 1 (production):** Hugging Face Inference Endpoint

```python
# Example extraction abstraction
class EntityExtractor(ABC):
    @abstractmethod
    async def extract(self, text: str) -> list[Entity]: ...

class PromptExtractor(EntityExtractor): ...   # Option 3
class ModelExtractor(EntityExtractor): ...     # Option 1
```

Which extractor is used should be controlled by an environment variable:
```
ENTITY_EXTRACTION_BACKEND=prompt  # or "model"
ENTITY_MODEL_ENDPOINT=https://api-inference.huggingface.co/models/...
```

### RAG Pipeline
- Embedding model: `bge-small-en-v1.5` (384 dimensions, 512 token max sequence length)
- CRITICAL: BGE models require a query prefix for search queries: `"Represent this sentence for searching relevant passages: "` + query
  - When embedding DOCUMENT CHUNKS: no prefix, just encode the raw text
  - When embedding SEARCH QUERIES: prepend the prefix before encoding
- Vector search: pgvector with cosine similarity
- Top-k retrieval: configurable, default k=5
- Chunk size: configurable, default 512 tokens with 50 token overlap
- Always return source citations with chunk IDs and page numbers

### Query Routing (How the system decides which mode to use)
The UI presents three interaction methods after a document is uploaded:

**Suggested action buttons:** Displayed prominently after upload, visually separated from the text input.
- "Full Review" — triggers full document review (Flow 2B)
- "Find Risks" — triggers targeted risk analysis
- "Extract Obligations" — triggers targeted obligation extraction
- "Summarize" — triggers scoped summarization
- These are shortcuts, not the only way to interact

**Free text input:** Labeled "Ask a question (fast)" to set user expectation that typing here is the cheap path. User types any question or request.

**Mode toggle pill:** Small visible toggle next to the input: `Question (fast) | Review (thorough)`
- Defaults to "Question (fast)"
- Power users can manually override to "Review" mode before typing
- Acts as a visible state indicator so the user always knows which mode is active

### Semantic Routing (how text input gets classified)
Instead of brittle keyword matching, we use **semantic routing** with the same embedding model already loaded for RAG (bge-small-en-v1.5). This is free, fast, and understands meaning, not just exact words.

**How it works:**

1. At app startup, pre-compute embeddings for example phrases per route:

```python
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('BAAI/bge-small-en-v1.5')

# Example phrases for each route — expand these over time
FULL_REVIEW_EXAMPLES = [
    "give me a full review of this contract",
    "analyze the entire document",
    "due diligence review",
    "issue spot this agreement",
    "red flag anything concerning",
    "what are the problems with this document overall",
    "comprehensive analysis of all clauses",
    "review everything and summarize the key issues",
    "is this contract enforceable overall",
    "walk me through the whole agreement",
    "run a complete risk assessment",
    "what should I be worried about in this contract",
]

TARGETED_QUESTION_EXAMPLES = [
    "what is the termination clause",
    "when does this contract expire",
    "who are the parties involved",
    "is there a non-compete provision",
    "what is the liability cap",
    "summarize section 4",
    "what are the payment terms",
    "what happens if either party breaches",
    "is there an arbitration clause",
    "what is the governing law",
]

# Pre-compute embeddings (done once at startup)
full_review_embeddings = model.encode(FULL_REVIEW_EXAMPLES, normalize_embeddings=True)
targeted_embeddings = model.encode(TARGETED_QUESTION_EXAMPLES, normalize_embeddings=True)
```

2. At query time, embed the user's input and compare:

```python
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

def detect_query_type(user_input: str, threshold: float = 0.5) -> str:
    """
    Classify user input as full_review or targeted_question
    using semantic similarity. Free — uses local embedding model.
    """
    query_embedding = model.encode(
        QUERY_PREFIX + user_input, normalize_embeddings=True
    )

    # Average similarity to each route's examples
    full_review_score = np.mean(
        query_embedding @ full_review_embeddings.T
    )
    targeted_score = np.mean(
        query_embedding @ targeted_embeddings.T
    )

    if full_review_score > targeted_score:
        return "full_review"
    return "targeted_question"
```

**Why semantic routing instead of keyword matching:**
- "Due diligence on this contract" → correctly routes to full review (keywords would miss this)
- "Issue spot this agreement" → correctly routes to full review
- "Red flag anything concerning" → correctly routes to full review
- "Is this enforceable overall" → correctly routes to full review
- "What's the liability cap in section 7" → correctly routes to targeted question
- Attorneys use domain-specific phrasing that keyword lists can't anticipate
- ~90% accuracy from embeddings alone, and misroutes are caught by the confirmation gate

**Why not use an LLM to classify?**
Users pay their own API keys (BYOK). An LLM call on every query just to classify wastes their money and adds latency. Semantic routing uses the same embedding model already loaded for RAG — zero additional cost, milliseconds to run.

**Confirmation gate (critical for BYOK):**
- If routing detects full review → show confirmation dialog BEFORE running:
  "This looks like a full-document review. Estimated: ~X pages / ~Y tokens / ~$Z.
  [Run Full Review] [Answer as a question instead]"
- If routing detects targeted question → run immediately (cheap, no confirmation needed)
- The confirmation gate catches the ~10% of misroutes, making effective accuracy ~100%
- NEVER auto-run full review without user confirmation

**Improving over time:**
- Add a "Wrong mode?" link on results so users can correct misroutes
- Log corrections and use them to expand the example phrase lists
- Track "regret signals" (user immediately reruns as full review after a targeted answer)

---

### Two Query Modes
The system handles two fundamentally different use cases with different agent configurations:

**Targeted queries** (e.g., "What's the termination clause?"):
- ALL 4 AGENTS: Research → Analysis → Draft → Fact-Check
- Research Agent converts question to vector, queries pgvector for top-k relevant chunks
- Analysis Agent examines those chunks
- Draft Agent writes the answer with citations
- Fact-Check Agent verifies citations
- Cheap, fast, standard RAG

**Full document review** (e.g., "Give me a full review of this contract"):
- DECIDED: Hybrid approach — See DECISION_FULL_REVIEW_STRATEGY.md for full research
- 3 AGENTS: Analysis → Draft → Fact-Check (Research Agent SKIPPED)
- Step 1: Count total tokens in the document
- Step 2: Show cost estimate to user, wait for confirmation
- Step 3: Choose path based on document size:
  - Under FULL_REVIEW_TOKEN_THRESHOLD (default 80000): **Single call** — send entire document to frontier model in one API call. Prompt must instruct the model to review systematically section by section.
  - Over threshold OR multi-document query: **Map-reduce** — process chunks individually (include section headers and cross-reference context in each chunk prompt), then synthesize findings via reduce step. Use multi-level reduce if summaries exceed context window.
- Step 4: Feed output (from either path) into Analysis → Draft → Fact-Check agents
- Build single call path first (simpler, handles most legal documents)

### Token Cost Estimation
Before running expensive operations (full reviews, multi-document analysis), the backend should:
- Count total tokens in relevant chunks using a tokenizer (tiktoken for OpenAI, anthropic-tokenizer for Claude)
- Determine which path will be used (single call vs map-reduce) based on threshold
- Estimate cost based on the user's selected model and provider
- Return the estimate to the frontend BEFORE executing
- Let the user confirm or cancel

### Multi-Agent System (LangGraph)
Two graph configurations depending on query type:

```
TARGETED QUESTION:
User Query --> Research Agent --> Analysis Agent --> Draft Agent --> Fact-Check Agent --> Final Output
                    ^                                                      |
                    |______________________________________________________|
                    (retry loop if fact-check finds issues, max 2 retries)

FULL DOCUMENT REVIEW:
[Single Call or Map-Reduce based on token threshold] --> Analysis Agent --> Draft Agent --> Fact-Check Agent --> Final Output
```

The LangGraph orchestrator must:
1. Detect query type (targeted question vs full review)
2. For full reviews: count tokens and select the correct path (single call vs map-reduce)
3. Route to the correct graph

Each agent:
- Has a clear, focused system prompt
- Receives structured input and returns structured output
- Logs its actions to the `agent_trace` field in the analysis record
- Has timeout handling (max 60 seconds per agent)

### MCP Server
- Runs as a separate process from the main FastAPI app
- Communicates with the backend via internal API calls
- Tools must have proper JSON schemas for inputs and outputs
- Must include authentication (API key header)
- Rate limited: 100 requests per hour per key

---

## Database Connection

```python
# Ivan's standard PostgreSQL setup on DigitalOcean
DATABASE_URL=postgresql+asyncpg://{user}:{password}@{host}:{port}/openbrief
```

pgvector must be installed on the PostgreSQL instance:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Environment Variables (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/openbrief

# Security
SECRET_KEY=<generate-a-random-key>
ENCRYPTION_KEY=<fernet-key-for-api-key-encryption>

# Entity Extraction
ENTITY_EXTRACTION_BACKEND=prompt
ENTITY_MODEL_ENDPOINT=

# Embedding
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# RAG Config
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=50
RAG_TOP_K=5

# Server
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=["http://localhost:3000"]

# MCP Server
MCP_SERVER_PORT=8001
MCP_API_KEY=<key-for-mcp-server-to-call-backend>

# Full Review Strategy
FULL_REVIEW_TOKEN_THRESHOLD=80000
```

---

## Phase-by-Phase Implementation Guide

### When starting Phase 1:
1. Initialize the project structure as defined in PROJECT_PLAN.md
2. Set up FastAPI with async SQLAlchemy and Alembic
3. Create the database schema (see PROJECT_PLAN.md for full schema)
4. Build the document ingestion pipeline: upload -> parse -> chunk -> embed -> store
5. Build a basic similarity search endpoint to test retrieval
6. Set up Next.js frontend with a simple file upload page

### When starting Phase 2:
1. Read Phase 1 code first to understand current state
2. Build the RAG query pipeline on top of existing retriever
3. Implement the BYOK system with provider abstraction
4. Integrate DeepEval for evaluation metrics
5. Build evaluation dashboard in frontend

### When starting Phase 3:
1. Read Phase 1 and 2 code first
2. Install LangChain and LangGraph
3. Build agents one at a time, test each individually before orchestrating
4. Build the LangGraph workflow connecting all four agents
5. Add frontend components for agent pipeline visualization

### When starting Phase 4:
1. This phase is mostly done in Google Colab, not on the server
2. Create training data preparation scripts
3. Write the QLoRA training script
4. Train, evaluate, and publish to Hugging Face
5. Integrate the extractor abstraction into the backend

### When starting Phase 5:
1. Read MCP SDK documentation thoroughly
2. Build MCP server as a separate module
3. Define tool schemas carefully (this is the public API)
4. Test with Claude Desktop locally before deploying

### When starting Phase 6:
1. Focus on frontend polish, error handling, documentation
2. Deploy to DigitalOcean
3. Write README and self-hosting guide
4. Record demo video

---

## Common Patterns to Follow

### API Endpoint Pattern
```python
@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Upload a legal document for analysis."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Process file...
    return DocumentResponse(...)
```

### Error Handling Pattern
```python
class OpenBriefError(Exception):
    """Base exception for OpenBrief."""

class DocumentProcessingError(OpenBriefError):
    """Raised when document processing fails."""

class RAGQueryError(OpenBriefError):
    """Raised when RAG pipeline fails."""

class LLMProviderError(OpenBriefError):
    """Raised when LLM API call fails."""
```

### Test Pattern
```python
@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient, test_user: User):
    """Test document upload creates chunks and embeddings."""
    with open("tests/fixtures/sample_contract.pdf", "rb") as f:
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            headers={"Authorization": f"Bearer {test_user.token}"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["upload_status"] == "processing"
```

---

## What NOT to Do

- Do NOT use LlamaIndex. We are using LangChain/LangGraph.
- Do NOT use Pinecone, Weaviate, Chroma, or any separate vector database. We use pgvector.
- Do NOT use Streamlit or Gradio for the frontend. We use Next.js.
- Do NOT hardcode model names. Always use environment variables or config.
- Do NOT make synchronous database calls. Always use async.
- Do NOT skip error handling to save time.
- Do NOT create placeholder endpoints that return fake data.
