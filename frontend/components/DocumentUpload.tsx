"use client";

import { useCallback, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DocumentResponse {
  id: string;
  filename: string;
  file_size: number;
  page_count: number | null;
  upload_status: string;
  created_at: string;
}

type UploadState = "idle" | "selected" | "uploading" | "success" | "error";

interface DocumentUploadProps {
  onUploadComplete?: () => void;
}

export default function DocumentUpload({ onUploadComplete }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [document, setDocument] = useState<DocumentResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((f: File): string | null => {
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      return "Only PDF files are supported.";
    }
    if (f.size > 50 * 1024 * 1024) {
      return "File too large. Maximum size is 50MB.";
    }
    return null;
  }, []);

  const selectFile = useCallback(
    (f: File) => {
      const err = validateFile(f);
      if (err) {
        setError(err);
        setState("error");
        return;
      }
      setFile(f);
      setError("");
      setDocument(null);
      setState("selected");
    },
    [validateFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) selectFile(droppedFile);
    },
    [selectFile]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) selectFile(selected);
    },
    [selectFile]
  );

  const handleUpload = useCallback(async () => {
    if (!file) return;

    setState("uploading");
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/api/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Upload failed (${res.status})`);
      }

      const data: DocumentResponse = await res.json();
      setDocument(data);
      setState("success");
      onUploadComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setState("error");
    }
  }, [file]);

  const handleReset = useCallback(() => {
    setFile(null);
    setDocument(null);
    setError("");
    setState("idle");
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full max-w-xl">
      {/* Drop zone */}
      {(state === "idle" || state === "error") && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
            dragOver
              ? "border-[var(--accent)] bg-[var(--accent)]/5"
              : "border-[var(--border)] hover:border-[var(--muted)] hover:bg-[var(--surface)]"
          }`}
        >
          <svg
            className="mx-auto h-10 w-10 text-[var(--muted)]"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 16v-8m0 0l-3 3m3-3l3 3M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="mt-3 text-sm text-[var(--muted)]">
            Drag and drop a PDF here, or{" "}
            <span className="text-[var(--accent)] font-medium">click to browse</span>
          </p>
          <p className="mt-1 text-xs text-[var(--muted)] opacity-60">
            PDF files only, up to 50MB
          </p>

          <input
            ref={inputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>
      )}

      {/* Selected file info */}
      {state === "selected" && file && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--accent)]/10">
                <span className="text-xs font-bold text-[var(--accent)]">PDF</span>
              </div>
              <div>
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs text-[var(--muted)]">{formatSize(file.size)}</p>
              </div>
            </div>
            <button
              onClick={handleReset}
              className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Remove
            </button>
          </div>

          <button
            onClick={handleUpload}
            className="mt-4 w-full rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] active:scale-[0.98]"
          >
            Upload &amp; Process
          </button>
        </div>
      )}

      {/* Uploading state */}
      {state === "uploading" && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-[var(--muted)]/30 border-t-[var(--accent)]" />
          <p className="mt-3 text-sm">
            Uploading and processing...
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Parsing, chunking, and generating embeddings
          </p>
        </div>
      )}

      {/* Success state */}
      {state === "success" && document && (
        <div className="rounded-xl border border-[var(--success)]/30 bg-[var(--success)]/5 p-5">
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-[var(--success)]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <p className="text-sm font-medium text-[var(--success)]">
              Document processed successfully
            </p>
          </div>

          <div className="mt-3 space-y-1 text-sm">
            <p>
              <span className="text-[var(--muted)]">File:</span> {document.filename}
            </p>
            <p>
              <span className="text-[var(--muted)]">Pages:</span>{" "}
              {document.page_count ?? "Unknown"}
            </p>
            <p>
              <span className="text-[var(--muted)]">Status:</span>{" "}
              {document.upload_status}
            </p>
            <p className="text-xs text-[var(--muted)] font-mono">{document.id}</p>
          </div>

          <button
            onClick={handleReset}
            className="mt-4 w-full rounded-lg border border-[var(--success)]/30 px-4 py-2 text-sm font-medium text-[var(--success)] transition-colors hover:bg-[var(--success)]/10"
          >
            Upload Another
          </button>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="mt-3 rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-4">
          <p className="text-sm text-[var(--error)]">{error}</p>
          {state === "error" && (
            <button
              onClick={handleReset}
              className="mt-2 text-sm font-medium text-[var(--error)] hover:opacity-80 transition-opacity"
            >
              Try again
            </button>
          )}
        </div>
      )}
    </div>
  );
}
