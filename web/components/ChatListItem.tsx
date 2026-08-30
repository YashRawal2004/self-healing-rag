"use client";

import { useEffect, useRef, useState } from "react";

import { MoreIcon, PencilIcon, TrashIcon } from "./icons";
import type { ChatSummary } from "@/lib/types";

export default function ChatListItem({
  chat,
  active,
  onSelect,
  onRename,
  onDelete,
}: {
  chat: ChatSummary;
  active: boolean;
  onSelect: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(chat.title);

  const inputRef = useRef<HTMLInputElement>(null);
  const rowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  // Close the menu on an outside click or Escape, the way a menu is expected to.
  useEffect(() => {
    if (!menuOpen) return;

    function onPointerDown(event: PointerEvent) {
      if (!rowRef.current?.contains(event.target as Node)) setMenuOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  function startEditing() {
    setDraft(chat.title);
    setEditing(true);
    setMenuOpen(false);
  }

  function commit() {
    const trimmed = draft.trim();
    // An empty title would leave an unclickable blank row in the sidebar.
    if (trimmed && trimmed !== chat.title) onRename(trimmed);
    setEditing(false);
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        autoFocus
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            commit();
          } else if (event.key === "Escape") {
            event.preventDefault();
            setEditing(false);
          }
        }}
        aria-label="Chat title"
        className="w-full rounded-lg border border-accent bg-canvas px-2.5 py-2 text-sm outline-none"
      />
    );
  }

  return (
    <div ref={rowRef} className="relative">
      <button
        type="button"
        onClick={onSelect}
        onDoubleClick={startEditing}
        title={chat.title}
        className={`flex w-full items-center rounded-lg py-2 pl-2.5 pr-8 text-left text-sm transition-colors ${
          active ? "bg-raised text-ink" : "text-ink-muted hover:bg-raised/60 hover:text-ink"
        }`}
      >
        <span className="truncate">{chat.title}</span>
      </button>

      <button
        type="button"
        onClick={() => setMenuOpen((previous) => !previous)}
        aria-label={`Options for ${chat.title}`}
        aria-expanded={menuOpen}
        // Hidden until hover keeps the list quiet, but focus-visible keeps it
        // reachable by keyboard.
        className={`absolute right-1 top-1/2 -translate-y-1/2 rounded p-1 text-ink-faint transition-opacity hover:bg-line hover:text-ink focus-visible:opacity-100 ${
          menuOpen || active ? "opacity-100" : "opacity-0 group-hover/list:opacity-100"
        }`}
      >
        <MoreIcon className="h-3.5 w-3.5" />
      </button>

      {menuOpen && (
        <div
          role="menu"
          className="absolute right-1 top-full z-20 mt-1 w-40 overflow-hidden rounded-lg border border-line bg-canvas py-1 shadow-lg"
        >
          <button
            type="button"
            role="menuitem"
            onClick={startEditing}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-ink hover:bg-raised"
          >
            <PencilIcon className="h-3.5 w-3.5" />
            Rename
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setMenuOpen(false);
              onDelete();
            }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-danger hover:bg-raised"
          >
            <TrashIcon className="h-3.5 w-3.5" />
            Delete
          </button>
        </div>
      )}
    </div>
  );
}
