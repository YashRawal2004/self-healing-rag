"""Flask backend for the Self-Healing RAG web UI.

Run from the project root:  uv run self-healing-rag-server
"""

from __future__ import annotations

import sys

from flask import Flask, g, jsonify, request
from flask_cors import CORS

from self_healing_rag.config import (
    ALLOWED_ORIGINS,
    MAX_UPLOAD_BYTES,
    SERVER_HOST,
    SERVER_PORT,
    SESSION_COOKIE_NAME,
)
from self_healing_rag.postgres import init_pool

from . import db
from .auth import clear_session_cookie
from .routes_auth import bp as auth_bp
from .routes_chats import bp as chats_bp
from .routes_documents import bp as documents_bp
from .routes_settings import bp as settings_bp

_PUBLIC_EXACT = {
    "/api/health",
    "/api/auth/register",
    "/api/auth/login",
}


def _make_stdout_unicode_safe() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def create_app() -> Flask:
    _make_stdout_unicode_safe()
    init_pool()

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    app.json.ensure_ascii = False

    CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

    app.register_blueprint(auth_bp)
    app.register_blueprint(chats_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(settings_bp)

    @app.before_request
    def load_session():
        g.user = None
        g.session_id = None
        if not request.path.startswith("/api/"):
            return None

        token = request.cookies.get(SESSION_COOKIE_NAME)
        if token:
            session = db.lookup_session(token)
            if session:
                g.user = {"id": session["user_id"], "login_id": session["login_id"]}
                g.session_id = session["session_id"]

        if request.path in _PUBLIC_EXACT or request.method == "OPTIONS":
            return None
        if g.user is None:
            response = jsonify({"error": "Not signed in"})
            clear_session_cookie(response)
            return response, 401
        return None

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.errorhandler(413)
    def too_large(_):
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        return jsonify({"error": f"Upload exceeds the {limit_mb} MB limit"}), 413

    @app.errorhandler(Exception)
    def unhandled(exc):
        from werkzeug.exceptions import HTTPException

        if isinstance(exc, HTTPException):
            return exc
        return jsonify({"error": "The database connection dropped. Please try again."}), 500

    return app


def main() -> None:
    app = create_app()
    print(f"\n🚀 Self-Healing RAG API on http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"   Allowed origins: {', '.join(ALLOWED_ORIGINS)}\n")
    app.run(host=SERVER_HOST, port=SERVER_PORT, threaded=True, debug=False)


if __name__ == "__main__":
    main()
