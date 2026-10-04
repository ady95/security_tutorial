"""3장 실습용 쇼핑몰 앱 (secbook-shop) — 기준(안전한) 버전

이후 실습에서는 이 앱을 바탕으로 일부러 취약하게 만든 버전과 고친 버전을 비교한다.
모든 계정·비밀번호는 실습용 가짜 값이다.
"""
import os
import sqlite3

from flask import Flask, abort, g, jsonify, redirect, request, session

app = Flask(__name__)
app.secret_key = os.environ["SHOP_SECRET_KEY"]
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
app.json.ensure_ascii = False  # JSON 응답의 한글을 \uXXXX 대신 그대로 보여 준다
DB_PATH = os.environ.get("SHOP_DB", "shop.db")

USERS = [
    (1, "alice", "lab-only-alice-pw", "user"),
    (2, "bob", "lab-only-bob-pw", "user"),
    (3, "admin", "lab-only-admin-pw", "admin"),
]
ORDERS = [
    (101, 1, "보안 입문서", 1, 18000),
    (102, 1, "USB 보안키", 2, 52000),
    (201, 2, "노트북 거치대", 1, 34000),
]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS orders;
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, item TEXT, qty INTEGER, price INTEGER);
    """)
    # 실습을 단순하게 하려고 비밀번호를 평문으로 저장한다. 03-7에서 해시 저장으로 바꾼다
    conn.executemany("INSERT INTO users VALUES (?, ?, ?, ?)", USERS)
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", ORDERS)
    conn.commit()
    conn.close()


@app.get("/")
def home():
    user = session.get("username")
    if user:
        return f'<p>{user} 님, 환영합니다.</p><p><a href="/me">내 정보</a> · <a href="/logout">로그아웃</a></p>'
    return (
        '<h3>secbook-shop</h3>'
        '<form method="post" action="/login">'
        '<input name="username" placeholder="아이디"> '
        '<input name="password" type="password" placeholder="비밀번호"> '
        '<button>로그인</button></form>'
    )


@app.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    # 입력값을 SQL 문에 직접 붙이지 않고 자리표시자(?)로 전달한다 (03-3, 03-4에서 비교)
    row = db().execute(
        "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
        (username, password),
    ).fetchone()
    if row is None:
        return "아이디 또는 비밀번호가 올바르지 않습니다.", 401
    session.clear()
    session["user_id"] = row["id"]
    session["username"] = row["username"]
    return redirect("/me")


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/me")
def me():
    if "user_id" not in session:
        return redirect("/")
    return f'<p>로그인한 사용자: {session["username"]}</p><p><a href="/api/orders">내 주문 (JSON)</a></p>'


@app.get("/api/orders")
def my_orders():
    if "user_id" not in session:
        return jsonify(error="login required"), 401
    rows = db().execute(
        "SELECT id, item, qty, price FROM orders WHERE user_id = ?", (session["user_id"],)
    ).fetchall()
    return jsonify(orders=[dict(r) for r in rows])


@app.get("/api/orders/<int:order_id>")
def order_detail(order_id):
    if "user_id" not in session:
        return jsonify(error="login required"), 401
    row = db().execute(
        "SELECT id, user_id, item, qty, price FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    # 다른 사람의 주문은 없는 것처럼 응답한다 (03-8 접근 제어에서 비교)
    if row is None or row["user_id"] != session["user_id"]:
        abort(404)
    return jsonify(dict(row))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
