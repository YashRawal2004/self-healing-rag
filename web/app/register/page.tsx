"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import * as api from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.register(loginId.trim(), password);
      router.replace("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full overflow-auto bg-canvas">
      <form
        onSubmit={(event) => void onSubmit(event)}
        className="m-auto w-full max-w-sm px-6 py-12"
      >
        <h1 className="text-lg font-semibold">Create an account</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Login id is 3–32 characters: letters, digits, underscore. No email.
        </p>

        <label className="mt-6 block text-xs font-medium text-ink-muted">
          Login id
          <input
            value={loginId}
            onChange={(event) => setLoginId(event.target.value)}
            autoComplete="username"
            className="mt-1 w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm outline-none focus:border-ink-faint"
            required
          />
        </label>
        <label className="mt-3 block text-xs font-medium text-ink-muted">
          Password (min 8)
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            minLength={8}
            className="mt-1 w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm outline-none focus:border-ink-faint"
            required
          />
        </label>

        {error && <p className="mt-3 text-xs text-danger">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="mt-5 w-full rounded-lg bg-ink px-3 py-2 text-sm text-canvas disabled:opacity-50"
        >
          {busy ? "Creating…" : "Create account"}
        </button>

        <p className="mt-4 text-center text-xs text-ink-muted">
          Already have an account?{" "}
          <Link href="/login" className="text-accent underline underline-offset-2">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
