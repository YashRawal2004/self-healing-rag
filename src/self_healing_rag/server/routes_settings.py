"""Per-user settings and OpenRouter key."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

from self_healing_rag.crypto import decrypt_secret, encrypt_secret, key_hint

from . import db
from .openrouter import unknown_models
from .settings_load import decrypted_key
from self_healing_rag.settings_schema import parse_settings

bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@bp.get("")
def get_settings():
    return jsonify(db.get_settings(g.user["id"]).model_dump())


@bp.put("")
def put_settings():
    payload = request.get_json(silent=True) or {}
    try:
        settings = parse_settings(payload)
    except ValidationError as exc:
        return jsonify({"error": _first_error(exc)}), 400

    api_key = decrypted_key(g.user["id"])
    if not api_key:
        return jsonify({"error": "Add an OpenRouter API key before saving models"}), 400

    try:
        bad = unknown_models(api_key, settings.models.model_dump())
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400

    if bad:
        field, model_id = next(iter(bad.items()))
        return jsonify({"error": f"Unknown OpenRouter model for {field}: {model_id}"}), 400

    saved = db.save_settings(g.user["id"], settings)
    return jsonify(saved.model_dump())


@bp.put("/key")
def put_key():
    payload = request.get_json(silent=True) or {}
    api_key = str(payload.get("api_key", "")).strip()
    if not api_key:
        return jsonify({"error": "api_key is required"}), 400

    ciphertext, nonce = encrypt_secret(api_key)
    db.upsert_api_key(g.user["id"], ciphertext, nonce, key_hint(api_key))
    return jsonify({"key_configured": True, "key_hint": key_hint(api_key)})


@bp.delete("/key")
def delete_key():
    db.delete_api_key(g.user["id"])
    return jsonify({"key_configured": False, "key_hint": None})


def _first_error(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Invalid settings"
    err = errors[0]
    loc = ".".join(str(part) for part in err.get("loc", ()))
    msg = err.get("msg", "invalid")
    return f"{loc}: {msg}" if loc else msg
