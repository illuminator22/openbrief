# OpenBrief - Timeline & Milestones
## 13-Week Build Plan

---

## Pre-Build: Learning Sprint (Week 0)
**Duration:** 4-5 days before Week 1

| Day | Topic | Goal |
|-----|-------|------|
| 1 | pgvector | Install on DigitalOcean, insert/query vectors |
| 2 | Sentence Transformers | Encode text, compute similarity |
| 3 | PyMuPDF | Extract text from a sample legal PDF |
| 4-5 | LangChain basics | Build a simple retrieval chain |

---

## Phase 1: Foundation (Weeks 1-2)

### Week 1
| Day | Task |
|-----|------|
| Mon | Initialize repo, FastAPI project structure, database setup |
| Tue | Create database schema with Alembic migrations |
| Wed | Build document upload endpoint (PDF only) |
| Thu | Implement PDF parser + legal-aware chunker |
| Fri | Implement embedding generation + pgvector storage |

### Week 2
| Day | Task |
|-----|------|
| Mon | Build vector similarity search endpoint |
| Tue | Write tests for ingestion pipeline |
| Wed | Set up Next.js frontend project |
| Thu | Build file upload UI component |
| Fri | Build document list view + basic search UI |

**Milestone:** Upload a PDF, see it chunked and searchable.

---

## Phase 2: RAG Pipeline + Evaluation (Weeks 3-4)

### Learning: DeepEval (1-2 days before starting)

### Week 3
| Day | Task |
|-----|------|
| Mon | Build RAG query pipeline (retrieve -> prompt -> answer) |
| Tue | Implement BYOK system (Anthropic + OpenAI providers) |
| Wed | Add citation tracking (link answers to source chunks) |
| Thu | Integrate DeepEval for hallucination/relevance scoring |
| Fri | Create evaluation test suite (25 test cases) |

### Week 4
| Day | Task |
|-----|------|
| Mon | Expand test suite to 50+ cases |
| Tue | Build evaluation metrics API endpoints |
| Wed | Build evaluation dashboard frontend (charts, trends) |
| Thu | Tune chunk size and retrieval parameters based on eval |
| Fri | Polish RAG pipeline, fix edge cases, write tests |

**Milestone:** Ask questions about uploaded docs, get cited answers, see evaluation metrics.

---

## Phase 3: Multi-Agent System (Weeks 5-7)

### Learning: LangGraph (3-4 days before starting)

### Week 5
| Day | Task |
|-----|------|
| Mon | Set up LangGraph, build Research Agent |
| Tue | Test Research Agent with real documents |
| Wed | Build Analysis Agent |
| Thu | Test Analysis Agent, refine prompts |
| Fri | Build Draft Agent |

### Week 6
| Day | Task |
|-----|------|
| Mon | Test Draft Agent, refine output formats |
| Tue | Build Fact-Check Agent |
| Wed | Test Fact-Check Agent against known good/bad outputs |
| Thu | Build LangGraph orchestration (connect all 4 agents) |
| Fri | Add retry loop (Fact-Check -> Research if issues found) |

### Week 7
| Day | Task |
|-----|------|
| Mon | Add agent trace logging to database |
| Tue | Build frontend agent pipeline visualization |
| Wed | Add human-in-the-loop checkpoints |
| Thu | End-to-end testing with real legal documents |
| Fri | Fix bugs, optimize prompts, write tests |

**Milestone:** Upload a contract, watch 4 agents analyze it step by step, get a fact-checked report.

---

## Phase 4: QLoRA Fine-Tuning (Weeks 8-9)

### Learning: QLoRA from AI Engineering course (ongoing)

### Week 8
| Day | Task |
|-----|------|
| Mon | Source public legal documents for training data |
| Tue | Annotate training data (entity labels) |
| Wed | Continue annotation, prepare dataset splits |
| Thu | Write dataset preparation script |
| Fri | Set up Google Colab training environment |

### Week 9
| Day | Task |
|-----|------|
| Mon | Run QLoRA training, monitor loss |
| Tue | Evaluate model, compare against prompt-based extraction |
| Wed | Write model card, push to Hugging Face |
| Thu | Integrate entity extractor abstraction into backend |
| Fri | Build entity display in frontend |

**Milestone:** Fine-tuned model on Hugging Face with model card. Entity extraction working in app (using Option 3 for now).

---

## Phase 5: MCP Server (Weeks 10-11)

### Learning: MCP Python SDK (2-3 days before starting)

### Week 10
| Day | Task |
|-----|------|
| Mon | Study MCP SDK, build hello-world MCP server |
| Tue | Design tool schemas for all 7 OpenBrief tools |
| Wed | Implement analyze_contract + extract_entities tools |
| Thu | Implement summarize_document + find_obligations tools |
| Fri | Implement compare_documents + ask_question tools |

### Week 11
| Day | Task |
|-----|------|
| Mon | Implement get_evaluation_metrics tool |
| Tue | Add authentication and rate limiting |
| Wed | Test all tools with Claude Desktop |
| Thu | Fix issues found during testing |
| Fri | Write MCP server documentation |

**Milestone:** Connect Claude Desktop to OpenBrief MCP server, analyze a contract through chat.

---

## Phase 6: Polish & Launch (Weeks 12-13)

### Week 12
| Day | Task |
|-----|------|
| Mon | Frontend polish: landing page |
| Tue | Frontend polish: onboarding flow, settings page |
| Wed | Backend hardening: input validation, rate limits, logging |
| Thu | Security: API key encryption, document isolation, CORS |
| Fri | Deploy to DigitalOcean, set up domain + SSL |

### Week 13
| Day | Task |
|-----|------|
| Mon | Write README.md with screenshots |
| Tue | Write self-hosting guide + API reference |
| Wed | Record demo video (2-3 minutes) |
| Thu | Write launch posts (Reddit, HN, LinkedIn, Product Hunt) |
| Fri | LAUNCH DAY |

**Milestone:** Live at openbrief.net. Open-source on GitHub. Posts published.

---

## Post-Launch Roadmap

### Ongoing (from day 1)
- [ ] Monitor for bugs and issues
- [ ] Respond to GitHub issues
- [ ] Submit to awesome-mcp-servers lists on GitHub

### v2 - Messaging & Connectors
- [ ] Telegram bot — attorneys can query their document library via text message
- [ ] WhatsApp Business API integration — same as Telegram but on WhatsApp
- [ ] Gmail connector — pull attachments from emails, auto-ingest documents from labeled folders
- [ ] Google Drive connector — sync documents from shared firm folders
- [ ] Upgrade entity extraction to Option 1 (HF Inference Endpoint) if demand exists

### v3 - Collaboration & Expansion
- [ ] Multi-user collaboration — multiple attorneys sharing a document library
- [ ] Dropbox / OneDrive connectors
- [ ] Slack integration for legal teams sharing files
- [ ] Document comparison across versions (redline-style)
- [ ] Support for more document types (DOCX, TXT, HTML)
- [ ] Hosted paid tier (managed version for firms who don't want to self-host)

---

## Weekly Check-in Questions

Ask yourself every Friday:
1. Did I hit this week's milestone?
2. What blocked me?
3. What do I need to learn before next week?
4. Is the code tested and documented?
5. Could someone else understand my code from the docs alone?

---

## Emergency Priorities

If you're running behind schedule, here's what to cut vs what to keep:

**Never cut (core product):**
- Document ingestion + RAG pipeline (Phase 1-2)
- At least 2 agents working (Research + Analysis from Phase 3)
- Basic frontend with upload and results
- Evaluation metrics

**Can simplify:**
- Reduce to 2-3 agents instead of 4 (skip Fact-Check, merge Draft into Analysis)
- Reduce MCP tools to 3 instead of 7
- Skip dark mode
- Reduce test cases from 50 to 25

**Can delay to post-launch:**
- QLoRA fine-tuning (can launch with Option 3 only)
- Human-in-the-loop checkpoints
- Document comparison feature
- Product Hunt submission
