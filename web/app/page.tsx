"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import ChatPanel from "@/components/ChatPanel";
import Composer from "@/components/Composer";
import KnowledgeBaseModal from "@/components/KnowledgeBaseModal";
import Sidebar from "@/components/Sidebar";
import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";
import type { ChatDocument, ChatSummary, Me, Message, TraceStep } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<ChatDocument[]>([]);

  const [steps, setSteps] = useState<TraceStep[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [kbOpen, setKbOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const loadDocuments = useCallback(async (chatId: string) => {
    try {
      setDocuments(await api.listDocuments(chatId));
    } catch {
      setDocuments([]);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        await api.getHealth();
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : String(caught));
        return;
      }

      try {
        const who = await api.getMe();
        setMe(who);
        const list = await api.listChats();
        setChats(list);
        if (list.length > 0) {
          const first = list[0];
          setActiveChatId(first.id);
          const chat = await api.getChat(first.id);
          setMessages(chat.messages);
          setDocuments(await api.listDocuments(first.id));
        }
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 401) {
          router.replace("/login");
          return;
        }
        setError(caught instanceof Error ? caught.message : String(caught));
      }
    })();
  }, [router]);

  async function selectChat(chatId: string) {
    if (chatId === activeChatId || running) return;
    setError(null);
    setActiveChatId(chatId);
    setMessages([]);
    setDocuments([]);
    try {
      const chat = await api.getChat(chatId);
      setMessages(chat.messages);
      await loadDocuments(chatId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  async function ensureChat(): Promise<string | null> {
    if (activeChatId) return activeChatId;
    try {
      const created = await api.createChat();
      setActiveChatId(created.id);
      setChats((previous) => [created, ...previous]);
      setDocuments([]);
      setMessages([]);
      return created.id;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
      return null;
    }
  }

  async function newChat() {
    if (running) return;
    if (activeChatId && messages.length === 0) return;
    setError(null);
    setSteps([]);
    try {
      const created = await api.createChat();
      setActiveChatId(created.id);
      setChats((previous) => [created, ...previous]);
      setMessages([]);
      setDocuments([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  async function openDocuments() {
    const chatId = await ensureChat();
    if (chatId) setKbOpen(true);
  }

  async function renameChat(chatId: string, title: string) {
    setChats((previous) =>
      previous.map((chat) =>
        chat.id === chatId ? { ...chat, title, title_is_auto: false } : chat,
      ),
    );
    try {
      await api.renameChat(chatId, title);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
      try {
        setChats(await api.listChats());
      } catch {
        // already reported
      }
    }
  }

  async function deleteChat(chatId: string) {
    try {
      await api.deleteChat(chatId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
      return;
    }
    setChats((previous) => previous.filter((chat) => chat.id !== chatId));
    if (chatId === activeChatId) newChat();
  }

  async function send(text: string) {
    setError(null);
    let chatId = activeChatId;

    if (chatId === null) {
      const createdId = await ensureChat();
      if (!createdId) return;
      chatId = createdId;
    }

    const optimisticId = -Date.now();
    setMessages((previous) => [
      ...previous,
      {
        id: optimisticId,
        role: "user",
        content: text,
        trace: [],
        created_at: new Date().toISOString(),
      },
    ]);

    setSteps([]);
    setRunning(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const event of api.streamTurn(chatId, text, controller.signal)) {
        switch (event.type) {
          case "user":
            setMessages((previous) =>
              previous.map((message) =>
                message.id === optimisticId ? event.message : message,
              ),
            );
            break;
          case "title":
            setChats((previous) =>
              previous.map((chat) =>
                chat.id === chatId ? { ...chat, title: event.title } : chat,
              ),
            );
            break;
          case "step":
            setSteps((previous) => [...previous, event.step]);
            break;
          case "answer":
            setMessages((previous) => [...previous, event.message]);
            setSteps([]);
            break;
          case "error":
            setMessages((previous) =>
              previous.filter((message) => message.id !== optimisticId),
            );
            setError(event.error);
            break;
          case "done":
            break;
        }
      }

      setChats((previous) => {
        const target = previous.find((chat) => chat.id === chatId);
        if (!target) return previous;
        return [target, ...previous.filter((chat) => chat.id !== chatId)];
      });
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") {
        try {
          const chat = await api.getChat(chatId);
          setMessages(chat.messages);
        } catch {
          // reselect later
        }
      } else if (caught instanceof ApiError && caught.status === 401) {
        router.replace("/login");
      } else {
        setMessages((previous) =>
          previous.filter((message) => message.id !== optimisticId),
        );
        setError(caught instanceof Error ? caught.message : String(caught));
      }
    } finally {
      setRunning(false);
      setSteps([]);
      abortRef.current = null;
    }
  }

  async function handleLogout() {
    try {
      await api.logout();
    } catch {
      // still bounce to login
    }
    router.replace("/login");
  }

  if (!me) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-ink-muted">
        {error ?? "Loading…"}
      </div>
    );
  }

  const emptyHint = !me.key_configured
    ? "Add an OpenRouter API key in Settings before uploading or asking a question."
    : documents.length === 0
      ? "Upload a PDF to this chat first. Other chats will not see those chunks."
      : "Questions are answered only from this chat's documents. The retrieval loop grades itself and retries when results fall short.";

  return (
    <div className="flex h-full">
      <Sidebar
        me={me}
        chats={chats}
        activeChatId={activeChatId}
        documentCount={activeChatId ? documents.length : null}
        onNewChat={newChat}
        onSelectChat={(chatId) => void selectChat(chatId)}
        onRenameChat={(chatId, title) => void renameChat(chatId, title)}
        onDeleteChat={(chatId) => void deleteChat(chatId)}
        onOpenKb={() => void openDocuments()}
        onLogout={() => void handleLogout()}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <ChatPanel
          messages={messages}
          streamingSteps={steps}
          running={running}
          error={error}
          emptyHint={emptyHint}
          onUpload={me.key_configured ? () => void openDocuments() : undefined}
        />

        <Composer
          onSend={(text) => void send(text)}
          onStop={() => abortRef.current?.abort()}
          busy={running}
          disabled={!me.key_configured}
          placeholder={
            me.key_configured ? "Ask about this chat's documents…" : "Add an API key in Settings…"
          }
        />
      </main>

      {kbOpen && activeChatId && (
        <KnowledgeBaseModal
          chatId={activeChatId}
          documents={documents}
          onClose={() => setKbOpen(false)}
          onChange={setDocuments}
        />
      )}
    </div>
  );
}
