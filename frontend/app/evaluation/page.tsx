"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface EvalSummary {
  total_evaluations: number;
  model_filter: string | null;
  avg_hallucination_score: number | null;
  avg_retrieval_precision: number | null;
  avg_citation_accuracy: number | null;
  avg_answer_relevance: number | null;
  avg_response_time_ms: number | null;
  category_averages: Record<string, Record<string, number | null>>;
  last_run: string | null;
}

interface EvalLogEntry {
  query: string;
  hallucination_score: number | null;
  retrieval_precision: number | null;
  citation_accuracy: number | null;
  answer_relevance: number | null;
  response_time_ms: number | null;
  model_used: string | null;
  created_at: string;
}

interface EvalResults {
  results: EvalLogEntry[];
  total: number;
}

function MetricCard({
  label,
  value,
  threshold,
  inverse = false,
}: {
  label: string;
  value: number | null;
  threshold: { green: number; yellow: number };
  inverse?: boolean;
}) {
  const pct = value !== null ? (value * 100).toFixed(1) : "—";
  let color = "text-[var(--muted)]";
  if (value !== null) {
    if (inverse) {
      color = value <= threshold.green ? "text-[var(--success)]" : value <= threshold.yellow ? "text-yellow-400" : "text-[var(--error)]";
    } else {
      color = value >= threshold.green ? "text-[var(--success)]" : value >= threshold.yellow ? "text-yellow-400" : "text-[var(--error)]";
    }
  }

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <p className="text-xs text-[var(--muted)]">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${color}`}>
        {pct}{value !== null ? "%" : ""}
      </p>
    </div>
  );
}

export default function EvaluationPage() {
  const [modelFilter, setModelFilter] = useState<string>("");
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const { data: summary, isLoading: summaryLoading } = useQuery<EvalSummary>({
    queryKey: ["eval-summary", modelFilter],
    queryFn: async () => {
      const url = modelFilter
        ? `${API_URL}/api/evaluation/summary?model=${encodeURIComponent(modelFilter)}`
        : `${API_URL}/api/evaluation/summary`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load summary");
      return res.json();
    },
  });

  const { data: results } = useQuery<EvalResults>({
    queryKey: ["eval-results", modelFilter],
    queryFn: async () => {
      const url = modelFilter
        ? `${API_URL}/api/evaluation/results?model=${encodeURIComponent(modelFilter)}&limit=100`
        : `${API_URL}/api/evaluation/results?limit=100`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load results");
      return res.json();
    },
  });

  // Get unique models from results for the filter dropdown
  const uniqueModels = Array.from(
    new Set(results?.results?.map((r) => r.model_used).filter(Boolean) || [])
  ) as string[];

  // Build chart data from category averages
  const chartData = summary?.category_averages
    ? Object.entries(summary.category_averages).map(([category, metrics]) => ({
        category: category.replace(/_/g, " "),
        Hallucination: metrics.hallucination != null ? +(metrics.hallucination * 100).toFixed(1) : 0,
        Relevance: metrics.answer_relevancy != null ? +(metrics.answer_relevancy * 100).toFixed(1) : 0,
        Faithfulness: metrics.faithfulness != null ? +(metrics.faithfulness * 100).toFixed(1) : 0,
        Precision: metrics.contextual_precision != null ? +(metrics.contextual_precision * 100).toFixed(1) : 0,
      }))
    : [];

  const toggleRow = (idx: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  if (summaryLoading) {
    return (
      <div className="p-8">
        <h2 className="text-2xl font-semibold">Evaluation</h2>
        <p className="mt-4 text-[var(--muted)]">Loading evaluation data...</p>
      </div>
    );
  }

  if (!summary || summary.total_evaluations === 0) {
    return (
      <div className="p-8">
        <h2 className="text-2xl font-semibold">Evaluation</h2>
        <div className="mt-8 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
          <p className="text-[var(--muted)]">No evaluation data yet.</p>
          <p className="mt-2 text-sm text-[var(--muted)] opacity-60">
            Run an evaluation via POST /api/evaluation/run to see metrics here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold">Evaluation Dashboard</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {summary.total_evaluations} test cases evaluated
            {summary.last_run && ` · Last run: ${new Date(summary.last_run).toLocaleDateString()}`}
          </p>
        </div>

        {/* Model filter */}
        {uniqueModels.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-[var(--muted)]">Model:</span>
            <select
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="rounded-lg border border-[var(--border)] bg-[var(--input-bg)] px-3 py-1.5 text-xs text-[var(--foreground)] focus:border-[var(--accent)] focus:outline-none"
            >
              <option value="">All models</option>
              {uniqueModels.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-8">
        <MetricCard
          label="Hallucination Rate"
          value={summary.avg_hallucination_score}
          threshold={{ green: 0.95, yellow: 0.90 }}
        />
        <MetricCard
          label="Answer Relevance"
          value={summary.avg_answer_relevance}
          threshold={{ green: 0.90, yellow: 0.80 }}
        />
        <MetricCard
          label="Faithfulness"
          value={summary.avg_citation_accuracy}
          threshold={{ green: 0.90, yellow: 0.80 }}
        />
        <MetricCard
          label="Retrieval Precision"
          value={summary.avg_retrieval_precision}
          threshold={{ green: 0.85, yellow: 0.75 }}
        />
      </div>

      {/* Category breakdown chart */}
      {chartData.length > 0 && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 mb-8">
          <h3 className="text-sm font-medium text-[var(--muted)] mb-4">Scores by Category</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="category"
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                angle={-20}
                textAnchor="end"
                height={60}
              />
              <YAxis
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                domain={[0, 100]}
                label={{ value: "%", position: "insideLeft", fill: "var(--muted)" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  color: "var(--foreground)",
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Hallucination" fill="#D97757" radius={[2, 2, 0, 0]} />
              <Bar dataKey="Relevance" fill="#1D9E75" radius={[2, 2, 0, 0]} />
              <Bar dataKey="Faithfulness" fill="#7F77DD" radius={[2, 2, 0, 0]} />
              <Bar dataKey="Precision" fill="#378ADD" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Individual results table */}
      {results && results.results.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[var(--muted)] mb-3">
            Individual Results ({results.total})
          </h3>
          <div className="rounded-xl border border-[var(--border)] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[var(--surface)] text-[var(--muted)] text-left">
                  <th className="px-4 py-2 font-medium">Query</th>
                  <th className="px-4 py-2 font-medium">Halluc.</th>
                  <th className="px-4 py-2 font-medium">Relev.</th>
                  <th className="px-4 py-2 font-medium">Faith.</th>
                  <th className="px-4 py-2 font-medium">Prec.</th>
                  <th className="px-4 py-2 font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {results.results.map((r, i) => {
                  const allPassing =
                    (r.hallucination_score === null || r.hallucination_score >= 0.5) &&
                    (r.answer_relevance === null || r.answer_relevance >= 0.5) &&
                    (r.citation_accuracy === null || r.citation_accuracy >= 0.5);

                  return (
                    <tr
                      key={i}
                      onClick={() => toggleRow(i)}
                      className={`border-t border-[var(--border)] cursor-pointer transition-colors hover:bg-[var(--surface)] ${
                        allPassing ? "" : "bg-[var(--error)]/5"
                      }`}
                    >
                      <td className="px-4 py-2 max-w-xs truncate">{r.query}</td>
                      <td className="px-4 py-2">{r.hallucination_score != null ? `${(r.hallucination_score * 100).toFixed(0)}%` : "—"}</td>
                      <td className="px-4 py-2">{r.answer_relevance != null ? `${(r.answer_relevance * 100).toFixed(0)}%` : "—"}</td>
                      <td className="px-4 py-2">{r.citation_accuracy != null ? `${(r.citation_accuracy * 100).toFixed(0)}%` : "—"}</td>
                      <td className="px-4 py-2">{r.retrieval_precision != null ? `${(r.retrieval_precision * 100).toFixed(0)}%` : "—"}</td>
                      <td className="px-4 py-2 text-[var(--muted)]">{r.response_time_ms ? `${(r.response_time_ms / 1000).toFixed(1)}s` : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
