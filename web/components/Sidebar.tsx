"use client";

import Link from "next/link";

import ChatListItem from "./ChatListItem";
import { BooksIcon, GearIcon, LogoutIcon, PlusIcon } from "./icons";
import type { ChatSummary, Me } from "@/lib/types";

export default function Sidebar({
  me,
  chats,
  activeChatId,
  documentCount,
  onNewChat,
  onSelectChat,
  onRenameChat,
  onDeleteChat,
  onOpenKb,
  onLogout,
}: {
  me: Me;
  chats: ChatSummary[];
  activeChatId: string | null;
  documentCount: number | null;
  onNewChat: () => void;
  onSelectChat: (chatId: string) => void;
  onRenameChat: (chatId: string, title: string) => void;
  onDeleteChat: (chatId: string) => void;
  onOpenKb: () => void;
  onLogout: () => void;
}) {
  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-line bg-panel">
      <div className="px-3 py-3">
        <div className="mb-3 px-1">
          <h1 className="text-sm font-semibold">Self-Healing RAG</h1>
          <p className="text-[0.6875rem] text-ink-faint">{me.login_id}</p>
        </div>

        <button
          type="button"
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-lg border border-line px-2.5 py-2 text-sm text-ink transition-colors hover:bg-raised"
        >
          <PlusIcon className="h-4 w-4" />
          New chat
        </button>
      </div>

      <nav className="group/list min-h-0 flex-1 space-y-0.5 overflow-y-auto px-3 pb-3">
        {chats.length === 0 ? (
          <p className="px-2.5 py-2 text-xs text-ink-faint">No chats yet.</p>
        ) : (
          chats.map((chat) => (
            <ChatListItem
              key={chat.id}
              chat={chat}
              active={chat.id === activeChatId}
              onSelect={() => onSelectChat(chat.id)}
              onRename={(title) => onRenameChat(chat.id, title)}
              onDelete={() => onDeleteChat(chat.id)}
            />
          ))
        )}
      </nav>

      <div className="space-y-0.5 border-t border-line p-3">
        <button
          type="button"
          onClick={onOpenKb}
          title="Upload PDFs for this chat"
          className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm text-ink-muted transition-colors hover:bg-raised hover:text-ink"
        >
          <BooksIcon className="h-4 w-4" />
          <span className="flex-1">Documents</span>
          {documentCount !== null && (
            <span className="text-[0.6875rem] text-ink-faint">{documentCount}</span>
          )}
        </button>
        <Link
          href="/settings"
          className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-ink-muted transition-colors hover:bg-raised hover:text-ink"
        >
          <GearIcon className="h-4 w-4" />
          Settings
        </Link>
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm text-ink-muted transition-colors hover:bg-raised hover:text-ink"
        >
          <LogoutIcon className="h-4 w-4" />
          Log out
        </button>
      </div>
    </aside>
  );
}
