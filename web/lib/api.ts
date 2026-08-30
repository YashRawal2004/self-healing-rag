/** Typed client. Same-origin `/api` is proxied to Flask so the session cookie sticks. */

import type { Chat, ChatDocument, ChatSummary, Me, TurnEvent, UserSettings } from "./types";

const jsonHeaders = { "Content-Type": "application/json" };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { credentials: "include", ...init });
  } catch {
    throw new ApiError("Cannot reach the API. Is the Flask server running?", 0);
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.error === "string") return body.error;
  } catch {
    // fall through
  }
  return `Request failed with status ${response.status}`;
}

export function getHealth() {
  return request<{ ok: boolean }>("/api/health");
}

export function getMe() {
  return request<Me>("/api/me");
}

export function register(loginId: string, password: string) {
  return request<Me>("/api/auth/register", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ login_id: loginId, password }),
  });
}

export function login(loginId: string, password: string) {
  return request<Me>("/api/auth/login", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ login_id: loginId, password }),
  });
}

export function logout() {
  return request<{ ok: boolean }>("/api/auth/logout", { method: "POST" });
}

export function changePassword(currentPassword: string, newPassword: string) {
  return request<{ ok: boolean }>("/api/auth/password", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export function deleteAccount(password: string) {
  return request<{ ok: boolean }>("/api/auth/account", {
    method: "DELETE",
    headers: jsonHeaders,
    body: JSON.stringify({ password }),
  });
}

export async function listChats(): Promise<ChatSummary[]> {
  const { chats } = await request<{ chats: ChatSummary[] }>("/api/chats");
  return chats;
}

export function createChat() {
  return request<ChatSummary>("/api/chats", { method: "POST" });
}

export function getChat(chatId: string) {
  return request<Chat>(`/api/chats/${chatId}`);
}

export function renameChat(chatId: string, title: string) {
  return request<ChatSummary>(`/api/chats/${chatId}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify({ title }),
  });
}

export function deleteChat(chatId: string) {
  return request<void>(`/api/chats/${chatId}`, { method: "DELETE" });
}

export function getSettings() {
  return request<UserSettings>("/api/settings");
}

export function saveSettings(settings: UserSettings) {
  return request<UserSettings>("/api/settings", {
    method: "PUT",
    headers: jsonHeaders,
    body: JSON.stringify(settings),
  });
}

export function saveApiKey(apiKey: string) {
  return request<{ key_configured: boolean; key_hint: string }>("/api/settings/key", {
    method: "PUT",
    headers: jsonHeaders,
    body: JSON.stringify({ api_key: apiKey }),
  });
}

export function deleteApiKey() {
  return request<{ key_configured: boolean; key_hint: null }>("/api/settings/key", {
    method: "DELETE",
  });
}

export async function listDocuments(chatId: string): Promise<ChatDocument[]> {
  const { documents } = await request<{ documents: ChatDocument[] }>(
    `/api/chats/${chatId}/documents`,
  );
  return documents;
}

export function uploadDocuments(chatId: string, files: File[]) {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return request<{ documents: ChatDocument[]; ingested: ChatDocument[] }>(
    `/api/chats/${chatId}/documents`,
    { method: "POST", body: form },
  );
}

export function deleteDocument(chatId: string, documentId: string) {
  return request<{ documents: ChatDocument[] }>(
    `/api/chats/${chatId}/documents/${documentId}`,
    { method: "DELETE" },
  );
}

export function clearDocuments(chatId: string) {
  return request<{ documents: ChatDocument[] }>(`/api/chats/${chatId}/documents`, {
    method: "DELETE",
  });
}

export async function* streamTurn(
  chatId: string,
  content: string,
  signal?: AbortSignal,
): AsyncGenerator<TurnEvent> {
  let response: Response;
  try {
    response = await fetch(`/api/chats/${chatId}/messages`, {
      method: "POST",
      headers: jsonHeaders,
      credentials: "include",
      body: JSON.stringify({ content }),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Cannot reach the API. Is the Flask server running?", 0);
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  if (!response.body) {
    throw new ApiError("The server returned an empty response stream", 0);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let split: number;
      while ((split = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, split);
        buffer = buffer.slice(split + 2);
        const line = frame.split("\n").find((candidate) => candidate.startsWith("data: "));
        if (line) yield JSON.parse(line.slice(6)) as TurnEvent;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
