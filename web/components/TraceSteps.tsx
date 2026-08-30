"use client";

import { useState } from "react";

import {
  AlertIcon,
  CheckIcon,
  ChevronIcon,
  PenToolIcon,
  RefreshIcon,
  SearchIcon,
} from "./icons";
import type { TraceStep } from "@/lib/types";

/** Per-node presentation. Anything unlisted falls back to a plain search icon. */
const NODE_STYLES: Record<string, { icon: typeof SearchIcon; tone: string }> = {
  tool_start: { icon: SearchIcon, tone: "text-ink-muted" },
  retrieve: { icon: SearchIcon, tone: "text-ink-muted" },
  grade_documents: { icon: CheckIcon, tone: "text-ink-muted" },
  transform_query: { icon: RefreshIcon, tone: "text-accent" },
  generate: { icon: PenToolIcon, tone: "text-ink-muted" },
  grade_answer: { icon: CheckIcon, tone: "text-ink-muted" },
  retry: { icon: RefreshIcon, tone: "text-accent" },
  fallback: { icon: AlertIcon, tone: "text-danger" },
  best_effort: { icon: AlertIcon, tone: "text-danger" },
  tool_error: { icon: AlertIcon, tone: "text-danger" },
};

/** One-line summary for the collapsed state: how much work the loop actually did. */
function summarize(steps: TraceStep[], running: boolean): string {
  if (running && steps.length === 0) return "Thinking…";

  const retries = steps.filter((step) => step.node === "retry").length;
  const count = `${steps.length} step${steps.length === 1 ? "" : "s"}`;

  if (running) return `${steps[steps.length - 1].label}…`;
  if (retries === 0) return count;
  return `${count} · ${retries} self-correction${retries === 1 ? "" : "s"}`;
}

export default function TraceSteps({
  steps,
  running = false,
}: {
  steps: TraceStep[];
  /** Keeps the panel open and pulsing while the turn is still streaming. */
  running?: boolean;
}) {
  const [manuallyOpen, setManuallyOpen] = useState(false);

  // Open automatically while streaming so the loop is visible as it happens,
  // then collapse once the answer lands — the answer is the point, not the trace.
  const open = running || manuallyOpen;

  if (steps.length === 0 && !running) return null;

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setManuallyOpen((previous) => !previous)}
        aria-expanded={open}
        className="group flex items-center gap-1.5 text-xs text-ink-muted transition-colors hover:text-ink"
      >
        <ChevronIcon
          className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? "rotate-90" : ""}`}
        />
        <span className={running ? "animate-pulse" : undefined}>
          {summarize(steps, running)}
        </span>
      </button>

      {open && steps.length > 0 && (
        <ol className="mt-2 space-y-1.5 border-l border-line pl-4">
          {steps.map((step, index) => {
            const style = NODE_STYLES[step.node] ?? {
              icon: SearchIcon,
              tone: "text-ink-muted",
            };
            const Icon = style.icon;

            return (
              <li key={index} className="flex items-start gap-2 text-xs leading-relaxed">
                <Icon className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${style.tone}`} />
                <span className="min-w-0">
                  <span className="text-ink">{step.label}</span>
                  {step.detail && (
                    <span className="text-ink-faint"> — {step.detail}</span>
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
