/** Shapes returned by the Flask API. */

export type TraceStep = {
  node:
    | "tool_start"
    | "tool_error"
    | "retrieve"
    | "grade_documents"
    | "transform_query"
    | "generate"
    | "grade_answer"
    | "retry"
    | "fallback"
    | "best_effort";
  label: string;
  detail: string;
  [key: string]: unknown;
};

export type Message = {
  id: number;
  role: "user" | "assistant";
  content: string;
  trace: TraceStep[];
  created_at: string;
};

export type ChatSummary = {
  id: string;
  title: string;
  title_is_auto: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
};

export type Chat = ChatSummary & { messages: Message[] };

export type Me = {
  id: string;
  login_id: string;
  created_at: string | null;
  key_configured: boolean;
  key_hint: string | null;
};

export type ChatDocument = {
  id: string;
  filename: string;
  page_count: number | null;
  status: "pending" | "ingested" | "failed";
  error: string | null;
  chunk_count: number;
  created_at: string;
};

export type UserSettings = {
  models: {
    agent: string;
    grade_documents: string;
    transform_query: string;
    generate: string;
    grade_answer: string;
  };
  prompts: {
    agent_system: string;
    doc_grader: string;
    query_rewriter: string;
    generate: string;
    generate_retry: string;
    answer_grader: string;
  };
  retrieval: {
    chunk_size: number;
    chunk_overlap: number;
    top_k: number;
  };
  budgets: {
    max_retrieval_retries: number;
    max_generation_retries: number;
  };
};

export type TurnEvent =
  | { type: "user"; message: Message }
  | { type: "title"; title: string }
  | { type: "step"; step: TraceStep }
  | { type: "answer"; message: Message }
  | { type: "error"; error: string }
  | { type: "done" };
