"""Register, login, logout, password change, delete account, /api/me."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from . import auth, db

bp = Blueprint("auth", __name__, url_prefix="/api")


@bp.post("/auth/register")
def register():
    payload = request.get_json(silent=True) or {}
    login_id = str(payload.get("login_id", "")).strip()
    password = str(payload.get("password", ""))

    error = auth.validate_login_id(login_id) or auth.validate_password(password)
    if error:
        return jsonify({"error": error}), 400
    if db.login_id_taken(login_id):
        return jsonify({"error": "That login id is already taken"}), 409

    user = db.create_user(login_id, auth.hash_password(password))
    token, token_hash = auth.new_session_token()
    db.create_session(user["id"], token_hash)

    response = jsonify(user)
    auth.set_session_cookie(response, token)
    return response, 201


@bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    login_id = str(payload.get("login_id", "")).strip()
    password = str(payload.get("password", ""))

    user_row = db.get_user_by_login(login_id)
    if user_row is None:
        auth.dummy_verify(password)
        return jsonify({"error": "Invalid login id or password"}), 401
    if not auth.verify_password(user_row["password_hash"], password):
        return jsonify({"error": "Invalid login id or password"}), 401

    token, token_hash = auth.new_session_token()
    db.create_session(str(user_row["id"]), token_hash)
    me = db.me_payload(str(user_row["id"]))

    response = jsonify(me)
    auth.set_session_cookie(response, token)
    return response


@bp.post("/auth/logout")
def logout():
    session_id = getattr(g, "session_id", None)
    if session_id:
        db.delete_session(session_id)
    response = jsonify({"ok": True})
    auth.clear_session_cookie(response)
    return response


@bp.post("/auth/password")
def change_password():
    payload = request.get_json(silent=True) or {}
    current_password = str(payload.get("current_password", ""))
    new_password = str(payload.get("new_password", ""))

    error = auth.validate_password(new_password)
    if error:
        return jsonify({"error": error}), 400

    user_id = g.user["id"]
    user_row = db.get_user_by_id(user_id)
    if user_row is None or not auth.verify_password(user_row["password_hash"], current_password):
        return jsonify({"error": "Current password is wrong"}), 401

    db.set_password_hash(user_id, auth.hash_password(new_password))
    db.delete_other_sessions(user_id, g.session_id)
    return jsonify({"ok": True})


@bp.delete("/auth/account")
def delete_account():
    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", ""))

    user_id = g.user["id"]
    user_row = db.get_user_by_id(user_id)
    if user_row is None or not auth.verify_password(user_row["password_hash"], password):
        return jsonify({"error": "Password is wrong"}), 401

    db.delete_user(user_id)
    response = jsonify({"ok": True})
    auth.clear_session_cookie(response)
    return response


@bp.get("/me")
def me():
    return jsonify(db.me_payload(g.user["id"]))
