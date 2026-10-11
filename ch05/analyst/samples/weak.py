def find_product(conn, name):
    return conn.execute(f"SELECT name FROM products WHERE name = '{name}'").fetchall()


def render_message(value):
    return f"<div>{value}</div>"
