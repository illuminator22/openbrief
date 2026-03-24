export default function SettingsPage() {
  return (
    <div className="p-8">
      <h2 className="text-2xl font-semibold">Settings</h2>
      <p className="mt-2 text-[var(--muted)]">
        API key configuration will be available here in Phase 2.
      </p>
      <p className="mt-4 text-sm text-[var(--muted)] opacity-60">
        Bring Your Own Key (BYOK) — configure your Claude or OpenAI API key.
      </p>
    </div>
  );
}
