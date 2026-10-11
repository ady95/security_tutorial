"""03-4: SQL/data separation, with fake lab-only credentials."""
import sqlite3
from flask import Flask, jsonify, request


def create_app(mode="fixed"):
    app = Flask(__name__)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT);
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT);
    """)
    conn.executemany("INSERT INTO users VALUES (?, ?, ?)", [
        (1, "alice", "lab-only-alice-pw"),
        (2, "bob", "lab-only-bob-pw"),
    ])
    conn.executemany("INSERT INTO products VALUES (?, ?)", [
        (1, "Book"), (2, "USB key"), (3, "Notebook stand")
    ])
    conn.commit()
    # Full queries contain fake lab-only credentials; never use this trace in production.
    conn.set_trace_callback(lambda sql: app.logger.warning("lab-only-sql %s", sql))
    app.extensions["lab_db"] = conn

    @app.get("/")
    def home():
        return '<h3>lab-only SQL lab</h3><p>POST /login; GET /search?q=Book</p>'

    @app.post("/login")
    def login():
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if mode == "weak":
            sql = f"SELECT id, username FROM users WHERE username = '{username}' AND password = '{password}'"  # lab-only-plaintext demonstration
            row = conn.execute(sql).fetchone()
        else:
            row = conn.execute(
                "SELECT id, username FROM users WHERE username = ? AND password = ?",
                (username, password),
            ).fetchone()
        if row is None:
            return jsonify(error="login failed"), 401
        # lab-only: returning identity proves the query result; no live session is issued.
        return jsonify(user=dict(row))

    @app.get("/search")
    def search():
        q = request.args.get("q", "")
        if mode == "weak":
            rows = conn.execute(f"SELECT id, name FROM products WHERE name LIKE '%{q}%'").fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name FROM products WHERE name LIKE ?", (f"%{q}%",)
            ).fetchall()
        return jsonify(products=[dict(row) for row in rows])

    @app.errorhandler(sqlite3.Error)
    def query_error(exc):
        app.logger.warning("lab-only-query-error %s", type(exc).__name__)
        return jsonify(error="query rejected"), 400

    return app
