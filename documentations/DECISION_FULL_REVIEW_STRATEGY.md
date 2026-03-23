# OpenBrief - Decision: Full Document Review Strategy
## STATUS: DECIDED — Hybrid Approach (Option C)

---

## The Problem

When a user uploads a legal document and asks for a full review, we need to send the entire document's content to a frontier model (Claude/GPT) for analysis. The question is HOW to do this.

**Important:** This decision ONLY applies to full document reviews (Flow 2B). Targeted questions (Flow 2A) always use vector search with the embedding model to retrieve relevant chunks. That is settled and not part of this discussion.

---

## Our Thinking Process

### Initial Assumption: Map-Reduce Always

We initially planned to always use map-reduce for full document reviews:
- Read every chunk from the database one at a time
- Send each chunk individually to the frontier model ("extract key findings from this section")
- Collect all per-chunk summaries
- Send all summaries in one final call to synthesize a comprehensive review

The reasoning was that sending an entire document in one API call would be "millions of tokens" and "might not fit."

### Reality Check

Modern frontier models have massive context windows:
- Claude: 200K tokens standard, up to 1M on newer models
- GPT-4o: 128K tokens

A typical 200-page legal document is roughly 60K-80K tokens. That FITS in a single API call. Even a 500-page document (~150K-200K tokens) fits in Claude's standard context window.

So the original reasoning that "it won't fit" is not accurate for most legal documents.

### Research Findings

We researched this topic thoroughly. Here's what the evidence says:

**1. The "Lost in the Middle" problem is real.**
A Stanford/University of Washington study (Liu et al., 2024) found that LLM performance follows a U-shaped curve. Models are best at using information at the beginning or end of their input context. Performance degrades by over 30% when critical information is in the middle of long contexts. This means dumping a 200-page contract into one call risks the model missing clauses buried in the middle.

**2. But map-reduce has its own failure mode.**
RAG/map-reduce optimizes for precision (finding the smallest useful subset). Long context optimizes for completeness (giving the model broader visibility). Map-reduce fails when processing chunks individually misses cross-references between sections. Long context fails when the model sees too much and loses focus.

**3. Legal documents specifically need cross-referencing.**
Contracts constantly reference other sections ("as defined in Section 3.2", "subject to Article 7"). Processing chunks individually in map-reduce misses these cross-references entirely because chunk 5 and chunk 180 are processed in separate API calls.

**4. The cost difference is massive.**
One benchmark found RAG queries cost 1,250x less than sending everything to the model. For OpenBrief where users pay their own API costs (BYOK), this matters a lot.

**5. The 2026 industry consensus is hybrid.**
Production systems route cost-sensitive queries through RAG while reserving long-context processing for tasks requiring full corpus analysis. Neither approach alone is optimal.

### How Claude Code Handles This (Relevant Analogy)

Claude Code faces the same problem: a user asks it to understand a codebase with 10,000+ lines of code. How does it handle it?

- It does NOT read everything in one shot
- It reads the directory structure first
- It selectively reads key files (entry points, configs, READMEs)
- It pulls in specific files only as needed
- When context gets too long, it compacts/summarizes older content to make room
- It's essentially doing map-reduce automatically behind the scenes

This suggests that the map-reduce pattern is the standard approach for handling large content. But Claude Code is interactive and can decide what to read next. Our full review pipeline is a batch operation, which is different.

---

## Decision: Hybrid Approach

### Small documents (under ~80K tokens, roughly 100-120 pages):
**Single call.** Send the entire document to the frontier model in one API call.

Why:
- Model sees the FULL document and can cross-reference sections
- Legal contracts reference other clauses constantly, single call handles this naturally
- Simpler code path, one API call
- Most legal documents (contracts, briefs, filings) fall under this threshold
- Quality is better because the model has complete context

Risk:
- "Lost in the middle" may cause the model to miss some details in the center of the document
- Higher per-call cost than map-reduce (but simpler, and the user sees an estimate before confirming)

Mitigation:
- Prompt engineering: instruct the model to be thorough and systematic, processing the document section by section
- Have the Fact-Check Agent verify key findings against source text afterward

### Large documents (over ~80K tokens) or multi-document queries:
**Map-reduce.** Process chunks individually, then synthesize.

Why:
- Documents this size may not fit in all model context windows (especially OpenAI's 128K limit)
- Even if they fit, "lost in the middle" degrades quality significantly at this scale
- Multi-document queries (e.g., "review all my contracts") can't fit in any context window
- Map-reduce handles any scale

Implementation details:
- Map step: process each chunk individually, extract key findings
- Include section headers and reference context in each chunk prompt so the model knows what other sections are being referenced
- Reduce step: if too many summaries to fit, do multi-level reduce (summarize batches first)
- Final reduce: combine all findings into structured output for the agents
- Skip boilerplate chunks (signature pages, standard definitions) when possible

### The threshold (~80K tokens):
- This is a starting point based on research, not a final number
- Should be configurable via environment variable: FULL_REVIEW_TOKEN_THRESHOLD=80000
- Must be tested with real legal documents during Phase 3
- Adjust based on evaluation metrics comparing quality of both approaches
- Consider that different models have different sweet spots (Claude handles longer context better than GPT-4o)

---

## What This Means for the Agent Flow

For both paths (single call and map-reduce), the same 3 agents run afterward:

```
[Single Call OR Map-Reduce output]
        |
        v
  [Analysis Agent]
        |-- Identifies patterns, contradictions, key risks,
        |   missing clauses, unusual terms
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
```

The only difference is what feeds INTO the Analysis Agent:
- Single call: the frontier model's full analysis of the entire document
- Map-reduce: synthesized findings from all chunks

Research Agent is skipped in both cases since we already have the full document content.

---

## Token Cost Estimation (applies to both paths)

Before running ANY full review, the backend must:
1. Count total tokens in the document
2. Determine which path will be used (single call vs map-reduce based on threshold)
3. Estimate API cost based on the user's selected provider and model
4. Return the estimate to the frontend
5. Wait for user confirmation before proceeding

The frontend shows something like:
"Full review of this 95-page contract (~62,000 tokens). Estimated cost: ~$0.50 with Claude Sonnet. Proceed?"

---

## Implementation Order

1. Build single call path first (simpler, handles most documents)
2. Test with real legal documents of varying sizes
3. Build map-reduce path for large documents
4. Test both paths, compare quality and cost
5. Tune the threshold based on real results
6. Both paths feed into the same Analysis -> Draft -> Fact-Check agent pipeline

---

## Environment Variables

```env
# Full review strategy
FULL_REVIEW_TOKEN_THRESHOLD=80000
# Can be overridden per-model if needed
FULL_REVIEW_TOKEN_THRESHOLD_CLAUDE=100000
FULL_REVIEW_TOKEN_THRESHOLD_OPENAI=80000
```

---

## References

- "Lost in the Middle: How Language Models Use Long Contexts" (Liu et al., 2024) — Stanford/UW research on positional bias in long context
- Databricks blog: "Long Context RAG Performance of LLMs" — benchmarks on quality degradation
- Elasticsearch Labs: "RAG vs Long Context Model LLM" — cost comparison (1,250x cheaper for RAG)
- RAGFlow: "From RAG to Context" — 2025 year-end review on hybrid approaches
- This decision affects Flow 2B in PROJECT_PLAN.md architecture diagram
- This decision affects the "Two Query Modes" section in CLAUDE_CODE_PROMPT.md
