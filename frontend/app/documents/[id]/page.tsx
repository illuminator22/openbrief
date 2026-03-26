"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import StatusBadge from "@/components/StatusBadge";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Type definitions ---

interface LLMSettings {
  provider: string | null;
  model: string | null;
  has_key: boolean;
}

interface ModelInfo {
  id: string;
  name: string;
  description: string;
  pricing: { input: number; output: number } | null;
}

interface DocumentDetail {
  id: string;
  filename: string;
  file_size: number;
  page_count: number | null;
  upload_status: string;
  created_at: string;
  chunk_count: number;
}

interface Citation {
  excerpt_number: number;
  chunk_id: string | null;
  page_number: number | null;
  section_title: string | null;
  relevant_quote: string;
}

interface QueryResult {
  analysis_id: string;
  answer: string;
  citations: Citation[];
  confidence: string;
  insufficient_information: boolean;
  model_used: string;
  response_time_ms: number;
}

interface ChunkResult {
  chunk_id: string;
  content: string;
  section_title: string | null;
  page_number: number | null;
  chunk_index: number;
  similarity_score: number;
}

interface SearchResult {
  query: string;
  document_id: string;
  results: ChunkResult[];
}

type QueryMode = "ask" | "search";

// --- Confidence badge ---

function ConfidenceBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    high: "bg-[var(--success)]/15 text-[var(--success)]",
    medium: "bg-[var(--accent)]/15 text-[var(--accent)]",
    low: "bg-[var(--error)]/15 text-[var(--error)]",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[level] || styles.low}`}>
      {level} confidence
    </span>
  );
}

// --- Main component ---

export default function DocumentDetailPage() {
  const params = useParams();
  const documentId = params.id as string;

  // Document state
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [docLoading, setDocLoading] = useState(true);
  const [docError, setDocError] = useState("");

  // Query state
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<QueryMode>("ask");
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // LLM settings + models
  const { data: llmSettings } = useQuery<LLMSettings>({
    queryKey: ["llm-settings"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/settings/llm`);
      if (!res.ok) throw new Error("Failed to load settings");
      return res.json();
    },
  });

  const { data: modelsData } = useQuery<{ models: Record<string, ModelInfo[]> }>({
    queryKey: ["models"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/settings/models`);
      if (!res.ok) throw new Error("Failed to load models");
      return res.json();
    },
  });

  // Set default model from user settings
  useEffect(() => {
    if (llmSettings?.model && !selectedModel) {
      setSelectedModel(llmSettings.model);
    }
  }, [llmSettings, selectedModel]);

  const hasApiKey = llmSettings?.has_key === true;
  const providerModels = modelsData?.models?.[llmSettings?.provider || ""] || [];

  // Results state
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set());

  // Fetch document
  useEffect(() => {
    async function fetchDocument() {
      try {
        const res = await fetch(`${API_URL}/api/documents/${documentId}`);
        if (!res.ok) {
          throw new Error(res.status === 404 ? "Document not found" : `Error ${res.status}`);
        }
        setDocument(await res.json());
      } catch (err) {
        setDocError(err instanceof Error ? err.message : "Failed to load document");
      } finally {
        setDocLoading(false);
      }
    }
    fetchDocument();
  }, [documentId]);

  // Handle query submission
  const handleSubmit = useCallback(async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setQueryResult(null);
    setSearchResult(null);

    try {
      if (mode === "ask") {
        // RAG pipeline — calls LLM, costs money
        const body: Record<string, string> = {
          document_id: documentId,
          question: query.trim(),
        };
        if (selectedModel) body.model = selectedModel;
        const res = await fetch(`${API_URL}/api/analysis/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => null);
          throw new Error(data?.detail || `Query failed (${res.status})`);
        }
        setQueryResult(await res.json());
      } else {
        // Chunk search — vector similarity, free
        const res = await fetch(
          `${API_URL}/api/documents/${documentId}/search?q=${encodeURIComponent(query.trim())}`
        );
        if (!res.ok) {
          const data = await res.json().catch(() => null);
          throw new Error(data?.detail || `Search failed (${res.status})`);
        }
        setSearchResult(await res.json());
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [query, mode, documentId]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });

  const formatSize = (bytes: number) =>
    bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(1)} KB`
      : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

  // --- Render ---

  if (docLoading) {
    return (
      <div className="p-8">
        <p className="text-[var(--muted)]">Loading document...</p>
      </div>
    );
  }

  if (docError || !document) {
    return (
      <div className="p-8">
        <Link href="/documents" className="text-sm text-[var(--accent)] hover:underline">
          &larr; Back to Documents
        </Link>
        <div className="mt-4 rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-4">
          <p className="text-sm text-[var(--error)]">{docError || "Document not found"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl">
      <Link href="/documents" className="text-sm text-[var(--accent)] hover:underline">
        &larr; Back to Documents
      </Link>

      {/* Document info */}
      <div className="mt-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold">{document.filename}</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {document.page_count ?? "?"} pages &middot; {formatSize(document.file_size)} &middot; {document.chunk_count} chunks
            </p>
          </div>
          <StatusBadge status={document.upload_status} />
        </div>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Uploaded {formatDate(document.created_at)}
        </p>
      </div>

      {/* Query section */}
      {document.upload_status === "completed" && (
        <div className="mt-8">
          {/* Mode toggle */}
          <div className="flex items-center gap-2 mb-4">
            <button
              onClick={() => setMode("ask")}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                mode === "ask"
                  ? "bg-[var(--accent)] text-white"
                  : "bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)]"
              }`}
            >
              Ask (uses LLM)
            </button>
            <button
              onClick={() => setMode("search")}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                mode === "search"
                  ? "bg-[var(--accent)] text-white"
                  : "bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)]"
              }`}
            >
              Search (free)
            </button>
            <span className="text-xs text-[var(--muted)] ml-2">
              {mode === "ask"
                ? "AI-powered answer with citations — uses your API key"
                : "Vector similarity search — returns matching chunks, no LLM cost"}
            </span>
          </div>

          {/* Model selector (Ask mode only) */}
          {mode === "ask" && (
            <div className="mb-4">
              {hasApiKey ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[var(--muted)]">Model:</span>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="rounded-lg border border-[var(--border)] bg-[var(--input-bg)] px-3 py-1.5 text-xs text-[var(--foreground)] focus:border-[var(--accent)] focus:outline-none transition-colors"
                  >
                    {providerModels.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <p className="text-xs text-[var(--accent)]">
                  No API key configured —{" "}
                  <Link href="/settings" className="underline hover:opacity-80">
                    go to Settings
                  </Link>
                </p>
              )}
            </div>
          )}

          {/* Input */}
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              placeholder={
                mode === "ask"
                  ? "Ask a question about this document"
                  : "Search for keywords or topics"
              }
              className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--input-bg)] px-4 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:outline-none transition-colors"
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !query.trim()}
              className="rounded-lg bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (mode === "ask" ? "Thinking..." : "Searching...") : mode === "ask" ? "Ask" : "Search"}
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="mt-3 rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-3">
              <p className="text-sm text-[var(--error)]">{error}</p>
            </div>
          )}

          {/* RAG query result */}
          {queryResult && (
            <div className="mt-6 space-y-4">
              {/* Metadata bar */}
              <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
                <ConfidenceBadge level={queryResult.confidence} />
                <span>{queryResult.model_used}</span>
                <span>{(queryResult.response_time_ms / 1000).toFixed(1)}s</span>
                {queryResult.insufficient_information && (
                  <span className="text-[var(--accent)]">Insufficient information</span>
                )}
              </div>

              {/* Answer */}
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
                <p className="text-sm leading-relaxed font-content whitespace-pre-wrap">
                  {queryResult.answer}
                </p>
              </div>

              {/* Citations */}
              {queryResult.citations.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-[var(--muted)] mb-2">
                    Citations ({queryResult.citations.length})
                  </h4>
                  <div className="space-y-2">
                    {queryResult.citations.map((c, i) => (
                      <div
                        key={i}
                        className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3"
                      >
                        <div className="flex items-center gap-2 text-xs text-[var(--muted)] mb-1">
                          <span className="font-medium text-[var(--accent)]">[{c.excerpt_number}]</span>
                          {c.section_title && <span>{c.section_title}</span>}
                          {c.page_number && <span>Page {c.page_number}</span>}
                        </div>
                        <p className="text-xs leading-relaxed font-content italic">
                          &ldquo;{c.relevant_quote}&rdquo;
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Chunk search results */}
          {searchResult && (
            <div className="mt-6 space-y-3">
              <p className="text-sm text-[var(--muted)]">
                {searchResult.results.length} result{searchResult.results.length !== 1 ? "s" : ""} for &ldquo;{searchResult.query}&rdquo;
              </p>

              {searchResult.results.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">No relevant chunks found.</p>
              ) : (
                searchResult.results.map((chunk) => {
                  const isExpanded = expandedChunks.has(chunk.chunk_id);
                  const truncated = chunk.content.length > 300 && !isExpanded;
                  const displayContent = truncated
                    ? chunk.content.slice(0, 300) + "..."
                    : chunk.content;

                  return (
                    <div
                      key={chunk.chunk_id}
                      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
                          {chunk.section_title && (
                            <span className="font-medium text-[var(--foreground)]">
                              {chunk.section_title}
                            </span>
                          )}
                          {chunk.page_number && <span>Page {chunk.page_number}</span>}
                        </div>
                        <span className="text-xs font-medium text-[var(--accent)]">
                          {(chunk.similarity_score * 100).toFixed(1)}% match
                        </span>
                      </div>

                      <p className="text-sm leading-relaxed font-content whitespace-pre-wrap">
                        {displayContent}
                      </p>

                      {chunk.content.length > 300 && (
                        <button
                          onClick={() => toggleExpand(chunk.chunk_id)}
                          className="mt-2 text-xs text-[var(--accent)] hover:underline"
                        >
                          {isExpanded ? "Show less" : "Show more"}
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}

      {document.upload_status === "processing" && (
        <div className="mt-8 rounded-xl border border-[var(--accent)]/30 bg-[var(--accent)]/5 p-4">
          <p className="text-sm text-[var(--accent)]">
            This document is still being processed. Search will be available once processing is complete.
          </p>
        </div>
      )}

      {document.upload_status === "failed" && (
        <div className="mt-8 rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-4">
          <p className="text-sm text-[var(--error)]">
            Processing failed for this document. Try uploading it again.
          </p>
        </div>
      )}
    </div>
  );
}
