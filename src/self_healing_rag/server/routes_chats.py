"""Chat CRUD and the streaming message endpoint."""

from __future__ import annotations

from flask import Blueprint, Response, g, jsonify, request

from . import db
from .runner import stream_turn
from .settings_load import load_turn_secrets

bp = Blueprint("chats", __name__, url_prefix="/api/chats")

MAX_TITLE_LENGTH = 120


@bp.get("")
def list_chats():
    return jsonify({"chats": db.list_chats(g.user["id"])})


@bp.post("")
def create_chat():
    return jsonify(db.create_chat(g.user["id"])), 201


@bp.get("/<chat_id>")
def get_chat(chat_id: str):
    chat = db.get_chat(g.user["id"], chat_id)
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404
    return jsonify(chat)


@bp.patch("/<chat_id>")
def rename_chat(chat_id: str):
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    if not title:
        return jsonify({"error": "A non-empty title is required"}), 400
    chat = db.rename_chat(g.user["id"], chat_id, title[:MAX_TITLE_LENGTH])
    if chat is None:
        return jsonify({"error": "Chat not found"}), 404
    return jsonify(chat)


@bp.delete("/<chat_id>")
def delete_chat(chat_id: str):
    if not db.delete_chat(g.user["id"], chat_id):
        return jsonify({"error": "Chat not found"}), 404
    return "", 204


@bp.post("/<chat_id>/messages")
def post_message(chat_id: str):
    payload = request.get_json(silent=True) or {}
    content = str(payload.get("content", "")).strip()
    user_id = g.user["id"]

    if not content:
        return jsonify({"error": "A non-empty message is required"}), 400
    if not db.chat_exists(user_id, chat_id):
        return jsonify({"error": "Chat not found"}), 404

    settings, api_key = load_turn_secrets(user_id)
    if not api_key:
        return jsonify({"error": "Add an OpenRouter API key in Settings first"}), 400

    return Response(
        stream_turn(user_id, chat_id, content, settings, api_key),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
