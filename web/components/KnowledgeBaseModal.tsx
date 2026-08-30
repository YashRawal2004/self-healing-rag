"use client";

import { useEffect, useRef, useState } from "react";

import { CloseIcon, TrashIcon, UploadIcon } from "./icons";
import { clearDocuments, deleteDocument, uploadDocuments } from "@/lib/api";
import type { ChatDocument } from "@/lib/types";

type Busy = "upload" | "clear" | string | null;

export default function KnowledgeBaseModal({
  chatId,
  documents,
  onClose,
  onChange,
}: {
  chatId: string;
  documents: ChatDocument[];
  onClose: () => void;
  onChange: (documents: ChatDocument[]) => void;
}) {
  const [busy, setBusy] = useState<Busy>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [confirmingClear, setConfirmingClear] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  async function handleFiles(fileList: FileList | File[]) {
    const pdfs = Array.from(fileList).filter((file) => file.name.toLowerCase().endsWith(".pdf"));
    if (pdfs.length === 0) {
      setError("Only PDF files can be ingested.");
      return;
    }
    setBusy("upload");
    setError(null);
    setNote(null);
    try {
      const result = await uploadDocuments(chatId, pdfs);
      onChange(result.documents);
      const chunks = result.ingested.reduce((sum, doc) => sum + doc.chunk_count, 0);
      setNote(
        `Ingested ${chunks} chunk${chunks === 1 ? "" : "s"} from ${result.ingested.length} file${result.ingested.length === 1 ? "" : "s"}. The PDF was discarded; only chunks are kept.`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete(documentId: string) {
    setBusy(documentId);
    setError(null);
    try {
      const result = await deleteDocument(chatId, documentId);
      onChange(result.documents);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(null);
    }
  }

  async function handleClear() {
    setConfirmingClear(false);
    setBusy("clear");
    setError(null);
    try {
      const result = await clearDocuments(chatId);
      onChange(result.documents);
      setNote("This chat's chunks were deleted.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(null);
    }
  }

  const disabled = busy !== null;
  const chunkCount = documents.reduce((sum, doc) => sum + doc.chunk_count, 0);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="kb-title"
        onClick={(event) => event.stopPropagation()}
        className="relative w-full max-w-lg overflow-hidden rounded-xl border border-line bg-canvas shadow-xl"
      >
        <header className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h2 id="kb-title" className="text-sm font-semibold">
            Documents in this chat
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-ink-faint transition-colors hover:bg-raised hover:text-ink"
          >
            <CloseIcon />
          </button>
        </header>

        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">
          <div className="mb-4">
            <div className="mb-2 flex items-baseline justify-between">
              <span className="text-xs font-medium text-ink-muted">Uploaded here</span>
              <span className="text-xs text-ink-faint">
                {chunkCount} chunk{chunkCount === 1 ? "" : "s"}
              </span>
            </div>

            {documents.length > 0 ? (
              <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
                {documents.map((file) => (
                  <li
                    key={file.id}
                    className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
                  >
                    <span className="min-w-0 truncate" title={file.filename}>
                      {file.filename}
                    </span>
                    <span className="flex shrink-0 items-center gap-2">
                      <span className="text-xs text-ink-faint">{file.chunk_count}</span>
                      <button
                        type="button"
                        disabled={disabled}
                        onClick={() => void handleDelete(file.id)}
                        className="text-ink-faint hover:text-danger disabled:opacity-40"
                        aria-label={`Delete ${file.filename}`}
                      >
                        <TrashIcon className="h-3.5 w-3.5" />
                      </button>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-lg border border-dashed border-line px-3 py-4 text-center text-xs text-ink-faint">
                Empty — upload a PDF. Other chats cannot see these chunks.
              </p>
            )}
          </div>

          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              if (!disabled) void handleFiles(event.dataTransfer.files);
            }}
            className={`mb-4 rounded-lg border border-dashed px-4 py-6 text-center transition-colors ${
              dragging ? "border-accent bg-raised" : "border-line"
            }`}
          >
            <UploadIcon className="mx-auto mb-2 h-5 w-5 text-ink-faint" />
            <p className="text-sm text-ink-muted">
              Drop PDFs here, or{" "}
              <button
                type="button"
                disabled={disabled}
                onClick={() => fileInputRef.current?.click()}
                className="text-accent underline underline-offset-2 disabled:opacity-50"
              >
                browse
              </button>
            </p>
            <p className="mt-1 text-[0.6875rem] text-ink-faint">
              Parsed in memory. Only chunks are stored for this chat.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              hidden
              onChange={(event) => {
                if (event.target.files?.length) void handleFiles(event.target.files);
                event.target.value = "";
              }}
            />
          </div>

          <button
            type="button"
            disabled={disabled || documents.length === 0}
            onClick={() => setConfirmingClear(true)}
            className="flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm text-danger transition-colors hover:bg-raised disabled:opacity-50"
          >
            <TrashIcon className="h-3.5 w-3.5" />
            Clear this chat
          </button>

          {busy && (
            <p className="mt-3 animate-pulse text-xs text-ink-muted">
              {busy === "upload" ? "Uploading and embedding…" : "Working…"}
            </p>
          )}
          {note && <p className="mt-3 text-xs text-ink-muted">{note}</p>}
          {error && <p className="mt-3 text-xs text-danger">{error}</p>}
        </div>

        {confirmingClear && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-sm rounded-xl border border-line bg-canvas p-5 shadow-xl">
              <h3 className="text-sm font-semibold">Clear this chat&apos;s documents?</h3>
              <p className="mt-2 text-xs leading-relaxed text-ink-muted">
                Chunks for this chat are deleted. Other chats are not touched. You will need to
                upload the PDF again.
              </p>
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setConfirmingClear(false)}
                  className="rounded-lg border border-line px-3 py-1.5 text-sm transition-colors hover:bg-raised"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => void handleClear()}
                  className="rounded-lg bg-danger px-3 py-1.5 text-sm text-white"
                >
                  Clear it
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
