"""03-7/03-8: authentication with hashes and server-side authorization."""
import os
from datetime import timedelta
from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash


def create_app(mode="fixed"):
    app = Flask(__name__)
    app.secret_key = os.environ.get("LAB_SECRET_KEY", "lab-only-web-signing-key")
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=10),
    )
    users = {
        "alice": {"id": 1, "role": "user", "hash": generate_password_hash("lab-only-alice-pw", method="scrypt:131072:8:1")},
        "bob": {"id": 2, "role": "user", "hash": generate_password_hash("lab-only-bob-pw", method="scrypt:131072:8:1")},
        "admin": {"id": 3, "role": "admin", "hash": generate_password_hash("lab-only-admin-pw", method="scrypt:131072:8:1")},
    }
    orders = {
        101: {"id": 101, "user_id": 1, "item": "Book"},
        201: {"id": 201, "user_id": 2, "item": "Notebook stand"},
    }

    def current_user():
        user = users.get(session.get("username"))
        return user

    @app.get("/")
    def home():
        return '<h3>lab-only access lab</h3><form method="post" action="/login"><input name="username"><input name="password" type="password"><button>login</button></form>'

    @app.post("/login")
    def login():
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = users.get(username)
        if user is None or not check_password_hash(user["hash"], password):
            return jsonify(error="login failed"), 401
        session.clear()
        session["username"] = username
        session.permanent = True
        return jsonify(username=username)

    @app.post("/logout")
    def logout():
        session.clear()
        return jsonify(message="logged out")

    @app.get("/api/orders/<int:order_id>")
    def detail(order_id):
        user = current_user()
        if user is None:
            return jsonify(error="login required"), 401
        row = orders.get(order_id)
        if row is None:
            return jsonify(error="not found"), 404
        if mode == "fixed" and row["user_id"] != user["id"]:
            app.logger.warning("lab-only-authz-deny user=%s order=%s", user["id"], order_id)
            return jsonify(error="not found"), 404
        return jsonify(row)

    @app.get("/api/admin/summary")
    def summary():
        user = current_user()
        if user is None:
            return jsonify(error="login required"), 401
        if mode == "fixed" and user["role"] != "admin":
            app.logger.warning("lab-only-role-deny user=%s", user["id"])
            return jsonify(error="forbidden"), 403
        return jsonify(order_count=len(orders))

    app.extensions["lab_users"] = users
    return app
