"""Load decrypted key + settings for a turn. Used by routes and the runner."""

from __future__ import annotations

from self_healing_rag.crypto import decrypt_secret
from self_healing_rag.settings_schema import UserSettings

from . import db


def decrypted_key(user_id: str) -> str | None:
    row = db.get_api_key_row(user_id)
    if row is None:
        return None
    return decrypt_secret(bytes(row["ciphertext"]), bytes(row["nonce"]))


def load_turn_secrets(user_id: str) -> tuple[UserSettings, str | None]:
    return db.get_settings(user_id), decrypted_key(user_id)
