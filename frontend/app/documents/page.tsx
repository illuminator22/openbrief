"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import DocumentUpload from "@/components/DocumentUpload";
import StatusBadge from "@/components/StatusBadge";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DocumentItem {
  id: string;
  filename: string;
  file_size: number;
  page_count: number | null;
  upload_status: string;
  created_at: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/documents/`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents);
      }
    } catch {
      // Silently fail — list will be empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

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
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="p-8">
      <h2 className="text-2xl font-semibold">Documents</h2>
      <p className="mt-2 text-[var(--muted)]">
        Upload a legal document to parse, chunk, and index for search.
      </p>

      <div className="mt-8">
        <DocumentUpload onUploadComplete={fetchDocuments} />
      </div>

      {/* Document list */}
      <div className="mt-10">
        <h3 className="text-lg font-semibold mb-4">Uploaded Documents</h3>

        {loading ? (
          <p className="text-sm text-[var(--muted)]">Loading documents...</p>
        ) : documents.length === 0 ? (
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
            <p className="text-[var(--muted)]">No documents uploaded yet.</p>
          </div>
        ) : (
          <div className="rounded-xl border border-[var(--border)] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[var(--surface)] text-[var(--muted)] text-left">
                  <th className="px-4 py-3 font-medium">Filename</th>
                  <th className="px-4 py-3 font-medium">Pages</th>
                  <th className="px-4 py-3 font-medium">Size</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-t border-[var(--border)] hover:bg-[var(--surface)] transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/documents/${doc.id}`}
                        className="text-[var(--accent)] hover:underline font-medium"
                      >
                        {doc.filename}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {doc.page_count ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {formatSize(doc.file_size)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={doc.upload_status} />
                    </td>
                    <td className="px-4 py-3 text-[var(--muted)]">
                      {formatDate(doc.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
