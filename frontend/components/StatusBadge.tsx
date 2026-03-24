interface StatusBadgeProps {
  status: string;
}

const statusStyles: Record<string, string> = {
  completed: "bg-[var(--success)]/15 text-[var(--success)]",
  processing: "bg-[var(--accent)]/15 text-[var(--accent)]",
  failed: "bg-[var(--error)]/15 text-[var(--error)]",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const style = statusStyles[status] || "bg-[var(--surface)] text-[var(--muted)]";

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {status}
    </span>
  );
}
