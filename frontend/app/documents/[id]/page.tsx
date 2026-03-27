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

interface CostEstimate {
  document_id: string;
  operation: string;
  model: string;
  input_tokens: number;
  estimated_output_tokens: number;
  estimated_cost: { input_cost: number; output_cost: number; total: number } | null;
  strategy: string | null;
  threshold_tokens: number;
  pricing_available: boolean;
  message: string;
}

interface Finding {
  category: string;
  severity: string;
  title: string;
  description: string;
  section_reference: string | null;
  recommendation: string | null;
}

interface Deadline {
  description: string;
  date_or_period: string;
  section_reference: string | null;
}

interface FullReviewResult {
  analysis_id: string;
  summary: string;
  document_type: string;
  parties: string[];
  key_findings: Finding[];
  deadlines: Deadline[];
  overall_risk_assessment: string;
  confidence: string;
  model_used: string;
  strategy_used: string;
  response_time_ms: number;
  total_tokens: number;
}

type QueryMode = "ask" | "search";

// --- Helper components ---

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

function RiskBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    low: "bg-[var(--success)]/15 text-[var(--success)]",
    moderate: "bg-[var(--accent)]/15 text-[var(--accent)]",
    high: "bg-orange-500/15 text-orange-400",
    critical: "bg-[var(--error)]/15 text-[var(--error)]",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[level] || "bg-[var(--surface)] text-[var(--muted)]"}`}>
      {level} risk
    </span>
  );
}

function SeverityBorder({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    high: "border-l-red-500",
    medium: "border-l-yellow-500",
    low: "border-l-green-500",
  };
  return colors[severity] || "border-l-[var(--muted)]";
}

function CategoryBadge({ category }: { category: string }) {
  const label = category.replace(/_/g, " ");
  return (
    <span className="inline-flex items-center rounded-full bg-[var(--surface-light)] px-2 py-0.5 text-xs text-[var(--muted)]">
      {label}
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
  const [selectedModel, setSelectedModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Results state
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set());

  // Full review state
  const [showEstimate, setShowEstimate] = useState(false);
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);
  const [estimateLoading, setEstimateLoading] = useState(false);
  const [estimateModel, setEstimateModel] = useState("");
  const [reviewResult, setReviewResult] = useState<FullReviewResult | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [expandedFindings, setExpandedFindings] = useState<Set<number>>(new Set());

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

  const hasApiKey = llmSettings?.has_key === true;
  const providerModels = modelsData?.models?.[llmSettings?.provider || ""] || [];
  const allModels = Object.values(modelsData?.models || {}).flat();

  // Set default model
  useEffect(() => {
    if (llmSettings?.model && !selectedModel) {
      setSelectedModel(llmSettings.model);
      setEstimateModel(llmSettings.model);
    }
  }, [llmSettings, selectedModel]);

  // Fetch document
  useEffect(() => {
    async function fetchDocument() {
      try {
        const res = await fetch(`${API_URL}/api/documents/${documentId}`);
        if (!res.ok) throw new Error(res.status === 404 ? "Document not found" : `Error ${res.status}`);
        setDocument(await res.json());
      } catch (err) {
        setDocError(err instanceof Error ? err.message : "Failed to load document");
      } finally {
        setDocLoading(false);
      }
    }
    fetchDocument();
  }, [documentId]);

  // Fetch previous full review
  useEffect(() => {
    async function fetchPreviousReview() {
      try {
        const res = await fetch(`${API_URL}/api/analysis/document/${documentId}/latest`);
        if (res.ok) {
          const data = await res.json();
          if (data) setReviewResult(data);
        }
      } catch {
        // Silently fail — no previous review
      }
    }
    if (documentId) fetchPreviousReview();
  }, [documentId]);

  // Handle query
  const handleSubmit = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setQueryResult(null);
    setSearchResult(null);

    try {
      if (mode === "ask") {
        const body: Record<string, string> = { document_id: documentId, question: query.trim() };
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
  }, [query, mode, documentId, selectedModel]);

  // Handle full review estimate
  const handleEstimate = useCallback(async () => {
    setEstimateLoading(true);
    setShowEstimate(true);
    try {
      const res = await fetch(`${API_URL}/api/analysis/estimate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: documentId, operation: "full_review" }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Estimate failed (${res.status})`);
      }
      setEstimate(await res.json());
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Estimate failed");
      setShowEstimate(false);
    } finally {
      setEstimateLoading(false);
    }
  }, [documentId]);

  // Recalculate cost when estimate model changes
  const estimatedCost = useCallback(() => {
    if (!estimate) return null;
    const modelInfo = allModels.find((m) => m.id === estimateModel);
    if (!modelInfo?.pricing) return estimate.estimated_cost;
    const inputCost = Math.ceil(estimate.input_tokens * modelInfo.pricing.input / 1_000_000 * 100) / 100;
    const outputCost = Math.ceil(estimate.estimated_output_tokens * modelInfo.pricing.output / 1_000_000 * 100) / 100;
    return { input_cost: inputCost, output_cost: outputCost, total: Math.round((inputCost + outputCost) * 100) / 100 };
  }, [estimate, estimateModel, allModels]);

  // Handle full review run
  const handleRunReview = useCallback(async () => {
    setShowEstimate(false);
    setReviewLoading(true);
    setReviewError("");
    setReviewResult(null);
    try {
      const res = await fetch(`${API_URL}/api/analysis/full-review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: documentId }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Review failed (${res.status})`);
      }
      setReviewResult(await res.json());
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setReviewLoading(false);
    }
  }, [documentId]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const toggleFinding = useCallback((idx: number) => {
    setExpandedFindings((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
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

  // Sort findings by severity
  const sortedFindings = reviewResult?.key_findings?.slice().sort((a, b) => {
    const order: Record<string, number> = { high: 0, medium: 1, low: 2 };
    return (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
  }) || [];

  // --- Render ---

  if (docLoading) {
    return <div className="p-8"><p className="text-[var(--muted)]">Loading document...</p></div>;
  }

  if (docError || !document) {
    return (
      <div className="p-8">
        <Link href="/documents" className="text-sm text-[var(--accent)] hover:underline">&larr; Back to Documents</Link>
        <div className="mt-4 rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-4">
          <p className="text-sm text-[var(--error)]">{docError || "Document not found"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl">
      <Link href="/documents" className="text-sm text-[var(--accent)] hover:underline">&larr; Back to Documents</Link>

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
        <p className="mt-2 text-xs text-[var(--muted)]">Uploaded {formatDate(document.created_at)}</p>
      </div>

      {document.upload_status === "completed" && (
        <>
          {/* Query section — Ask/Search */}
          <div className="mt-6">
            <div className="flex items-center gap-2 mb-4">
              <button
                onClick={() => setMode("ask")}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  mode === "ask" ? "bg-[var(--accent)] text-white" : "bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                Ask (uses LLM)
              </button>
              <button
                onClick={() => setMode("search")}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  mode === "search" ? "bg-[var(--accent)] text-white" : "bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                Search (free)
              </button>
              <span className="text-xs text-[var(--muted)] ml-2">
                {mode === "ask" ? "AI-powered answer with citations" : "Vector similarity search"}
              </span>
            </div>

            {/* Model selector */}
            {mode === "ask" && (
              <div className="mb-4">
                {hasApiKey ? (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[var(--muted)]">Model:</span>
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="rounded-lg border border-[var(--border)] bg-[var(--input-bg)] px-3 py-1.5 text-xs text-[var(--foreground)] focus:border-[var(--accent)] focus:outline-none"
                    >
                      {providerModels.map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <p className="text-xs text-[var(--accent)]">
                    No API key configured — <Link href="/settings" className="underline hover:opacity-80">go to Settings</Link>
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
                placeholder={mode === "ask" ? "Ask a question about this document" : "Search for keywords or topics"}
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

            {error && (
              <div className="mt-3 rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-3">
                <p className="text-sm text-[var(--error)]">{error}</p>
              </div>
            )}

            {/* RAG query result */}
            {queryResult && (
              <div className="mt-6 space-y-4">
                <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
                  <ConfidenceBadge level={queryResult.confidence} />
                  <span>{queryResult.model_used}</span>
                  <span>{(queryResult.response_time_ms / 1000).toFixed(1)}s</span>
                  {queryResult.insufficient_information && (
                    <span className="text-[var(--accent)]">Insufficient information</span>
                  )}
                </div>
                <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
                  <p className="text-sm leading-relaxed font-content whitespace-pre-wrap">{queryResult.answer}</p>
                </div>
                {queryResult.citations.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-[var(--muted)] mb-2">Citations ({queryResult.citations.length})</h4>
                    <div className="space-y-2">
                      {queryResult.citations.map((c, i) => (
                        <div key={i} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
                          <div className="flex items-center gap-2 text-xs text-[var(--muted)] mb-1">
                            <span className="font-medium text-[var(--accent)]">[{c.excerpt_number}]</span>
                            {c.section_title && <span>{c.section_title}</span>}
                            {c.page_number && <span>Page {c.page_number}</span>}
                          </div>
                          <p className="text-xs leading-relaxed font-content italic">&ldquo;{c.relevant_quote}&rdquo;</p>
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
                  {searchResult.results.length} result{searchResult.results.length !== 1 ? "s" : ""}
                </p>
                {searchResult.results.map((chunk) => {
                  const isExpanded = expandedChunks.has(chunk.chunk_id);
                  const displayContent = chunk.content.length > 300 && !isExpanded
                    ? chunk.content.slice(0, 300) + "..." : chunk.content;
                  return (
                    <div key={chunk.chunk_id} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
                          {chunk.section_title && <span className="font-medium text-[var(--foreground)]">{chunk.section_title}</span>}
                          {chunk.page_number && <span>Page {chunk.page_number}</span>}
                        </div>
                        <span className="text-xs font-medium text-[var(--accent)]">{(chunk.similarity_score * 100).toFixed(1)}%</span>
                      </div>
                      <p className="text-sm leading-relaxed font-content whitespace-pre-wrap">{displayContent}</p>
                      {chunk.content.length > 300 && (
                        <button onClick={() => toggleExpand(chunk.chunk_id)} className="mt-2 text-xs text-[var(--accent)] hover:underline">
                          {isExpanded ? "Show less" : "Show more"}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="my-8 border-t border-[var(--border)]" />

          {/* Full Review button */}
          <div>
            <button
              onClick={handleEstimate}
              disabled={!hasApiKey || reviewLoading || estimateLoading}
              title={!hasApiKey ? "Configure your API key in Settings first" : ""}
              className="rounded-lg border border-[var(--accent)] px-5 py-2.5 text-sm font-medium text-[var(--accent)] transition-colors hover:bg-[var(--accent)]/10 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {reviewLoading ? "Running review..." : "Full Document Review"}
            </button>
            {!hasApiKey && (
              <p className="mt-1 text-xs text-[var(--accent)]">
                <Link href="/settings" className="underline">Configure your API key</Link> to run reviews.
              </p>
            )}
          </div>

          {/* Cost estimate modal */}
          {showEstimate && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
              <div className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-6 w-full max-w-md shadow-xl">
                <h3 className="text-lg font-semibold">Full Document Review</h3>
                <p className="mt-1 text-sm text-[var(--muted)]">{document.filename}</p>

                {estimateLoading ? (
                  <div className="mt-4 text-center py-6">
                    <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-[var(--muted)]/30 border-t-[var(--accent)]" />
                    <p className="mt-2 text-sm text-[var(--muted)]">Calculating estimate...</p>
                  </div>
                ) : estimate ? (
                  <div className="mt-4 space-y-4">
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-[var(--muted)]">Input tokens</span>
                        <span>{estimate.input_tokens.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--muted)]">Est. output tokens</span>
                        <span>{estimate.estimated_output_tokens.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--muted)]">Strategy</span>
                        <span>{estimate.strategy === "single_call" ? "Single call" : "Map-reduce"}</span>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs text-[var(--muted)] mb-1">Model</label>
                      <select
                        value={estimateModel}
                        onChange={(e) => setEstimateModel(e.target.value)}
                        className="w-full rounded-lg border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--accent)] focus:outline-none"
                      >
                        {allModels.map((m) => (
                          <option key={m.id} value={m.id}>{m.name}</option>
                        ))}
                      </select>
                    </div>

                    {estimatedCost() && (
                      <div className="rounded-lg bg-[var(--surface)] p-3 text-center">
                        <p className="text-2xl font-semibold">${estimatedCost()!.total.toFixed(2)}</p>
                        <p className="text-xs text-[var(--muted)]">Estimated cost</p>
                      </div>
                    )}

                    <div className="flex gap-3">
                      <button
                        onClick={handleRunReview}
                        className="flex-1 rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] active:scale-[0.98]"
                      >
                        Run Full Review
                      </button>
                      <button
                        onClick={() => setShowEstimate(false)}
                        className="flex-1 rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm font-medium text-[var(--muted)] transition-colors hover:bg-[var(--surface)]"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          )}

          {/* Review loading state */}
          {reviewLoading && (
            <div className="mt-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
              <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-[var(--muted)]/30 border-t-[var(--accent)]" />
              <p className="mt-3 text-sm">Analyzing document...</p>
              <p className="mt-1 text-xs text-[var(--muted)]">This may take 30-60 seconds.</p>
            </div>
          )}

          {/* Review error */}
          {reviewError && (
            <div className="mt-4 rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-3">
              <p className="text-sm text-[var(--error)]">{reviewError}</p>
            </div>
          )}

          {/* Full review results */}
          {reviewResult && !reviewLoading && (
            <div className="mt-6 space-y-6">
              {/* Header */}
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm font-medium">{reviewResult.document_type}</span>
                  <RiskBadge level={reviewResult.overall_risk_assessment} />
                  <ConfidenceBadge level={reviewResult.confidence} />
                  <span className="text-xs text-[var(--muted)]">{reviewResult.model_used}</span>
                </div>
                {reviewResult.parties.length > 0 && (
                  <p className="mt-2 text-xs text-[var(--muted)]">
                    Parties: {reviewResult.parties.join(", ")}
                  </p>
                )}
              </div>

              {/* Summary */}
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
                <h4 className="text-sm font-medium text-[var(--muted)] mb-2">Executive Summary</h4>
                <p className="text-sm leading-relaxed font-content whitespace-pre-wrap">{reviewResult.summary}</p>
              </div>

              {/* Key findings */}
              {sortedFindings.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-[var(--muted)] mb-3">
                    Key Findings ({sortedFindings.length})
                  </h4>
                  <div className="space-y-2">
                    {sortedFindings.map((f, i) => {
                      const isOpen = expandedFindings.has(i);
                      const borderColor = SeverityBorder({ severity: f.severity });
                      return (
                        <div
                          key={i}
                          className={`rounded-xl border border-[var(--border)] bg-[var(--surface)] border-l-4 ${borderColor} overflow-hidden`}
                        >
                          <button
                            onClick={() => toggleFinding(i)}
                            className="w-full text-left p-4 flex items-center justify-between"
                          >
                            <div className="flex items-center gap-2 flex-wrap">
                              <CategoryBadge category={f.category} />
                              <span className="text-sm font-medium">{f.title}</span>
                              {f.section_reference && (
                                <span className="text-xs text-[var(--muted)]">{f.section_reference}</span>
                              )}
                            </div>
                            <svg
                              className={`w-4 h-4 text-[var(--muted)] transition-transform ${isOpen ? "rotate-180" : ""}`}
                              fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                          {isOpen && (
                            <div className="px-4 pb-4 space-y-2">
                              <p className="text-sm leading-relaxed font-content">{f.description}</p>
                              {f.recommendation && (
                                <div className="rounded-lg bg-[var(--background)] p-3">
                                  <p className="text-xs text-[var(--muted)] mb-1">Recommendation</p>
                                  <p className="text-sm">{f.recommendation}</p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Deadlines */}
              {reviewResult.deadlines.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-[var(--muted)] mb-3">
                    Deadlines ({reviewResult.deadlines.length})
                  </h4>
                  <div className="rounded-xl border border-[var(--border)] overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-[var(--surface)] text-[var(--muted)] text-left">
                          <th className="px-4 py-2 font-medium">Description</th>
                          <th className="px-4 py-2 font-medium">Date/Period</th>
                          <th className="px-4 py-2 font-medium">Section</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reviewResult.deadlines.map((d, i) => (
                          <tr key={i} className="border-t border-[var(--border)]">
                            <td className="px-4 py-2">{d.description}</td>
                            <td className="px-4 py-2 text-[var(--accent)]">{d.date_or_period}</td>
                            <td className="px-4 py-2 text-[var(--muted)]">{d.section_reference || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

        </>
      )}

      {document.upload_status === "processing" && (
        <div className="mt-8 rounded-xl border border-[var(--accent)]/30 bg-[var(--accent)]/5 p-4">
          <p className="text-sm text-[var(--accent)]">This document is still being processed.</p>
        </div>
      )}
      {document.upload_status === "failed" && (
        <div className="mt-8 rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-4">
          <p className="text-sm text-[var(--error)]">Processing failed. Try uploading again.</p>
        </div>
      )}
    </div>
  );
}
