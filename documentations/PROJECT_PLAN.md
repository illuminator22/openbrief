# OpenBrief - Project Plan
## Open-Source Multi-Agent Legal Document Intelligence Platform

**Author:** Ivan Arshakyan (BrainX Corp)
**Created:** March 2026
**Status:** Planning Phase

---

## Vision

OpenBrief is an open-source, full-stack legal document intelligence platform. Users upload legal documents (contracts, briefs, case filings) and a team of specialized AI agents collaborates to analyze them. The platform features a production RAG pipeline with transparent evaluation metrics, multi-agent orchestration, a QLoRA fine-tuned entity extraction model, and an MCP server that lets any AI assistant (Claude, ChatGPT) plug into OpenBrief as a tool.

**Target users:** Solo attorneys, small law firms, legal researchers, paralegals, and law students who cannot afford enterprise tools like Harvey ($$$) or CoCounsel.

**Business model:** Open-source core (free, BYOK API keys) + future hosted version (paid).

---

## What Makes This Unique

1. **Open-source** - Harvey, CoCounsel, Spellbook are all closed and expensive. OpenBrief is the indie/open alternative.
2. **MCP Server** - No legal AI tool exposes an MCP server. Any Claude or ChatGPT user can connect to OpenBrief directly from their AI assistant.
3. **Transparent evaluation** - Public hallucination rate tracking and retrieval quality metrics. Legal AI tools hide this behind sales calls.
4. **Model-agnostic** - BYOK (Bring Your Own Key). Supports Claude, GPT, and other providers. Users choose which model they trust with their confidential documents.
5. **Custom fine-tuned model** - QLoRA fine-tuned model for legal entity extraction, published on Hugging Face with full documentation.

---

## Tech Stack

### Backend
- **Python 3.11+** - Primary language
- **FastAPI** - REST API framework (Ivan already proficient)
- **PostgreSQL + pgvector** - Database + vector similarity search
- **LangChain + LangGraph** - Agent orchestration framework
- **Sentence Transformers** - Document embedding generation
- **DeepEval** - RAG evaluation framework
- **Hugging Face Transformers + PEFT** - QLoRA fine-tuning
- **MCP Python SDK** - Model Context Protocol server

### Frontend
- **Next.js (TypeScript)** - React-based frontend framework (Ivan has Cadence experience)
- **Tailwind CSS** - Styling
- **Recharts or Chart.js** - Evaluation metrics dashboard

### Infrastructure
- **DigitalOcean** - Production hosting (Ivan already has server)
- **Google Colab** - GPU for model training (free tier)
- **Hugging Face** - Model hosting and (eventually) inference endpoint
- **GitHub** - Open-source repository

---

## Architecture Overview

```
=== FLOW 1: DOCUMENT UPLOAD (automatic, runs once per document) ===

User uploads document
        |
        v
  [Next.js Frontend]
        |
        v
  [FastAPI Backend]
        |
        v
  [Document Ingestion Pipeline]
        |-- PDF parsing (PyMuPDF / pdfplumber)
        |-- Legal-aware chunking (respects section boundaries)
        |-- Embedding generation (bge-small-en-v1.5)
        |-- Store chunks + embeddings in PostgreSQL + pgvector
        |
        v
  [Entity Extraction] ← THIS IS WHERE OUR FINE-TUNED MODEL RUNS
        |-- Scans each chunk for: party names, dates, jurisdictions,
        |   obligations, monetary amounts, deadlines, governing law
        |-- Testing phase: Frontier model prompt (Option 3, free)
        |-- Production phase: HF Inference Endpoint (Option 1, ~$40-90/mo)
        |-- Results stored in entities table
        |
        v
  Document ready. User sees extracted entities immediately.


=== FLOW 2A: TARGETED QUESTION (e.g., "What's the termination clause?") ===

User asks a specific question
        |
        v
  [Token Cost Estimation] → cheap, proceed directly
        |
        v
  [Research Agent]
        |-- Converts question to vector (bge-small-en-v1.5 + query prefix)
        |-- Queries pgvector for top-k most relevant chunks
        |-- Returns relevant chunks with metadata
        |
        v
  [Analysis Agent] ← POWERED BY FRONTIER MODEL (Claude/GPT)
        |-- Analyzes retrieved chunks for arguments, risks, obligations
        |
        v
  [Draft Agent]
        |-- Generates answer/report with citations to source chunks
        |
        v
  [Fact-Check Agent]
        |-- Verifies every citation exists in the source document
        |-- If issues found, loops back to Research Agent (max 2 retries)
        |
        v
  Final output with citations + confidence score

  ALL 4 AGENTS USED: Research → Analysis → Draft → Fact-Check


=== FLOW 2B: FULL DOCUMENT REVIEW (e.g., "Give me a full review") ===

  DECIDED: Hybrid Approach — See DECISION_FULL_REVIEW_STRATEGY.md for full research

User requests full document review
        |
        v
  [Token Cost Estimation]
        |-- Count total tokens in document
        |-- Show estimate to user, wait for confirmation
        |
        v
  [Size Detection] → Is document under ~80K tokens?
        |
        |-- YES (most legal docs): SINGLE CALL
        |   Send entire document to frontier model in one API call.
        |   Model sees full context, can cross-reference sections.
        |   Prompt instructs model to review systematically section by section.
        |
        |-- NO (very large docs or multi-document): MAP-REDUCE
        |   Map: process each chunk individually, extract key findings.
        |   Include section headers and reference context per chunk.
        |   Reduce: synthesize all chunk findings into structured output.
        |   Multi-level reduce if too many summaries for one call.
        |
        v
  [Analysis Agent] ← POWERED BY FRONTIER MODEL (Claude/GPT)
        |-- Takes full review output (from either path)
        |-- Identifies patterns, contradictions, key risks,
        |   missing clauses, unusual terms across the whole document
        |
        v
  [Draft Agent]
        |-- Generates comprehensive review report with citations
        |
        v
  [Fact-Check Agent]
        |-- Verifies citations against source chunks
        |
        v
  Final comprehensive review with citations + confidence score

  3 AGENTS USED: Analysis → Draft → Fact-Check
  (Research Agent skipped — we already have the full document content)
  Threshold configurable: FULL_REVIEW_TOKEN_THRESHOLD=80000


=== FLOW 3: MCP SERVER (external access) ===

  [MCP Server]
        |-- Exposes OpenBrief capabilities as MCP tools
        |-- Any Claude/ChatGPT user can connect and analyze docs
        |-- Tools: analyze_contract, extract_entities, summarize_brief,
        |   find_obligations, compare_documents
        |-- Calls the same backend APIs as the web frontend

```

**Key distinction:**
- Flow 1 (upload) uses the **fine-tuned model** for entity extraction. Runs once per document, automatically.
- Flow 2A (targeted questions) uses **Research Agent + pgvector** to find relevant chunks, then 3 agents analyze them. Cheap and fast.
- Flow 2B (full reviews) uses a **hybrid approach**: single call for small docs (under ~80K tokens), map-reduce for large docs or multi-document queries. Then 3 agents analyze the results. See DECISION_FULL_REVIEW_STRATEGY.md.
- Flow 3 (MCP) is just another entry point into the same backend as Flow 2A/2B.

---

## Phase Breakdown

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Project setup, database, document ingestion pipeline

- [ ] Initialize GitHub repository with proper structure
- [ ] Set up FastAPI project with project structure
- [ ] Set up PostgreSQL with pgvector extension on DigitalOcean
- [ ] Build document upload API endpoint (PDF support)
- [ ] Implement PDF parsing with PyMuPDF and pdfplumber
- [ ] Build legal-aware document chunking system
  - Respect section headers, clause boundaries, paragraph breaks
  - Include metadata: section title, page number, document name
  - Configurable chunk size with overlap
- [ ] Implement embedding generation using Sentence Transformers
  - Model: bge-small-en-v1.5 (384 dimensions, 512 token max sequence length)
  - IMPORTANT: When encoding search queries, prepend "Represent this sentence for searching relevant passages: " prefix
  - When encoding document chunks, do NOT use the prefix
- [ ] Store embeddings in pgvector with metadata
- [ ] Build basic vector similarity search endpoint
- [ ] Write tests for ingestion pipeline
- [ ] Set up Next.js frontend with file upload UI

**Deliverables:**
- Working document upload and ingestion
- Vector search returning relevant chunks
- Basic frontend with upload functionality

---

### Phase 2: RAG Pipeline + Evaluation (Weeks 3-4)
**Goal:** Production RAG pipeline with evaluation metrics

- [ ] Build RAG query pipeline
  - Accept user question
  - Retrieve top-k relevant chunks from pgvector
  - Construct prompt with retrieved context
  - Call frontier model API (Claude/GPT via BYOK key)
  - Return answer with source citations (chunk references)
- [ ] Build full document review pipeline (hybrid approach — see DECISION_FULL_REVIEW_STRATEGY.md)
  - Build single call path first (handles most legal documents under ~80K tokens)
  - Build map-reduce path for large documents and multi-document queries
  - Implement token counting and automatic path selection based on threshold
  - Threshold configurable via FULL_REVIEW_TOKEN_THRESHOLD env variable
- [ ] Build token cost estimation system
  - Count tokens in relevant chunks before running expensive operations
  - Estimate API cost based on user's selected provider and model
  - Return estimate to frontend before executing (user confirms or cancels)
  - Show estimate on full reviews and multi-document queries
- [ ] Implement BYOK (Bring Your Own Key) system
  - Support Claude API key
  - Support OpenAI API key
  - Configurable model selection
  - Secure key storage (encrypted, never logged)
- [ ] Build evaluation system with DeepEval
  - Hallucination rate: does the answer contain info NOT in the retrieved chunks?
  - Retrieval precision: are the retrieved chunks actually relevant?
  - Citation accuracy: do the cited sources actually support the claims?
  - Answer relevance: does the answer address the question?
- [ ] Create evaluation test suite
  - Minimum 50 test cases with known correct answers
  - Track metrics over time
  - CI integration: fail if hallucination rate exceeds threshold
- [ ] Build evaluation dashboard in frontend
  - Real-time metrics display
  - Historical trend charts
  - Per-query breakdown
- [ ] Optimize chunk size and retrieval parameters based on eval results

**Deliverables:**
- Working RAG pipeline with citations
- BYOK system supporting Claude and OpenAI
- Evaluation dashboard showing live metrics
- Test suite with 50+ cases

---

### Phase 3: Multi-Agent System (Weeks 5-7)
**Goal:** Specialized AI agents working together via LangGraph

- [ ] Set up LangGraph orchestration framework
- [ ] Build query routing system
  - Suggested action buttons shown after document upload: "Full Review", "Find Risks", "Extract Obligations", "Summarize"
  - Buttons visually separated from the chat input to prevent accidental expensive actions
  - Free text input labeled "Ask a question (fast)" to set cheap-path expectation
  - Mode toggle pill next to input: "Question (fast) | Review (thorough)" for power user override
  - Semantic routing using bge-small-en-v1.5 (same model already loaded for RAG, zero cost)
    - Pre-compute embeddings for example phrases per route at app startup
    - At query time, embed user input and compare similarity to each route's examples
    - ~90% accuracy, misroutes caught by confirmation gate
  - Confirmation gate: if full review detected, show cost/token estimate dialog before running
  - NEVER auto-run full review without user confirmation
  - "Wrong mode?" feedback link on results to improve routing over time
- [ ] Build Research Agent
  - Takes a legal question or analysis request
  - Queries the RAG pipeline for relevant document chunks
  - Returns structured set of relevant passages with metadata
  - Handles multi-document research (cross-reference between uploads)
- [ ] Build Analysis Agent
  - Receives retrieved passages from Research Agent
  - Identifies: key arguments, legal risks, obligations, rights, conditions
  - Structures output into categorized findings
  - Flags ambiguous or contradictory clauses
- [ ] Build Draft Agent
  - Takes analysis results and generates human-readable output
  - Produces: executive summaries, clause-by-clause breakdowns, risk reports
  - Includes proper citations to source documents
  - Adapts output format based on request (summary vs detailed vs brief)
- [ ] Build Fact-Check Agent
  - Reviews Draft Agent output
  - Verifies every citation actually exists in the source documents
  - Checks that quoted/referenced text matches the original
  - Flags unsupported claims
  - Returns confidence score for the overall output
- [ ] Build orchestration graph in LangGraph
  - Define agent communication flow
  - Handle errors and retries at each step
  - Implement human-in-the-loop checkpoints for high-stakes outputs
- [ ] Build frontend views for agent workflow
  - Show agent pipeline progress in real-time
  - Display each agent's output step by step
  - Allow user to intervene/redirect at checkpoints

**Deliverables:**
- Four working agents orchestrated by LangGraph
- End-to-end analysis pipeline: upload doc -> get structured analysis
- Frontend showing agent workflow in real-time
- Fact-checked outputs with confidence scores

---

### Phase 4: QLoRA Fine-Tuning (Weeks 8-9)
**Goal:** Train and publish custom legal entity extraction model

- [ ] Prepare training dataset
  - Source: publicly available legal documents (court filings, SEC filings, open contracts)
  - Entity types: party names, dates, jurisdictions, obligations, monetary amounts, deadlines, governing law
  - Format: instruction-tuning format (input: text passage, output: structured entities)
  - Minimum 1,000 annotated examples
  - Split: 80% train, 10% validation, 10% test
- [ ] Set up training environment
  - Google Colab (free GPU tier) or RunPod if needed
  - Install: transformers, peft, bitsandbytes, datasets, trl
- [ ] Fine-tune model using QLoRA
  - Base model: Llama 3 8B or Mistral 7B (whichever performs better on validation)
  - QLoRA config: 4-bit quantization, LoRA rank 16-64
  - Training: 3-5 epochs, evaluate on validation set each epoch
  - Track loss, entity-level F1 score, exact match accuracy
- [ ] Evaluate model performance
  - Compare against frontier model prompt-based extraction (Option 3 baseline)
  - Document precision, recall, F1 for each entity type
  - Create confusion matrix and error analysis
- [ ] Publish model to Hugging Face
  - Full model card with: training data description, methodology, metrics, limitations
  - Include example usage code
  - License: Apache 2.0 or MIT
- [ ] Integrate into OpenBrief
  - During testing: use frontier model prompt (Option 3)
  - Architecture ready to swap to HF Inference Endpoint (Option 1) later
  - Entity extraction results displayed in frontend

**Deliverables:**
- Fine-tuned model published on Hugging Face with full documentation
- Evaluation report comparing fine-tuned vs prompt-based extraction
- Entity extraction integrated into the app
- Model card showing training methodology and metrics

---

### Phase 5: MCP Server (Weeks 10-11)
**Goal:** Expose OpenBrief as an MCP server any AI assistant can connect to

- [ ] Install MCP Python SDK
- [ ] Design MCP tool interface
  - `analyze_contract`: Upload and analyze a contract, returns structured findings
  - `extract_entities`: Extract legal entities from a document
  - `summarize_document`: Generate executive summary of a legal document
  - `find_obligations`: List all obligations and deadlines in a contract
  - `compare_documents`: Compare two legal documents and highlight differences
  - `ask_question`: Ask a natural language question about uploaded documents
  - `get_evaluation_metrics`: Return current RAG pipeline accuracy metrics
- [ ] Implement MCP server
  - Register tools with proper schemas (typed inputs and outputs)
  - Handle document upload via MCP resources
  - Authentication: API key based
  - Rate limiting to prevent abuse
- [ ] Test with Claude Desktop
  - Connect Claude Desktop to local MCP server
  - Test each tool end-to-end
  - Document setup instructions
- [ ] Test with other MCP-compatible clients
- [ ] Write MCP server documentation
  - Installation guide
  - Configuration options
  - Tool descriptions with examples
  - Security considerations

**Deliverables:**
- Working MCP server with 7 tools
- Tested with Claude Desktop
- Complete documentation for connecting
- Rate limiting and authentication

---

### Phase 6: Polish and Launch (Weeks 12-13)
**Goal:** Production-ready deployment and public launch

- [ ] Frontend polish
  - Landing page explaining what OpenBrief does
  - Clean onboarding flow (enter API key, upload first document)
  - Responsive design
  - Dark mode support
  - Loading states and error handling
- [ ] Backend hardening
  - Input validation on all endpoints
  - Rate limiting
  - Error handling and logging
  - API documentation (auto-generated OpenAPI/Swagger)
- [ ] Security
  - API key encryption at rest
  - Document isolation (users can only access their own documents)
  - No document data logged or stored beyond user's session (configurable)
  - CORS configuration
- [ ] Deployment
  - Deploy to DigitalOcean
  - Set up domain (openbrief.net)
  - SSL certificate
  - Basic monitoring and alerting
- [ ] Documentation
  - README.md with project overview, screenshots, quick start
  - CONTRIBUTING.md for open-source contributors
  - Architecture docs
  - API reference
  - Self-hosting guide
- [ ] Launch prep
  - Record demo video (2-3 minutes)
  - Write launch post for Reddit (r/opensource, r/legaltech, r/MachineLearning)
  - Post on Hacker News
  - LinkedIn post
  - Product Hunt submission
  - GitHub repo: proper tags, description, social preview image

**Deliverables:**
- Live production deployment
- Complete documentation
- Demo video
- Launch posts drafted

---

## File Structure

```
openbrief/
|-- README.md
|-- CONTRIBUTING.md
|-- LICENSE (MIT or Apache 2.0)
|-- .env.example
|-- docker-compose.yml (for self-hosting)
|
|-- backend/
|   |-- main.py                     # FastAPI app entry point
|   |-- config.py                   # Environment config, BYOK settings
|   |-- requirements.txt
|   |
|   |-- api/
|   |   |-- routes/
|   |   |   |-- documents.py        # Upload, list, delete documents
|   |   |   |-- analysis.py         # Trigger analysis, get results
|   |   |   |-- entities.py         # Entity extraction endpoints
|   |   |   |-- evaluation.py       # Evaluation metrics endpoints
|   |   |   |-- auth.py             # API key management
|   |   |
|   |   |-- middleware/
|   |       |-- rate_limit.py
|   |       |-- auth.py
|   |
|   |-- core/
|   |   |-- ingestion/
|   |   |   |-- pdf_parser.py       # PDF text extraction
|   |   |   |-- chunker.py          # Legal-aware document chunking
|   |   |   |-- embedder.py         # Sentence transformer embeddings
|   |   |
|   |   |-- rag/
|   |   |   |-- retriever.py        # pgvector similarity search
|   |   |   |-- pipeline.py         # Full RAG query pipeline
|   |   |   |-- prompts.py          # Prompt templates
|   |   |
|   |   |-- agents/
|   |   |   |-- orchestrator.py     # LangGraph workflow definition
|   |   |   |-- research_agent.py   # Document research agent
|   |   |   |-- analysis_agent.py   # Legal analysis agent
|   |   |   |-- draft_agent.py      # Summary/brief generation agent
|   |   |   |-- factcheck_agent.py  # Citation verification agent
|   |   |
|   |   |-- extraction/
|   |   |   |-- entity_extractor.py # Entity extraction (swappable backend)
|   |   |   |-- prompt_extractor.py # Option 3: frontier model prompt
|   |   |   |-- model_extractor.py  # Option 1: fine-tuned model endpoint
|   |   |
|   |   |-- evaluation/
|   |       |-- evaluator.py        # DeepEval integration
|   |       |-- metrics.py          # Custom metric definitions
|   |       |-- test_cases.py       # Evaluation test suite
|   |
|   |-- db/
|   |   |-- database.py             # PostgreSQL connection
|   |   |-- models.py               # SQLAlchemy models
|   |   |-- migrations/             # Alembic migrations
|   |
|   |-- mcp/
|       |-- server.py               # MCP server implementation
|       |-- tools.py                # MCP tool definitions
|       |-- config.py               # MCP server configuration
|
|-- frontend/
|   |-- package.json
|   |-- next.config.js
|   |-- tailwind.config.js
|   |
|   |-- app/
|   |   |-- page.tsx                # Landing page
|   |   |-- dashboard/
|   |   |   |-- page.tsx            # Main dashboard
|   |   |-- documents/
|   |   |   |-- page.tsx            # Document management
|   |   |   |-- [id]/
|   |   |       |-- page.tsx        # Single document analysis view
|   |   |-- evaluation/
|   |   |   |-- page.tsx            # Evaluation metrics dashboard
|   |   |-- settings/
|   |       |-- page.tsx            # API key configuration
|   |
|   |-- components/
|       |-- DocumentUpload.tsx
|       |-- SuggestedActions.tsx    # "Full Review", "Find Risks", "Extract Obligations", "Summarize" buttons
|       |-- QueryInput.tsx          # Free text input labeled "Ask a question (fast)" with mode toggle pill
|       |-- CostEstimate.tsx        # Token cost estimation confirmation dialog (confirm/cancel)
|       |-- AnalysisView.tsx
|       |-- AgentPipeline.tsx       # Real-time agent workflow display
|       |-- EntityTable.tsx
|       |-- EvaluationCharts.tsx
|       |-- ApiKeyForm.tsx
|
|-- training/
|   |-- README.md                   # Training documentation
|   |-- prepare_dataset.py          # Dataset preparation script
|   |-- train_qlora.py              # QLoRA training script
|   |-- evaluate_model.py           # Model evaluation script
|   |-- push_to_hub.py              # Push to Hugging Face script
|   |-- data/
|       |-- raw/                    # Raw legal documents
|       |-- processed/              # Processed training data
|       |-- test/                   # Evaluation test set
|
|-- docs/
|   |-- architecture.md
|   |-- self-hosting.md
|   |-- mcp-setup.md
|   |-- api-reference.md
|   |-- evaluation-methodology.md
|
|-- tests/
    |-- test_ingestion.py
    |-- test_rag.py
    |-- test_agents.py
    |-- test_extraction.py
    |-- test_mcp.py
```

---

## Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users (for multi-tenant support)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    api_key_hash VARCHAR(255),
    llm_provider VARCHAR(50) DEFAULT 'anthropic',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Uploaded documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_size INTEGER,
    page_count INTEGER,
    upload_status VARCHAR(50) DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Document chunks with embeddings
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    section_title VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Analysis results
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    analysis_type VARCHAR(100) NOT NULL,
    query TEXT,
    result JSONB NOT NULL,
    agent_trace JSONB,
    confidence_score NUMERIC(4,3),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Extracted entities
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    entity_type VARCHAR(100) NOT NULL,
    entity_value TEXT NOT NULL,
    page_number INTEGER,
    chunk_id UUID REFERENCES chunks(id),
    confidence NUMERIC(4,3),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Evaluation metrics log
CREATE TABLE evaluation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    retrieved_chunks JSONB,
    generated_answer TEXT,
    hallucination_score NUMERIC(4,3),
    retrieval_precision NUMERIC(4,3),
    citation_accuracy NUMERIC(4,3),
    answer_relevance NUMERIC(4,3),
    response_time_ms INTEGER,
    model_used VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Learning Path (Before Starting Phase 1)

These should be learned in order. Spend 2-3 days on each before starting the build.

1. **pgvector basics** - How vector similarity search works, how to set up pgvector in PostgreSQL. Ivan already knows PostgreSQL so this is a natural extension.
2. **Sentence Transformers** - How text embeddings work, how to generate them. Simple Python library, quick to learn.
3. **LangChain fundamentals** - Chains, prompts, retrievers. Don't go deep yet, just understand the building blocks.
4. **LangGraph** - Graph-based agent orchestration. This builds on LangChain. Focus on understanding nodes, edges, and state.
5. **DeepEval** - RAG evaluation. How to measure hallucination, retrieval quality, etc.
6. **QLoRA with PEFT** - Ivan's AI engineering course covers this. Apply it specifically to a legal NER task.
7. **MCP Python SDK** - How to build an MCP server. Read the official docs and reference implementations on GitHub.

---

## Key Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary language | Python | AI/ML ecosystem, FastAPI experience |
| Frontend | Next.js (TypeScript) | Cadence experience, good for SEO landing page |
| Database | PostgreSQL + pgvector | Already know PostgreSQL, pgvector avoids separate vector DB |
| Agent framework | LangGraph | Production-ready, graph-based, better than CrewAI for custom control |
| Embedding model | bge-small-en-v1.5 | 384 dimensions, 512 token max sequence (matches chunk size), better retrieval benchmarks. Requires query prefix for search queries. |
| Fine-tune base | Llama 3 8B or Mistral 7B | Small enough for free Colab, strong performance |
| Fine-tune method | QLoRA (4-bit) | Fits on free Colab GPU, matches course curriculum |
| Entity extraction (dev) | Frontier model prompt (Option 3) | Free during development |
| Entity extraction (prod) | HF Inference Endpoint (Option 1) | Switch when ready to launch |
| Hosting | DigitalOcean | Already have server, familiar setup |
| Model hosting | Hugging Face | Industry standard, free model publishing |
| License | MIT | Maximum adoption for open-source |
| API key model | BYOK | Zero cost to Ivan, user controls data privacy |

---

## Success Metrics

- [ ] RAG hallucination rate below 5%
- [ ] Retrieval precision above 85%
- [ ] Citation accuracy above 90%
- [ ] Sub-3 second response time for single document queries
- [ ] Fine-tuned model entity extraction F1 above 85%
- [ ] MCP server working with Claude Desktop
- [ ] At least 10 GitHub stars within first month
- [ ] At least one law firm or attorney using the platform
- [ ] Complete documentation for self-hosting
- [ ] Demo video under 3 minutes

---

## Resume Impact

After completing this project, Ivan's resume would include:

**OpenBrief** - Open-Source Legal Document Intelligence Platform
- Architected and launched an open-source multi-agent legal AI platform with a production RAG pipeline, achieving under 5% hallucination rate across 50+ evaluated test cases
- Built four specialized AI agents (Research, Analysis, Draft, Fact-Check) orchestrated via LangGraph for end-to-end legal document analysis with real-time pipeline visibility
- Fine-tuned a Llama 3 model using QLoRA for legal entity extraction, published on Hugging Face with full evaluation metrics and model documentation
- Developed an MCP server enabling any Claude or ChatGPT user to connect and analyze legal documents directly from their AI assistant
- Built transparent evaluation dashboard tracking hallucination rates, retrieval precision, and citation accuracy in real-time

This single project demonstrates: full-stack engineering, RAG pipelines, multi-agent orchestration, model fine-tuning, MCP protocol, evaluation methodology, open-source leadership, and production deployment.
