from html import escape


def find_product(conn, name):
    return conn.execute("SELECT name FROM products WHERE name = ?", (name,)).fetchall()


def render_message(value):
    return "<div>" + escape(value) + "</div>"
