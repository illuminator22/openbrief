"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

interface ModelsResponse {
  models: Record<string, ModelInfo[]>;
}

const PROVIDERS = [
  { id: "openai", label: "OpenAI" },
  { id: "anthropic", label: "Anthropic" },
  { id: "deepseek", label: "DeepSeek" },
];

export default function SettingsPage() {
  const queryClient = useQueryClient();

  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");

  // Fetch current settings
  const { data: settings, isLoading: settingsLoading } = useQuery<LLMSettings>({
    queryKey: ["llm-settings"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/settings/llm`);
      if (!res.ok) throw new Error("Failed to load settings");
      return res.json();
    },
  });

  // Fetch available models
  const { data: modelsData } = useQuery<ModelsResponse>({
    queryKey: ["models"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/settings/models`);
      if (!res.ok) throw new Error("Failed to load models");
      return res.json();
    },
  });

  // Set defaults from current settings
  useEffect(() => {
    if (settings?.provider) setProvider(settings.provider);
    if (settings?.model) setModel(settings.model);
  }, [settings]);

  // Auto-select first model when provider changes
  useEffect(() => {
    if (modelsData?.models) {
      const providerModels = modelsData.models[provider] || [];
      if (providerModels.length > 0 && !providerModels.some((m) => m.id === model)) {
        setModel(providerModels[0].id);
      }
    }
  }, [provider, modelsData, model]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_URL}/api/settings/llm-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, provider, model }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Save failed (${res.status})`);
      }
      return res.json();
    },
    onSuccess: () => {
      setApiKey("");
      queryClient.invalidateQueries({ queryKey: ["llm-settings"] });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_URL}/api/settings/llm-key`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to remove key");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-settings"] });
    },
  });

  const handleSave = useCallback(() => {
    if (!apiKey.trim()) return;
    saveMutation.mutate();
  }, [apiKey, saveMutation]);

  const currentModels = modelsData?.models?.[provider] || [];
  const isConfigured = settings?.has_key === true;

  if (settingsLoading) {
    return (
      <div className="p-8">
        <h2 className="text-2xl font-semibold">Settings</h2>
        <p className="mt-4 text-[var(--muted)]">Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl">
      <h2 className="text-2xl font-semibold">Settings</h2>
      <p className="mt-2 text-[var(--muted)]">
        Bring Your Own Key — configure your LLM API key for document analysis.
      </p>

      {/* Configured state */}
      {isConfigured && !saveMutation.isSuccess && (
        <div className="mt-8 rounded-xl border border-[var(--success)]/30 bg-[var(--success)]/5 p-6">
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-[var(--success)]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <p className="text-sm font-medium text-[var(--success)]">API key connected</p>
          </div>
          <div className="mt-3 space-y-1 text-sm">
            <p>
              <span className="text-[var(--muted)]">Provider:</span>{" "}
              {PROVIDERS.find((p) => p.id === settings?.provider)?.label || settings?.provider}
            </p>
            <p>
              <span className="text-[var(--muted)]">Model:</span>{" "}
              {settings?.model || "Default"}
            </p>
          </div>
          <button
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
            className="mt-4 rounded-lg border border-[var(--error)]/30 px-4 py-2 text-sm font-medium text-[var(--error)] transition-colors hover:bg-[var(--error)]/10 disabled:opacity-50"
          >
            {deleteMutation.isPending ? "Removing..." : "Remove API Key"}
          </button>
          {deleteMutation.isError && (
            <p className="mt-2 text-sm text-[var(--error)]">
              {deleteMutation.error.message}
            </p>
          )}
        </div>
      )}

      {/* Configuration form */}
      {(!isConfigured || saveMutation.isSuccess) && (
        <div className="mt-8 space-y-6">
          {/* Provider selector */}
          <div>
            <label className="block text-sm font-medium mb-3">Provider</label>
            <div className="flex gap-2">
              {PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setProvider(p.id)}
                  className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                    provider === p.id
                      ? "bg-[var(--accent)] text-white"
                      : "bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-light)]"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Model selector */}
          <div>
            <label className="block text-sm font-medium mb-2">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--input-bg)] px-4 py-2.5 text-sm text-[var(--foreground)] focus:border-[var(--accent)] focus:outline-none transition-colors"
            >
              {currentModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} — {m.description}
                  {m.pricing
                    ? ` ($${m.pricing.input}/${m.pricing.output} per 1M tokens)`
                    : ""}
                </option>
              ))}
            </select>
          </div>

          {/* API key input */}
          <div>
            <label className="block text-sm font-medium mb-2">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              placeholder={`Enter your ${PROVIDERS.find((p) => p.id === provider)?.label || ""} API key`}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--input-bg)] px-4 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:outline-none transition-colors"
            />
            <p className="mt-1.5 text-xs text-[var(--muted)]">
              Your key is encrypted at rest and never displayed after saving.
            </p>
          </div>

          {/* Save button */}
          <button
            onClick={handleSave}
            disabled={!apiKey.trim() || saveMutation.isPending}
            className="rounded-lg bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saveMutation.isPending ? "Saving..." : "Save API Key"}
          </button>

          {/* Error/success messages */}
          {saveMutation.isError && (
            <div className="rounded-xl border border-[var(--error)]/30 bg-[var(--error)]/5 p-3">
              <p className="text-sm text-[var(--error)]">{saveMutation.error.message}</p>
            </div>
          )}
          {saveMutation.isSuccess && (
            <div className="rounded-xl border border-[var(--success)]/30 bg-[var(--success)]/5 p-3">
              <p className="text-sm text-[var(--success)]">API key saved successfully.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
