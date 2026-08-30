import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# src/self_healing_rag/config.py → project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# ── LLM defaults (copied into user_settings on register) ──
LLM_MODEL = "openai/gpt-4o-mini"
MAIN_AGENT_MODEL = "openai/gpt-4o-mini"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Pinned for everyone — column type is vector(1536).
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMS = 1536

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4

MAX_RETRIEVAL_RETRIES = 3
MAX_GENERATION_RETRIES = 2
RAG_RECURSION_LIMIT = 50

# ── Web server ───────────────────────────────────────
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
MAX_UPLOAD_BYTES = 32 * 1024 * 1024
AUTO_TITLE_LENGTH = 48

# ── Neon + secrets ───────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

SESSION_COOKIE_NAME = "shr_session"
SESSION_TTL = timedelta(days=3)

LOGIN_ID_PATTERN = r"^[a-zA-Z0-9_]{3,32}$"
MIN_PASSWORD_LENGTH = 8
