"""Parse an uploaded PDF in a tempfile, embed, store chunks. Bytes are discarded."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from psycopg.errors import UniqueViolation

from self_healing_rag.config import EMBEDDING_MODEL, OPENROUTER_BASE_URL
from self_healing_rag.settings_schema import UserSettings

from . import db


class DuplicateDocument(Exception):
    pass


def ingest_pdf_bytes(
    user_id: str,
    chat_id: str,
    filename: str,
    data: bytes,
    api_key: str,
    settings: UserSettings,
) -> dict:
    sha256 = hashlib.sha256(data).hexdigest()
    if db.document_exists_hash(user_id, chat_id, sha256):
        raise DuplicateDocument(filename)

    retrieval = settings.retrieval
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        pages = PyPDFLoader(tmp_path).load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=retrieval.chunk_size,
            chunk_overlap=retrieval.chunk_overlap,
            length_function=len,
        )
        pieces = splitter.split_documents(pages)
        texts = [piece.page_content for piece in pieces]
        if not texts:
            raise ValueError(f"No text could be extracted from {filename}")

        embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
        )
        vectors = embeddings.embed_documents(texts)

        rows = []
        for index, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
            metadata = {
                "source": filename,
                "page": piece.metadata.get("page"),
            }
            rows.append(
                {
                    "chunk_index": index,
                    "content": piece.page_content,
                    "embedding": vector,
                    "metadata": metadata,
                }
            )

        try:
            return db.insert_document_with_chunks(
                user_id=user_id,
                chat_id=chat_id,
                filename=filename,
                page_count=len(pages),
                sha256=sha256,
                chunks=rows,
            )
        except UniqueViolation as exc:
            raise DuplicateDocument(filename) from exc
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
            # Windows sometimes keeps a handle until GC; ignore leftover.
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
