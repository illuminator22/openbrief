export default function DashboardPage() {
  return (
    <div className="p-8">
      <h2 className="text-2xl font-semibold">Dashboard</h2>
      <p className="mt-2 text-[var(--muted)]">
        Welcome to OpenBrief. Upload a legal document to get started.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6">
          <p className="text-sm text-[var(--muted)]">Documents</p>
          <p className="mt-1 text-3xl font-semibold">&mdash;</p>
        </div>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6">
          <p className="text-sm text-[var(--muted)]">Chunks Indexed</p>
          <p className="mt-1 text-3xl font-semibold">&mdash;</p>
        </div>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6">
          <p className="text-sm text-[var(--muted)]">Queries Run</p>
          <p className="mt-1 text-3xl font-semibold">&mdash;</p>
        </div>
      </div>
    </div>
  );
}
