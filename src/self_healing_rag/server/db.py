"""Postgres persistence for users, sessions, chats, messages, settings, keys."""

from __future__ import annotations

import json
from typing import Any

from psycopg.types.json import Jsonb

from self_healing_rag.config import AUTO_TITLE_LENGTH, SESSION_TTL
from self_healing_rag.postgres import connection, retry_on_disconnect
from self_healing_rag.settings_schema import UserSettings, default_settings, parse_settings

from .auth import as_iso, as_str, hash_token, now


def _uid(value: Any) -> str:
    return as_str(value)


def _as_vector(values: list[float]) -> str:
    """pgvector text form. A Python list is sent as float[] and <=> will not apply."""
    return "[" + ",".join(repr(float(x)) for x in values) + "]"


@retry_on_disconnect
def ping() -> None:
    with connection() as conn:
        conn.execute("SELECT 1")


# ── Users ────────────────────────────────────────────────────────────────────

@retry_on_disconnect
def create_user(login_id: str, password_hash: str) -> dict:
    settings = default_settings().model_dump()
    with connection() as conn:
        user = conn.execute(
            """
            INSERT INTO users (login_id, password_hash)
            VALUES (%s, %s)
            RETURNING id, login_id, created_at
            """,
            (login_id, password_hash),
        ).fetchone()
        conn.execute(
            "INSERT INTO user_settings (user_id, settings) VALUES (%s, %s)",
            (user["id"], Jsonb(settings)),
        )
    return _user_public(user, key_configured=False, key_hint=None)


@retry_on_disconnect
def get_user_by_login(login_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT id, login_id, password_hash FROM users WHERE login_id = %s",
            (login_id,),
        ).fetchone()
    return dict(row) if row else None


@retry_on_disconnect
def get_user_by_id(user_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT id, login_id, password_hash FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


@retry_on_disconnect
def login_id_taken(login_id: str) -> bool:
    with connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE login_id = %s", (login_id,)
        ).fetchone()
    return row is not None


def set_password_hash(user_id: str, password_hash: str) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = %s, updated_at = now() WHERE id = %s",
            (password_hash, user_id),
        )


def delete_user(user_id: str) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))


def me_payload(user_id: str) -> dict:
    with connection() as conn:
        user = conn.execute(
            "SELECT id, login_id, created_at FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
        key = conn.execute(
            """
            SELECT key_hint FROM user_api_keys
            WHERE user_id = %s AND provider = 'openrouter'
            """,
            (user_id,),
        ).fetchone()
    return _user_public(
        user,
        key_configured=key is not None,
        key_hint=key["key_hint"] if key else None,
    )


def _user_public(user: dict, key_configured: bool, key_hint: str | None) -> dict:
    return {
        "id": _uid(user["id"]),
        "login_id": user["login_id"],
        "created_at": as_iso(user.get("created_at")) if user.get("created_at") else None,
        "key_configured": key_configured,
        "key_hint": key_hint,
    }


# ── Sessions ─────────────────────────────────────────────────────────────────

@retry_on_disconnect
def create_session(user_id: str, token_hash: str) -> str:
    expires = now() + SESSION_TTL
    with connection() as conn:
        row = conn.execute(
            """
            INSERT INTO sessions (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_id, token_hash, expires),
        ).fetchone()
    return _uid(row["id"])


@retry_on_disconnect
def lookup_session(raw_token: str) -> dict | None:
    token_hash = hash_token(raw_token)
    with connection() as conn:
        row = conn.execute(
            """
            SELECT s.id AS session_id, s.expires_at, u.id AS user_id, u.login_id
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = %s AND s.expires_at > now()
            """,
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE sessions SET expires_at = %s WHERE id = %s",
            (now() + SESSION_TTL, row["session_id"]),
        )
    return {
        "session_id": _uid(row["session_id"]),
        "user_id": _uid(row["user_id"]),
        "login_id": row["login_id"],
    }


def delete_session(session_id: str) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM sessions WHERE id = %s", (session_id,))


def delete_other_sessions(user_id: str, keep_session_id: str) -> None:
    with connection() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE user_id = %s AND id <> %s",
            (user_id, keep_session_id),
        )


def delete_all_sessions(user_id: str) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))


# ── Settings + keys ──────────────────────────────────────────────────────────

def get_settings(user_id: str) -> UserSettings:
    with connection() as conn:
        row = conn.execute(
            "SELECT settings FROM user_settings WHERE user_id = %s",
            (user_id,),
        ).fetchone()
    raw = row["settings"] if row else {}
    return parse_settings(raw)


def save_settings(user_id: str, settings: UserSettings) -> UserSettings:
    payload = settings.model_dump()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO user_settings (user_id, settings, updated_at)
            VALUES (%s, %s, now())
            ON CONFLICT (user_id) DO UPDATE
              SET settings = EXCLUDED.settings, updated_at = now()
            """,
            (user_id, Jsonb(payload)),
        )
    return settings


def get_api_key_row(user_id: str, provider: str = "openrouter") -> dict | None:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT ciphertext, nonce, key_hint
            FROM user_api_keys
            WHERE user_id = %s AND provider = %s
            """,
            (user_id, provider),
        ).fetchone()
    return dict(row) if row else None


def upsert_api_key(
    user_id: str,
    ciphertext: bytes,
    nonce: bytes,
    hint: str,
    provider: str = "openrouter",
) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO user_api_keys (user_id, provider, ciphertext, nonce, key_hint)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, provider) DO UPDATE
              SET ciphertext = EXCLUDED.ciphertext,
                  nonce = EXCLUDED.nonce,
                  key_hint = EXCLUDED.key_hint,
                  updated_at = now()
            """,
            (user_id, provider, ciphertext, nonce, hint),
        )


def delete_api_key(user_id: str, provider: str = "openrouter") -> None:
    with connection() as conn:
        conn.execute(
            "DELETE FROM user_api_keys WHERE user_id = %s AND provider = %s",
            (user_id, provider),
        )


# ── Chats ────────────────────────────────────────────────────────────────────

def create_chat(user_id: str, title: str = "New chat") -> dict:
    with connection() as conn:
        row = conn.execute(
            """
            INSERT INTO chats (user_id, title)
            VALUES (%s, %s)
            RETURNING id, user_id, title, title_is_auto, created_at, updated_at
            """,
            (user_id, title),
        ).fetchone()
    chat = _chat_row(row)
    chat["message_count"] = 0
    return chat


def list_chats(user_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.user_id, c.title, c.title_is_auto, c.created_at, c.updated_at,
                   COUNT(m.id)::int AS message_count
            FROM chats c
            LEFT JOIN messages m ON m.chat_id = c.id
            WHERE c.user_id = %s
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [_chat_row(row) for row in rows]


def get_chat(user_id: str, chat_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, title, title_is_auto, created_at, updated_at
            FROM chats WHERE id = %s AND user_id = %s
            """,
            (chat_id, user_id),
        ).fetchone()
    if row is None:
        return None
    messages = get_messages(user_id, chat_id)
    chat = _chat_row(row)
    chat["message_count"] = len(messages)
    chat["messages"] = messages
    return chat


def chat_exists(user_id: str, chat_id: str) -> bool:
    with connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM chats WHERE id = %s AND user_id = %s",
            (chat_id, user_id),
        ).fetchone()
    return row is not None


def rename_chat(user_id: str, chat_id: str, title: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            """
            UPDATE chats
            SET title = %s, title_is_auto = false, updated_at = now()
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, title, title_is_auto, created_at, updated_at
            """,
            (title, chat_id, user_id),
        ).fetchone()
    return _chat_row(row) if row else None


def set_auto_title(user_id: str, chat_id: str, source_text: str) -> str | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT title_is_auto FROM chats WHERE id = %s AND user_id = %s",
            (chat_id, user_id),
        ).fetchone()
        if row is None or not row["title_is_auto"]:
            return None
        collapsed = " ".join(source_text.split())
        title = collapsed[:AUTO_TITLE_LENGTH].rstrip()
        if len(collapsed) > AUTO_TITLE_LENGTH:
            title += "…"
        title = title or "New chat"
        conn.execute(
            "UPDATE chats SET title = %s WHERE id = %s AND user_id = %s",
            (title, chat_id, user_id),
        )
    return title


def delete_chat(user_id: str, chat_id: str) -> bool:
    with connection() as conn:
        row = conn.execute(
            "DELETE FROM chats WHERE id = %s AND user_id = %s RETURNING id",
            (chat_id, user_id),
        ).fetchone()
    return row is not None


def touch_chat(user_id: str, chat_id: str) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE chats SET updated_at = now() WHERE id = %s AND user_id = %s",
            (chat_id, user_id),
        )


# ── Messages ─────────────────────────────────────────────────────────────────

def add_message(
    user_id: str,
    chat_id: str,
    role: str,
    content: str,
    trace: list[dict[str, Any]] | None = None,
) -> dict:
    created = now()
    with connection() as conn:
        row = conn.execute(
            """
            INSERT INTO messages (chat_id, user_id, role, content, trace, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, role, content, trace, created_at
            """,
            (chat_id, user_id, role, content, Jsonb(trace or []), created),
        ).fetchone()
    return _message_row(row)


def get_messages(user_id: str, chat_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, trace, created_at
            FROM messages
            WHERE chat_id = %s AND user_id = %s
            ORDER BY id
            """,
            (chat_id, user_id),
        ).fetchall()
    return [_message_row(row) for row in rows]


def delete_message(user_id: str, message_id: int) -> None:
    with connection() as conn:
        conn.execute(
            "DELETE FROM messages WHERE id = %s AND user_id = %s",
            (message_id, user_id),
        )


# ── Documents / chunks ───────────────────────────────────────────────────────

def list_documents(user_id: str, chat_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.filename, d.page_count, d.status, d.error, d.created_at,
                   COUNT(c.id)::int AS chunk_count
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            WHERE d.chat_id = %s AND d.user_id = %s
            GROUP BY d.id
            ORDER BY d.created_at
            """,
            (chat_id, user_id),
        ).fetchall()
    return [
        {
            "id": _uid(row["id"]),
            "filename": row["filename"],
            "page_count": row["page_count"],
            "status": row["status"],
            "error": row["error"],
            "chunk_count": row["chunk_count"],
            "created_at": as_iso(row["created_at"]),
        }
        for row in rows
    ]


def document_exists_hash(user_id: str, chat_id: str, sha256: str) -> bool:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM documents
            WHERE chat_id = %s AND user_id = %s AND sha256 = %s
            """,
            (chat_id, user_id, sha256),
        ).fetchone()
    return row is not None


def insert_document_with_chunks(
    user_id: str,
    chat_id: str,
    filename: str,
    page_count: int,
    sha256: str,
    chunks: list[dict[str, Any]],
) -> dict:
    """chunks items: {content, embedding, metadata, chunk_index}."""
    with connection() as conn:
        doc = conn.execute(
            """
            INSERT INTO documents (chat_id, user_id, filename, page_count, sha256, status)
            VALUES (%s, %s, %s, %s, %s, 'ingested')
            RETURNING id, filename, page_count, status, created_at
            """,
            (chat_id, user_id, filename, page_count, sha256),
        ).fetchone()
        for chunk in chunks:
            conn.execute(
                """
                INSERT INTO chunks (
                    document_id, chat_id, user_id, chunk_index, content, embedding, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s::vector, %s)
                """,
                (
                    doc["id"],
                    chat_id,
                    user_id,
                    chunk["chunk_index"],
                    chunk["content"],
                    _as_vector(chunk["embedding"]),
                    Jsonb(chunk["metadata"]),
                ),
            )
    return {
        "id": _uid(doc["id"]),
        "filename": doc["filename"],
        "page_count": doc["page_count"],
        "status": doc["status"],
        "chunk_count": len(chunks),
        "created_at": as_iso(doc["created_at"]),
    }


def delete_document(user_id: str, chat_id: str, document_id: str) -> bool:
    with connection() as conn:
        row = conn.execute(
            """
            DELETE FROM documents
            WHERE id = %s AND chat_id = %s AND user_id = %s
            RETURNING id
            """,
            (document_id, chat_id, user_id),
        ).fetchone()
    return row is not None


def clear_documents(user_id: str, chat_id: str) -> int:
    with connection() as conn:
        rows = conn.execute(
            """
            DELETE FROM documents
            WHERE chat_id = %s AND user_id = %s
            RETURNING id
            """,
            (chat_id, user_id),
        ).fetchall()
    return len(rows)


def search_chunks(
    user_id: str,
    chat_id: str,
    query_embedding: list[float],
    top_k: int,
) -> list[dict]:
    with connection() as conn:
        try:
            conn.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
        except Exception:
            pass
        rows = conn.execute(
            """
            SELECT content, metadata
            FROM chunks
            WHERE chat_id = %s AND user_id = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (chat_id, user_id, _as_vector(query_embedding), top_k),
        ).fetchall()
    return [{"content": row["content"], "metadata": row["metadata"] or {}} for row in rows]


# ── Row helpers ──────────────────────────────────────────────────────────────

def _chat_row(row: dict) -> dict:
    chat = {
        "id": _uid(row["id"]),
        "title": row["title"],
        "title_is_auto": bool(row["title_is_auto"]),
        "created_at": as_iso(row["created_at"]),
        "updated_at": as_iso(row["updated_at"]),
    }
    if "message_count" in row:
        chat["message_count"] = row["message_count"]
    return chat


def _message_row(row: dict) -> dict:
    trace = row["trace"] or []
    if isinstance(trace, str):
        trace = json.loads(trace)
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "trace": trace,
        "created_at": as_iso(row["created_at"]),
    }
