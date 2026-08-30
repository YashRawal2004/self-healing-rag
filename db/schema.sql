-- Self-Healing RAG — Neon Postgres + pgvector schema
--
-- 1. Create a project at https://console.neon.tech (one database is enough).
-- 2. In Connection Details copy TWO strings into .env:
--      DATABASE_URL         — pooled  (host contains "-pooler")  → the app
--      DATABASE_URL_DIRECT  — direct  (host has no "-pooler")    → this file
--    Both already include sslmode=require.
-- 3. Apply this file against the DIRECT url, not the pooled one:
--      psql "$DATABASE_URL_DIRECT" -f db/schema.sql
--    or paste the whole file into the Neon SQL Editor.
--
-- Other secrets (not Neon, but required by the app later):
--   ENCRYPTION_KEY  — 64 hex chars, encrypts each user's OpenRouter key
--                     python -c "import secrets; print(secrets.token_hex(32))"
-- OpenRouter keys are stored per user in user_api_keys. They do not go in .env.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ── Identity ──────────────────────────────────────────

CREATE TABLE users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  login_id      text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash text NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX sessions_user_id_idx ON sessions (user_id);
CREATE INDEX sessions_expires_at_idx ON sessions (expires_at);

-- ── Secrets (not JSON settings) ───────────────────────

CREATE TABLE user_api_keys (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider   text NOT NULL,
  ciphertext bytea NOT NULL,
  nonce      bytea NOT NULL,
  key_hint   text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, provider)
);

-- ── Per-user config (applies to every chat) ───────────

CREATE TABLE user_settings (
  user_id    uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  settings   jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- ── Chats + transcript ────────────────────────────────

CREATE TABLE chats (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title         text NOT NULL DEFAULT 'New chat',
  title_is_auto boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id, user_id)
);

CREATE INDEX chats_user_updated_idx ON chats (user_id, updated_at DESC);

CREATE TABLE messages (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  chat_id    uuid NOT NULL,
  user_id    uuid NOT NULL,
  role       text NOT NULL CHECK (role IN ('user', 'assistant')),
  content    text NOT NULL,
  trace      jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (chat_id, user_id) REFERENCES chats(id, user_id) ON DELETE CASCADE
);

CREATE INDEX messages_chat_id_idx ON messages (chat_id, id);

-- ── Documents: catalog only. PDF bytes are never stored. ─

CREATE TABLE documents (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id    uuid NOT NULL,
  user_id    uuid NOT NULL,
  filename   text NOT NULL,
  page_count integer,
  sha256     text,
  status     text NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending', 'ingested', 'failed')),
  error      text,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (chat_id, user_id) REFERENCES chats(id, user_id) ON DELETE CASCADE,
  UNIQUE (id, chat_id, user_id),
  UNIQUE (chat_id, sha256)
);

CREATE INDEX documents_chat_idx ON documents (chat_id);

-- ── Chunks + embeddings (text-embedding-3-small = 1536) ─

CREATE TABLE chunks (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL,
  chat_id     uuid NOT NULL,
  user_id     uuid NOT NULL,
  chunk_index integer NOT NULL,
  content     text NOT NULL,
  embedding   vector(1536) NOT NULL,
  metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (document_id, chat_id, user_id)
    REFERENCES documents(id, chat_id, user_id) ON DELETE CASCADE,
  UNIQUE (document_id, chunk_index)
);

CREATE INDEX chunks_chat_idx ON chunks (chat_id);
CREATE INDEX chunks_user_idx ON chunks (user_id);
CREATE INDEX chunks_embedding_hnsw
  ON chunks USING hnsw (embedding vector_cosine_ops);
