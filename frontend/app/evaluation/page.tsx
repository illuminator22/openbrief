export default function EvaluationPage() {
  return (
    <div className="p-8">
      <h2 className="text-2xl font-semibold">Evaluation</h2>
      <p className="mt-2 text-[var(--muted)]">
        RAG evaluation metrics will appear here in Phase 2.
      </p>
      <p className="mt-4 text-sm text-[var(--muted)] opacity-60">
        Hallucination rate, retrieval precision, citation accuracy, and answer relevance.
      </p>
    </div>
  );
}
