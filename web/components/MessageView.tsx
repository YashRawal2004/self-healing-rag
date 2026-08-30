"use client";

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import TraceSteps from "./TraceSteps";
import type { Message, TraceStep } from "@/lib/types";

/**
 * One turn in the transcript.
 *
 * The user's text sits in a bubble; the assistant's runs full width with no
 * container, which is what keeps long grounded answers readable.
 */
export default function MessageView({
  message,
  streamingSteps,
  running = false,
}: {
  message: Message;
  /** Live steps for the in-flight answer, before it is persisted. */
  streamingSteps?: TraceStep[];
  running?: boolean;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-raised px-4 py-2.5 text-[0.9375rem] leading-relaxed whitespace-pre-wrap break-words">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-none">
      <TraceSteps steps={streamingSteps ?? message.trace} running={running} />

      {message.content && (
        <div className="answer text-[0.9375rem] leading-relaxed break-words">
          <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
        </div>
      )}
    </div>
  );
}
