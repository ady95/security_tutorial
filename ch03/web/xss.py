"""03-6: visual marker only; no cookie access or external transmission."""
from flask import Flask, Response, redirect, request
from markupsafe import escape

MARKER = '<p id="marker">lab-only-waiting</p>'
FORM = '<form><input name="q"><button>show</button></form>'


def create_app(mode="fixed"):
    app = Flask(__name__)
    messages = []

    def display(value):
        return str(escape(value)) if mode == "fixed" else value

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        if mode == "fixed":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'"
            )
        return response

    @app.get("/")
    def home():
        return '<h3>lab-only XSS lab</h3><a href="/reflected">reflected</a> <a href="/stored">stored</a> <a href="/dom">dom</a>'

    @app.get("/reflected")
    def reflected():
        value = request.args.get("q", "")
        return MARKER + FORM + "<div>" + display(value) + "</div>"

    @app.route("/stored", methods=["GET", "POST"])
    def stored():
        if request.method == "POST":
            messages.append(request.form.get("message", "")[:1000])
            return redirect("/stored", code=303)
        form = '<form method="post"><input name="message"><button>save</button></form>'
        return MARKER + form + "<ul>" + "".join("<li>" + display(msg) + "</li>" for msg in messages) + "</ul>"

    @app.get("/dom")
    def dom():
        return MARKER + FORM + '<div id="result"></div><script src="/dom.js"></script>'

    @app.get("/dom.js")
    def dom_script():
        sink = "textContent" if mode == "fixed" else "innerHTML"
        script = (
            'const value = new URLSearchParams(location.search).get("q") || "";\n'
            f'document.getElementById("result").{sink} = value;\n'
        )
        return Response(script, mimetype="application/javascript")

    return app
