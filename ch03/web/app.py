"""Local container lab only; no production deployment."""
import os
from sqli import create_app as create_sqli
from xss import create_app as create_xss
from access import create_app as create_access

factories = {"sqli": create_sqli, "xss": create_xss, "access": create_access}

if __name__ == "__main__":
    kind = os.environ.get("LAB_APP", "sqli")
    mode = os.environ.get("LAB_MODE", "fixed")
    if kind not in factories or mode not in {"weak", "fixed"}:
        raise SystemExit("LAB_APP / LAB_MODE invalid")
    app = factories[kind](mode)
    app.run(host="0.0.0.0", port=5000, debug=False)
