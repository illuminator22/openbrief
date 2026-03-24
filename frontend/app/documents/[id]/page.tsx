"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import StatusBadge from "@/components/StatusBadge";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DocumentDetail {
  id: string;
  filename: string;
  file_size: number;
  page_count: number | null;
  upload_status: string;
  created_at: string;
  chunk_count: number;
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

export default function DocumentDetailPage() {
  const params = useParams();
  const documentId = params.id as string;

  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [docLoading, setDocLoading] = useState(true);
  const [docError, setDocError] = useState("");

  const [query, setQuery] = useState("");
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set());

  useEffect(() => {
    async function fetchDocument() {
      try {
        const res = await fetch(`${API_URL}/api/documents/${documentId}`);
        if (!res.ok) {
          throw new Error(res.status === 404 ? "Document not found" : `Error ${res.status}`);
        }
        const data: DocumentDetail = await res.json();
        setDocument(data);
      } catch (err) {
        setDocError(err instanceof Error ? err.message : "Failed to load document");
      } finally {
        setDocLoading(false);
      }
    }

    fetchDocument();
  }, [documentId]);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;

    setSearching(true);
    setSearchError("");
    setSearchResult(null);

    try {
      const res = await fetch(
        `${API_URL}/api/documents/${documentId}/search?q=${encodeURIComponent(query.trim())}`
      );
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Search failed (${res.status})`);
      }
      const data: SearchResult = await res.json();
      setSearchResult(data);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }, [query, documentId]);

  const toggleExpand = useCallback((chunkId: string) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev);
      if (next.has(chunkId)) {
        next.delete(chunkId);
      } else {
        next.add(chunkId);
      }
      return next;
    });
  }, []);

  const formatDate = (iso: string): string => {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

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

      {/* Search section */}
      {document.upload_status === "completed" && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4">Search this document</h3>

          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Ask a question about this document"
              className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--input-bg)] px-4 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:outline-none transition-colors"
            />
            <button
              onClick={handleSearch}
              disabled={searching || !query.trim()}
              className="rounded-lg bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {searching ? "Searching..." : "Search"}
            </button>
          </div>

          {/* Search error */}
          {searchError && (
            <div className="mt-3 rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-3">
              <p className="text-sm text-[var(--error)]">{searchError}</p>
            </div>
          )}

          {/* Search results */}
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
