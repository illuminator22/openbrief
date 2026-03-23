# OpenBrief

Open-source multi-agent legal document intelligence platform.

Users upload legal documents (contracts, briefs, case filings) and a team of AI agents collaborates to analyze them — with a production RAG pipeline, transparent evaluation metrics, and BYOK (Bring Your Own Key) model access.

**Status:** Phase 1 — Foundation (project structure, database, document ingestion pipeline)

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL + pgvector
- **Frontend:** Next.js, TypeScript, Tailwind CSS *(not yet started)*
- **Embeddings:** Sentence Transformers (bge-small-en-v1.5)
- **PDF Parsing:** PyMuPDF, pdfplumber

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with the [pgvector](https://github.com/pgvector/pgvector) extension

### Setup

```bash
cd backend
cp .env.example .env
# Edit .env with your database credentials

pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn main:app --reload
```

### Health Check

```
GET http://localhost:8000/health
```

## Project Structure

```
openbrief/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Pydantic Settings (loads from .env)
│   ├── api/routes/          # API endpoints
│   ├── core/
│   │   ├── ingestion/       # PDF parsing, chunking, embedding
│   │   ├── rag/             # Retriever, pipeline, prompts
│   │   ├── agents/          # LangGraph multi-agent system
│   │   ├── extraction/      # Entity extraction (swappable backend)
│   │   └── evaluation/      # DeepEval RAG evaluation
│   ├── db/                  # SQLAlchemy models, database connection
│   └── mcp/                 # MCP server
├── frontend/                # Next.js app (not yet started)
├── training/                # QLoRA fine-tuning scripts
├── docs/                    # Architecture and setup docs
└── tests/
```

## License

[MIT](LICENSE)

## Author

Ivan Arshakyan — [BrainX Corp]
