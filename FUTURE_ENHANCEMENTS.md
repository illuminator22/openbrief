# OpenBrief — Future Enhancements & Deferred Decisions
## Items Mentioned During Phase 1 Build (Days 1–4)

This document tracks every "do this later" or "future enhancement" mentioned during development. Review this at the end of each phase to decide what to pull forward.

---

## Database & Infrastructure

### 1. IVFFlat Index on chunks.embedding
- **When mentioned:** Day 2 (migration setup)
- **What:** Create an approximate nearest neighbor index to speed up vector searches
- **Why deferred:** IVFFlat requires existing data to build its clustering structure. Creating it on an empty table produces a useless index.
- **When to do it:** After ingesting real documents in Phase 1-2. Create a new Alembic migration.
- **Command:** `CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);`
- **Note:** `lists` should be roughly `sqrt(num_rows)`. 100 lists works for up to ~10K chunks. Adjust as data grows.

### 2. datetime.utcnow Deprecation
- **When mentioned:** Day 2 (model review)
- **What:** All models use `datetime.utcnow` for timestamps, which is deprecated in Python 3.12+
- **Why deferred:** Works fine on Python 3.10/3.11 (what the droplet runs). Not urgent.
- **When to do it:** When upgrading to Python 3.12+. Replace with `datetime.now(datetime.UTC)`.

### 3. Droplet RAM Upgrade Consideration
- **When mentioned:** Day 2 (PyTorch install)
- **What:** Upgraded from 2GB to 4GB RAM to install dependencies. Sentence Transformers + PyTorch + Uvicorn will use significant memory.
- **When to revisit:** Monitor memory usage during Phase 2 when the embedding model is loaded at startup. If the model + FastAPI + PostgreSQL connections exceed ~3GB, consider upgrading to 8GB or offloading embedding to a background worker.

---

## PDF Parsing & Chunking

### 4. pdfplumber for Table Extraction
- **When mentioned:** Day 4 (chunker design)
- **What:** PyMuPDF handles text extraction well but struggles with complex tables. pdfplumber has better table detection and extraction.
- **Why deferred:** Most legal documents are text-heavy. Tables (fee schedules, payment tables) are secondary for Phase 1.
- **When to do it:** Phase 2 or when evaluation metrics show retrieval failures on table-heavy documents.
- **Implementation:** Add a table detection step in pdf_parser.py that uses pdfplumber when tables are detected, converts them to markdown-formatted text, and inserts them into the page text.

### 5. Image-Only Page Handling (OCR)
- **When mentioned:** Day 4 (parser design)
- **What:** Pages with no extractable text (scanned documents) are skipped with a warning.
- **Why deferred:** OCR adds a heavy dependency (Tesseract) and significant complexity. Most modern legal PDFs are digital-native.
- **When to do it:** When users report issues with scanned documents. Consider pytesseract or a cloud OCR API.

### 6. Advanced Chunking Strategies
- **When mentioned:** Day 4 (chunker research)
- **What:** Several more sophisticated approaches exist:
  - **Semantic chunking:** Uses embeddings to detect topic shifts and split at meaning boundaries. More accurate but computationally expensive (requires embedding every sentence).
  - **Hierarchical chunking:** Creates multiple layers — large summary chunks and small detail chunks. Enables both broad and specific retrieval.
  - **Late chunking:** Embeds the full document first with a long-context model, then splits. Preserves cross-chunk context.
  - **Contextual retrieval:** Prepends a short document summary to each chunk so the chunk has context about the broader document.
- **Why deferred:** Recursive splitting at 512 tokens with legal-aware section boundaries is the proven baseline (validated by benchmarks showing 69% accuracy for recursive 512-token splitting). Fancier methods add complexity without guaranteed improvement.
- **When to do it:** After Phase 2 evaluation metrics are established. If retrieval precision is below 85%, try semantic chunking first. If cross-reference questions fail, try contextual retrieval (prepending summaries).

### 6.5. Merge Small Chunks Within Sections
- **When mentioned:** Day 4 (two-phase chunker design)
- **What:** The two-phase chunker splits unconditionally at every section header, then splits oversized pieces by size. This means very short sections (e.g., a 30-token "Governing Law" clause) become tiny standalone chunks. Tiny chunks have less semantic signal for cosine similarity retrieval.
- **Why deferred:** Real legal sections are rarely that short (usually 50-100+ tokens), and a correctly-labeled small chunk is far more useful than a large chunk spanning two sections with the wrong label. The tradeoff favors correctness over size optimization.
- **When to do it:** After Phase 2 evaluation metrics are established. If retrieval precision suffers on short sections, add a post-processing step in `chunk_document()` that merges consecutive sub-threshold chunks *within the same section* (never across section boundaries).

---

## Authentication & Security

### 7. Real Authentication System
- **When mentioned:** Day 3 (upload endpoint)
- **What:** Current auth is a dev placeholder that auto-creates a single dev user. Production needs JWT tokens, password hashing, user registration.
- **Why deferred:** Auth is not the core innovation of OpenBrief. Dev placeholder lets all endpoints work during development.
- **When to do it:** Phase 6 (Polish & Launch). Use python-jose for JWT and passlib for password hashing, as specified in CLAUDE_CODE_PROMPT.md.
- **File to replace:** `backend/api/routes/auth.py` — clearly marked as DEV PLACEHOLDER.

### 8. API Key Encryption at Rest
- **When mentioned:** Project plan (CLAUDE_CODE_PROMPT.md)
- **What:** User API keys (for Claude/GPT) must be encrypted using Fernet encryption before storing in the database.
- **Why deferred:** BYOK system is Phase 2.
- **When to do it:** Phase 2 when building the BYOK system. Use the `encryption_key` from config.py (already defined).

---

## Frontend

### 9. Next.js Frontend
- **When mentioned:** Day 1 (project setup)
- **What:** The frontend hasn't been started. Plan is Next.js 14+ with App Router, TypeScript strict, Tailwind CSS.
- **When to do it:** Day 8 of Phase 1 (Week 2). Start with document upload UI and document list view.

---

## RAG Pipeline

### 10. Chunk Size Tuning
- **When mentioned:** Day 4 (chunker research), Project plan (Phase 2)
- **What:** 512 tokens is the starting point based on research, but the optimal size depends on the actual documents and queries. Benchmarks show 512 is a strong default, but some legal documents may benefit from larger chunks (up to 1024).
- **When to do it:** Phase 2 after the evaluation system (DeepEval) is running. Test 256, 512, and 1024 token chunks against the same query set and compare retrieval precision.

### 11. Query Prefix Verification
- **When mentioned:** Day 2 (embeddings learning)
- **What:** BGE model uses the prefix `"Represent this sentence for searching relevant passages: "` for search queries but NOT for document chunks. This was corrected in the project docs during learning.
- **When to verify:** Day 5 when building the embedder. Double-check that `embed_chunks()` does NOT use the prefix and `embed_query()` DOES use it.

---

## Deployment & DevOps

### 12. Nginx client_max_body_size
- **When mentioned:** Day 3 (upload testing)
- **What:** Nginx defaults to 1MB max body size. We added `client_max_body_size 50M` to the /openbrief/ location block after hitting a 413 error.
- **Lesson learned:** Any Nginx config that involves file uploads needs this set explicitly. Keep it in sync with `UPLOAD_MAX_SIZE_MB` in config.py.

### 13. CORS Lockdown
- **When mentioned:** Droplet setup guide
- **What:** CORS `allow_origins` currently allows `["http://localhost:3000"]` from config. Before real users access the app, lock this to the actual frontend domain.
- **When to do it:** Phase 6 when deploying the frontend to a real domain.

### 14. Swap Space on Droplet
- **When mentioned:** Day 2 (PyTorch install failure)
- **What:** The droplet had no swap space, contributing to the OOM kill during pip install. After upgrading to 4GB RAM, this wasn't needed, but it's good practice for stability.
- **When to do it:** If any future process gets OOM-killed. Commands:
  ```bash
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab  # persist across reboots
  ```

---

## Post-Phase 1 Features (From Project Plan)

### 15. Multi-Document Queries
- **When mentioned:** DECISION_FULL_REVIEW_STRATEGY.md
- **What:** Searching across multiple uploaded documents simultaneously ("Which of my contracts expire this year?")
- **When to do it:** Phase 3 (multi-agent system). The Research Agent handles cross-document retrieval.

### 16. Token Cost Estimation
- **When mentioned:** Project plan (Phase 2)
- **What:** Before running expensive operations (full reviews), estimate API cost and show it to the user for confirmation.
- **When to do it:** Phase 2 when building the full document review pipeline.

### 17. Semantic Routing
- **When mentioned:** CLAUDE_CODE_PROMPT.md (Phase 3)
- **What:** Using bge-small-en-v1.5 embeddings to classify user queries as "targeted question" vs "full review" instead of keyword matching.
- **When to do it:** Phase 3 when building the query routing system.

---

## How to Use This Document

1. **At the end of each phase:** Review items tagged for that phase. Pull them into the work if time allows.
2. **When debugging quality issues:** Check if a deferred enhancement (chunking strategy, table extraction, OCR) would address the problem.
3. **When planning sprints:** Use this as a backlog of known improvements.
4. **Update continuously:** Every time you defer something, add it here with context on why and when.
