# Self-Healing RAG

A multi-user document Q&A app whose retrieval loop **grades its own work and retries** instead of silently answering from bad context.

You upload a PDF into a chat, ask questions, and watch the loop in the UI: search → grade chunks → rewrite the query if they are irrelevant → generate → grade the answer → regenerate if it hallucinated. Retry budgets are fixed, so a turn always ends as a good answer, a **best-effort** answer with a caveat, or a **fallback** that admits nothing relevant was found.

Each account has its own login, chats, encrypted OpenRouter key, and settings (models, prompts, retries). Chunks uploaded in chat 1 are **not** visible to chat 2. PDF bytes are never stored — only chunks, embeddings, and catalog metadata in Neon Postgres + pgvector.

---

## What problem this solves

Plain RAG fails in two quiet ways:

1. The retriever returns the wrong chunks, and the model still writes a fluent answer.
2. The model adds facts that were not in those chunks.

This project makes both failures **visible and bounded**. A grader looks at the chunks; if they do not match the question, the query is rewritten and search runs again. A second grader looks at the drafted answer; if it is ungrounded or incomplete, generation or retrieval runs again. When the budget is spent, the UI shows that instead of pretending.

---

## Architecture

```
  +-----------+        HTTP / SSE         +-----------+
  |  Browser  |  ---------------------->  |  Next.js  |
  |           |     localhost:3000        |   web/    |
  +-----------+                           +-----+-----+
                                                |
                                                |  /api/* rewrite
                                                |  (session cookie
                                                |   stays first-party)
                                                v
                                          +-----+-----+
                                          |   Flask   |
                                          |  :5000    |
                                          +-----+-----+
                                                |
               +--------------------------------+--------------------------------+
               |                                |                                |
               v                                v                                v
        +------+------+                 +------+------+                 +------+------+
        |    Auth     |                 |    Agent    |                 |  Documents  |
        |  sessions   |                 |  (ReAct)    |                 |  PDF ingest |
        |  settings   |                 |  1 tool:    |                 |  in-memory  |
        |  API keys   |                 |  ask_docs   |                 |  then drop  |
        +------+------+                 +------+------+                 +------+------+
               |                                |                                |
               |                                v                                |
               |                        +------+------+                          |
               |                        | Self-heal   |                          |
               |                        | LangGraph   |                          |
               |                        | retrieve /  |                          |
               |                        | grade /     |                          |
               |                        | rewrite /   |                          |
               |                        | generate    |                          |
               |                        +------+------+                          |
               |                                |                                |
               +--------------------------------+--------------------------------+
                                                |
                                                v
                                   +------------------------+
                                   |   Neon Postgres        |
                                   |   + pgvector           |
                                   |                        |
                                   |  users  sessions       |
                                   |  settings  api_keys    |
                                   |  chats  messages       |
                                   |  documents (catalog)   |
                                   |  chunks + embeddings   |
                                   +------------------------+
```

The browser never talks to Flask on `:5000` directly. Next.js proxies `/api` so the login cookie is first-party on `localhost:3000`.

---

## Self-healing loop

```
                    +-----------+
                    | retrieve  |
                    +-----+-----+
                          |
                          v
                  +-------+--------+
                  | grade documents|
                  +-------+--------+
                          |
            relevant      |      irrelevant / empty
         +----------------+------------------+
         |                                   |
         v                                   v
  +------+------+                    budget left? ----no----> fallback
  |  generate   |                          |
  +------+------+                         yes
         |                                 |
         v                                 v
  +------+------+                    +-----+------+
  | grade answer|                    | transform  |
  +------+------+                    | query      |
         |                           +-----+------+
         |                                 |
         |                                 v
         |                           (back to retrieve)
         |
         +-- good --------------------------> done
         |
         +-- hallucinated, budget left -----> generate again
         |
         +-- incomplete, budget left ------> transform query
         |
         +-- budget spent -----------------> best effort
```

Default budgets (each user can change them in Settings):

| Budget | Default | Used for |
| --- | --- | --- |
| Retrieval retries | 3 | Irrelevant chunks → rewrite query → search again |
| Generation retries | 2 | Ungrounded answer → regenerate from the same context |

Embedding model is **pinned** to `openai/text-embedding-3-small` (1536 dimensions). LLM stages (agent, graders, generate, rewrite) are per-user OpenRouter model ids.

---

## Isolation

```
 user A
   |
   +-- chat 1  ----  PDF A chunks     <--- questions here only see A
   |
   +-- chat 2  ----  PDF B chunks     <--- questions here only see B

 user B cannot see user A's chats, keys, or vectors
```

Upload is scoped to the **active chat**. The original PDF is parsed in a tempfile and discarded.

---

## Repository layout

```
.
├── README.md
├── pyproject.toml          # Python package + uv
├── uv.lock
├── .env.example            # copy to .env (gitignored)
├── db/
│   └── schema.sql          # apply once to Neon
├── src/self_healing_rag/
│   ├── config.py           # code defaults
│   ├── settings_schema.py  # per-user models / prompts / budgets
│   ├── postgres.py         # Neon pool
│   ├── crypto.py           # AES-GCM for OpenRouter keys
│   ├── agent/              # ReAct agent + ask_documents tool
│   ├── rag/                # LangGraph self-healing loop
│   └── server/             # Flask API
└── web/                    # Next.js UI
```

Do **not** commit `.env`. `uv.lock` and `web/package-lock.json` should be committed.

---

## Prerequisites

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)
- Node.js **20.9+**
- A [Neon](https://console.neon.tech) project (Postgres + pgvector)
- An [OpenRouter](https://openrouter.ai) key (pasted in the UI, not in `.env`)
- Optional: `psql` to apply the schema from the terminal (the Neon SQL Editor also works)

---

## Setup

### 1. Clone and install the backend

```bash
git clone <your-repo-url>
cd "Self-Healing RAG"    # or whatever you named the folder

uv sync
```

### 2. Create a Neon database

1. New project at [console.neon.tech](https://console.neon.tech).
2. Open **Connection Details**.
3. Copy **two** URIs (same user, password, and database name; only the host differs):

| Variable | Which string | Host contains | Used for |
| --- | --- | --- | --- |
| `DATABASE_URL` | Pooled | `-pooler` | Flask at runtime |
| `DATABASE_URL_DIRECT` | Direct (pooled **off**) | no `-pooler` | Applying `db/schema.sql` once |

If the console only shows one string, the direct host is the pooled host with `-pooler` removed.

### 3. Environment file

```bash
# Windows (PowerShell)
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env`:

```
DATABASE_URL=postgresql://...-pooler.../yourdb?sslmode=require
DATABASE_URL_DIRECT=postgresql://.../yourdb?sslmode=require
ENCRYPTION_KEY=
```

Generate `ENCRYPTION_KEY` (64 hex characters). This encrypts each user's OpenRouter key at rest:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as `ENCRYPTION_KEY`. Do not put an OpenRouter key in `.env`.

### 4. Apply the schema

Use the **direct** URL, not the pooled one:

```bash
# Windows PowerShell
psql $env:DATABASE_URL_DIRECT -f db/schema.sql

# macOS / Linux (after: set -a; source .env; set +a)
psql "$DATABASE_URL_DIRECT" -f db/schema.sql
```

Or paste the contents of `db/schema.sql` into the Neon **SQL Editor** and run it.

You should see tables: `users`, `sessions`, `user_api_keys`, `user_settings`, `chats`, `messages`, `documents`, `chunks`.

### 5. Frontend

```bash
cd web
npm install
cd ..
```

---

## Run

Two terminals, from the project root:

```bash
# Terminal 1 — API
uv run self-healing-rag-server
```

```bash
# Terminal 2 — UI
cd web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

1. Register a login id (letters, digits, underscore; no email).
2. **Settings** → paste your OpenRouter API key.
3. Open **Documents** (or **Upload a PDF** on the empty chat) and drop a PDF.
4. Ask a question. The live trace shows each step of the loop.

Sessions last **3 idle days** (`shr_session` HttpOnly cookie). Settings (models, prompts, chunk size, retries) apply to **every chat** for that user. Changing chunk size does not rewrite old chunks — re-upload the PDF.

---

## How a turn is stored

```
POST /api/chats/:id/messages
        |
        |  SSE: user → title? → step* → answer|error → done
        v
  messages row          (answer text + JSON trace)
  chunks queried        (WHERE chat_id AND user_id)
```

Stopping the stream in the UI only stops watching. The agent still finishes and saves.

---

## API (cookie required except health / register / login)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Process is up |
| POST | `/api/auth/register` | `{ login_id, password }` |
| POST | `/api/auth/login` | `{ login_id, password }` |
| POST | `/api/auth/logout` | Drop this session |
| POST | `/api/auth/password` | `{ current_password, new_password }` |
| DELETE | `/api/auth/account` | `{ password }` — hard delete |
| GET | `/api/me` | Login id + whether a key is saved |
| GET / PUT | `/api/settings` | Models, prompts, retrieval, budgets |
| PUT / DELETE | `/api/settings/key` | Encrypted OpenRouter key |
| GET / POST / PATCH / DELETE | `/api/chats` | Chats |
| POST | `/api/chats/:id/messages` | SSE turn |
| GET / POST / DELETE | `/api/chats/:id/documents` | This chat's PDFs → chunks |

---

## Configuration

Code defaults: `src/self_healing_rag/config.py` and the prompt files under `rag/` and `agent/`. On register those defaults are copied into `user_settings`. The UI **Settings** page edits that row.

Five LLM model fields are free-text OpenRouter ids and are checked against OpenRouter on save. Embedding is not user-editable.

---

