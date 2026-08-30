"use client";

import { useEffect, useRef, useState } from "react";

import { SendIcon, StopIcon } from "./icons";

const MAX_HEIGHT = 200;

export default function Composer({
  onSend,
  onStop,
  busy,
  disabled = false,
  placeholder = "Ask about your documents…",
}: {
  onSend: (text: string) => void;
  onStop: () => void;
  busy: boolean;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Grow with the content up to a cap, then scroll inside the box.
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT)}px`;
  }, [text]);

  function submit() {
    const trimmed = text.trim();
    if (!trimmed || busy || disabled) return;

    onSend(trimmed);
    setText("");
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter breaks the line. IME composition must not send,
    // or typing in Japanese/Chinese submits mid-word.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  const canSend = text.trim().length > 0 && !disabled;

  return (
    <div className="border-t border-line bg-canvas px-4 py-3 sm:px-6">
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-line bg-panel px-3 py-2 focus-within:border-ink-faint">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKeyDown}
          className="max-h-[200px] flex-1 resize-none bg-transparent py-1.5 text-[0.9375rem] leading-relaxed outline-none placeholder:text-ink-faint disabled:cursor-not-allowed"
        />

        {busy ? (
          <button
            type="button"
            onClick={onStop}
            title="Stop"
            aria-label="Stop generating"
            className="mb-0.5 rounded-lg bg-raised p-2 text-ink transition-colors hover:bg-line"
          >
            <StopIcon />
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!canSend}
            title="Send"
            aria-label="Send message"
            className="mb-0.5 rounded-lg bg-ink p-2 text-canvas transition-opacity hover:opacity-85 disabled:opacity-25"
          >
            <SendIcon />
          </button>
        )}
      </div>

      <p className="mx-auto mt-2 max-w-3xl text-center text-[0.6875rem] text-ink-faint">
        Answers come only from the ingested documents, and are graded for grounding
        before you see them.
      </p>
    </div>
  );
}
