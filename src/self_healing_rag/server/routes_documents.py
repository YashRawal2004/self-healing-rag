"""Per-chat document catalog. PDFs are parsed in memory and never stored."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from werkzeug.utils import secure_filename

from . import db
from .ingest_pdf import DuplicateDocument, ingest_pdf_bytes
from .settings_load import load_turn_secrets

bp = Blueprint("documents", __name__, url_prefix="/api/chats")


@bp.get("/<chat_id>/documents")
def list_documents(chat_id: str):
    if not db.chat_exists(g.user["id"], chat_id):
        return jsonify({"error": "Chat not found"}), 404
    return jsonify({"documents": db.list_documents(g.user["id"], chat_id)})


@bp.post("/<chat_id>/documents")
def upload_documents(chat_id: str):
    user_id = g.user["id"]
    if not db.chat_exists(user_id, chat_id):
        return jsonify({"error": "Chat not found"}), 404

    settings, api_key = load_turn_secrets(user_id)
    if not api_key:
        return jsonify({"error": "Add an OpenRouter API key in Settings first"}), 400

    uploads = [f for f in request.files.getlist("files") if f and f.filename]
    if not uploads:
        return jsonify({"error": "No files were uploaded"}), 400

    ingested = []
    for upload in uploads:
        if not upload.filename.lower().endswith(".pdf"):
            return jsonify({"error": f"Not a PDF: {upload.filename}"}), 400
        name = secure_filename(upload.filename) or "document.pdf"
        data = upload.read()
        if not data:
            return jsonify({"error": f"Empty file: {upload.filename}"}), 400
        try:
            ingested.append(
                ingest_pdf_bytes(user_id, chat_id, name, data, api_key, settings)
            )
        except DuplicateDocument:
            return jsonify({"error": f"Already ingested in this chat: {name}"}), 409
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    return jsonify({"documents": db.list_documents(user_id, chat_id), "ingested": ingested}), 201


@bp.delete("/<chat_id>/documents/<document_id>")
def delete_document(chat_id: str, document_id: str):
    user_id = g.user["id"]
    if not db.chat_exists(user_id, chat_id):
        return jsonify({"error": "Chat not found"}), 404
    if not db.delete_document(user_id, chat_id, document_id):
        return jsonify({"error": "Document not found"}), 404
    return jsonify({"documents": db.list_documents(user_id, chat_id)})


@bp.delete("/<chat_id>/documents")
def clear_documents(chat_id: str):
    user_id = g.user["id"]
    if not db.chat_exists(user_id, chat_id):
        return jsonify({"error": "Chat not found"}), 404
    db.clear_documents(user_id, chat_id)
    return jsonify({"documents": []})
