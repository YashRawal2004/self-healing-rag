"""Encrypt per-user OpenRouter keys with AES-GCM.

The master key is ENCRYPTION_KEY in .env (64 hex chars = 32 bytes). Ciphertext
and nonce are stored in user_api_keys; the raw OpenRouter key never hits disk.
"""

from __future__ import annotations

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

from self_healing_rag.config import ENCRYPTION_KEY


def _master_key() -> bytes:
    raw = ENCRYPTION_KEY.strip()
    if len(raw) != 64:
        raise RuntimeError(
            "ENCRYPTION_KEY must be 64 hex characters. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    try:
        key = bytes.fromhex(raw)
    except ValueError as exc:
        raise RuntimeError("ENCRYPTION_KEY must be hex") from exc
    if len(key) != 32:
        raise RuntimeError("ENCRYPTION_KEY must decode to 32 bytes")
    return key


def encrypt_secret(plaintext: str) -> tuple[bytes, bytes]:
    """Return (ciphertext, nonce)."""
    nonce = os.urandom(12)
    ciphertext = AESGCM(_master_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return ciphertext, nonce


def decrypt_secret(ciphertext: bytes, nonce: bytes) -> str:
    return AESGCM(_master_key()).decrypt(nonce, ciphertext, None).decode("utf-8")


def key_hint(api_key: str) -> str:
    trimmed = api_key.strip()
    if len(trimmed) <= 4:
        return trimmed
    return trimmed[-4:]
