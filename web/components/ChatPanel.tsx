"use client";

import { useEffect, useRef } from "react";

import MessageView from "./MessageView";
import { AlertIcon, BooksIcon } from "./icons";
import type { Message, TraceStep } from "@/lib/types";

export default function ChatPanel({
  messages,
  streamingSteps,
  running,
  error,
  emptyHint,
  onUpload,
}: {
  messages: Message[];
  streamingSteps: TraceStep[];
  running: boolean;
  error: string | null;
  emptyHint: string;
  onUpload?: () => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Follow the transcript as the turn unfolds — new steps arrive one at a time,
  // so this fires on every step, not just on a new message.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [messages.length, streamingSteps.length, running]);

  if (messages.length === 0 && !running) {
    return (
      <div className="flex flex-1 items-center justify-center px-6">
        <div className="max-w-sm text-center">
          <BooksIcon className="mx-auto mb-3 h-6 w-6 text-ink-faint" />
          <h2 className="text-sm font-medium text-ink">Ask your documents</h2>
          <p className="mt-1.5 text-xs leading-relaxed text-ink-muted">{emptyHint}</p>
          {onUpload && (
            <button
              type="button"
              onClick={onUpload}
              className="mt-4 rounded-lg bg-ink px-3 py-2 text-sm text-canvas"
            >
              Upload a PDF
            </button>
          )}
          {error && (
            <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-danger">
              <AlertIcon className="h-3.5 w-3.5" />
              {error}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        {messages.map((message) => (
          <MessageView key={message.id} message={message} />
        ))}

        {running && (
          <MessageView
            // Placeholder for the answer being streamed: no content yet, and the
            // live steps stand in for it until the `answer` frame arrives.
            message={{
              id: -1,
              role: "assistant",
              content: "",
              trace: [],
              created_at: "",
            }}
            streamingSteps={streamingSteps}
            running
          />
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-danger/40 bg-danger/5 px-3 py-2.5 text-xs text-danger">
            <AlertIcon className="mt-0.5 h-3.5 w-3.5" />
            <span className="min-w-0 break-words">{error}</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
