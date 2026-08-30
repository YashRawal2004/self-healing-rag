"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";
import type { Me, UserSettings } from "@/lib/types";

const MODEL_FIELDS: { key: keyof UserSettings["models"]; label: string }[] = [
  { key: "agent", label: "Agent" },
  { key: "grade_documents", label: "Grade documents" },
  { key: "transform_query", label: "Rewrite query" },
  { key: "generate", label: "Generate answer" },
  { key: "grade_answer", label: "Grade answer" },
];

const PROMPT_FIELDS: { key: keyof UserSettings["prompts"]; label: string }[] = [
  { key: "agent_system", label: "Agent system prompt" },
  { key: "doc_grader", label: "Document grader" },
  { key: "query_rewriter", label: "Query rewriter" },
  { key: "generate", label: "Generate" },
  { key: "generate_retry", label: "Generate (retry)" },
  { key: "answer_grader", label: "Answer grader" },
];

export default function SettingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const [who, current] = await Promise.all([api.getMe(), api.getSettings()]);
        setMe(who);
        setSettings(current);
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 401) {
          router.replace("/login");
          return;
        }
        setError(caught instanceof Error ? caught.message : String(caught));
      }
    })();
  }, [router]);

  function patchSettings(next: UserSettings) {
    setSettings(next);
  }

  async function saveSettings(event: FormEvent) {
    event.preventDefault();
    if (!settings) return;
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const saved = await api.saveSettings(settings);
      setSettings(saved);
      setNote("Settings saved. They apply to every chat on the next message.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function saveKey(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const result = await api.saveApiKey(apiKey.trim());
      setApiKey("");
      setMe((previous) =>
        previous
          ? { ...previous, key_configured: result.key_configured, key_hint: result.key_hint }
          : previous,
      );
      setNote("API key saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function removeKey() {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      await api.deleteApiKey();
      setMe((previous) =>
        previous ? { ...previous, key_configured: false, key_hint: null } : previous,
      );
      setNote("API key removed. Chat is disabled until you add one.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function onChangePassword(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      await api.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setNote("Password updated. Other devices were signed out.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteAccount() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteAccount(deletePassword);
      router.replace("/register");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
      setBusy(false);
    }
  }

  if (!settings || !me) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-ink-muted">
        Loading settings…
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto bg-canvas">
      <div className="mx-auto max-w-2xl px-5 py-8">
        <div className="mb-6 flex items-baseline justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold">Settings</h1>
            <p className="mt-1 text-xs text-ink-muted">
              Signed in as <span className="text-ink">{me.login_id}</span>. These knobs apply to
              every chat.
            </p>
          </div>
          <Link href="/" className="text-xs text-accent underline underline-offset-2">
            Back to chats
          </Link>
        </div>

        {error && <p className="mb-4 text-xs text-danger">{error}</p>}
        {note && <p className="mb-4 text-xs text-ink-muted">{note}</p>}

        <section className="mb-8 rounded-xl border border-line p-4">
          <h2 className="text-sm font-medium">OpenRouter API key</h2>
          <p className="mt-1 text-xs text-ink-muted">
            {me.key_configured
              ? `Saved (…${me.key_hint}). Paste a new key to replace it.`
              : "Required before you can chat or upload documents."}
          </p>
          <form onSubmit={(event) => void saveKey(event)} className="mt-3 flex gap-2">
            <input
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="sk-or-…"
              className="flex-1 rounded-lg border border-line bg-panel px-3 py-2 text-sm outline-none"
            />
            <button
              type="submit"
              disabled={busy || !apiKey.trim()}
              className="rounded-lg bg-ink px-3 py-2 text-sm text-canvas disabled:opacity-40"
            >
              Save
            </button>
          </form>
          {me.key_configured && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void removeKey()}
              className="mt-2 text-xs text-danger underline underline-offset-2"
            >
              Remove key
            </button>
          )}
        </section>

        <form onSubmit={(event) => void saveSettings(event)}>
          <section className="mb-8 rounded-xl border border-line p-4">
            <h2 className="text-sm font-medium">Models</h2>
            <p className="mt-1 text-xs text-ink-muted">
              OpenRouter model ids. Embedding is pinned to text-embedding-3-small.
            </p>
            <label className="mt-3 block text-xs text-ink-muted">
              Embedding (pinned)
              <input
                value="openai/text-embedding-3-small"
                disabled
                className="mt-1 w-full rounded-lg border border-line bg-raised px-3 py-2 text-sm text-ink-faint"
              />
            </label>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {MODEL_FIELDS.map((field) => (
                <label key={field.key} className="block text-xs text-ink-muted">
                  {field.label}
                  <input
                    value={settings.models[field.key]}
                    onChange={(event) =>
                      patchSettings({
                        ...settings,
                        models: { ...settings.models, [field.key]: event.target.value },
                      })
                    }
                    className="mt-1 w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm outline-none"
                  />
                </label>
              ))}
            </div>
          </section>

          <section className="mb-8 rounded-xl border border-line p-4">
            <h2 className="text-sm font-medium">Retrieval and retries</h2>
            <p className="mt-1 text-xs text-ink-muted">
              Changing chunk size does not rebuild old chats — re-upload to re-chunk.
            </p>
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {(
                [
                  ["chunk_size", "Chunk size", settings.retrieval.chunk_size],
                  ["chunk_overlap", "Overlap", settings.retrieval.chunk_overlap],
                  ["top_k", "Top K", settings.retrieval.top_k],
                  ["max_retrieval_retries", "Retrieval retries", settings.budgets.max_retrieval_retries],
                  ["max_generation_retries", "Generation retries", settings.budgets.max_generation_retries],
                ] as const
              ).map(([key, label, value]) => (
                <label key={key} className="block text-xs text-ink-muted">
                  {label}
                  <input
                    type="number"
                    value={value}
                    onChange={(event) => {
                      const next = Number(event.target.value);
                      if (key === "max_retrieval_retries" || key === "max_generation_retries") {
                        patchSettings({
                          ...settings,
                          budgets: { ...settings.budgets, [key]: next },
                        });
                      } else {
                        patchSettings({
                          ...settings,
                          retrieval: { ...settings.retrieval, [key]: next },
                        });
                      }
                    }}
                    className="mt-1 w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm outline-none"
                  />
                </label>
              ))}
            </div>
          </section>

          <section className="mb-8 rounded-xl border border-line p-4">
            <h2 className="text-sm font-medium">Prompts</h2>
            <div className="mt-3 space-y-3">
              {PROMPT_FIELDS.map((field) => (
                <label key={field.key} className="block text-xs text-ink-muted">
                  {field.label}
                  <textarea
                    value={settings.prompts[field.key]}
                    onChange={(event) =>
                      patchSettings({
                        ...settings,
                        prompts: { ...settings.prompts, [field.key]: event.target.value },
                      })
                    }
                    rows={6}
                    className="mt-1 w-full rounded-lg border border-line bg-panel px-3 py-2 font-mono text-xs outline-none"
                  />
                </label>
              ))}
            </div>
          </section>

          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-ink px-4 py-2 text-sm text-canvas disabled:opacity-40"
          >
            Save settings
          </button>
        </form>

        <section className="mt-10 rounded-xl border border-line p-4">
          <h2 className="text-sm font-medium">Change password</h2>
          <form onSubmit={(event) => void onChangePassword(event)} className="mt-3 grid gap-3 sm:grid-cols-2">
            <input
              type="password"
              placeholder="Current password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className="rounded-lg border border-line bg-panel px-3 py-2 text-sm"
            />
            <input
              type="password"
              placeholder="New password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              minLength={8}
              className="rounded-lg border border-line bg-panel px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={busy || !currentPassword || !newPassword}
              className="rounded-lg border border-line px-3 py-2 text-sm disabled:opacity-40 sm:col-span-2"
            >
              Update password
            </button>
          </form>
        </section>

        <section className="mt-6 rounded-xl border border-danger/40 p-4">
          <h2 className="text-sm font-medium text-danger">Delete account</h2>
          <p className="mt-1 text-xs text-ink-muted">
            Deletes you, every chat, every chunk, and the stored key. This cannot be undone.
          </p>
          {!confirmDelete ? (
            <button
              type="button"
              className="mt-3 text-xs text-danger underline underline-offset-2"
              onClick={() => setConfirmDelete(true)}
            >
              I want to delete my account
            </button>
          ) : (
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input
                type="password"
                placeholder="Type your password"
                value={deletePassword}
                onChange={(event) => setDeletePassword(event.target.value)}
                className="flex-1 rounded-lg border border-line bg-panel px-3 py-2 text-sm"
              />
              <button
                type="button"
                disabled={busy || !deletePassword}
                onClick={() => void onDeleteAccount()}
                className="rounded-lg bg-danger px-3 py-2 text-sm text-white disabled:opacity-40"
              >
                Delete forever
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
