"""Run with python -m unittest test_lab.py; no sockets or real systems."""
import unittest
from sqli import create_app as sqli
from xss import create_app as xss
from access import create_app as access

PAYLOAD = "<img src=x onerror=\"document.getElementById('marker').textContent='lab-only-xss'\">"


class LabTests(unittest.TestCase):
    def test_sql_injection_and_normal_inputs(self):
        for mode, expected in (("weak", 200), ("fixed", 401)):
            app = sqli(mode)
            self.addCleanup(app.extensions["lab_db"].close)
            client = app.test_client()
            self.assertEqual(client.post("/login", data={"username": "' OR 1=1 --", "password": "lab-only-wrong"}).status_code, expected)
            self.assertEqual(client.post("/login", data={"username": "alice", "password": "lab-only-alice-pw"}).status_code, 200)
            self.assertEqual(client.post("/login", data={"username": "alice", "password": "lab-only-wrong"}).status_code, 401)
            self.assertEqual(len(client.get("/search", query_string={"q": "Book"}).json["products"]), 2)
            found = client.get("/search", query_string={"q": "' OR 1=1 --"}).json["products"]
            self.assertEqual(len(found), 3 if mode == "weak" else 0)

    def test_reflected_stored_encoding_csp_and_dom_sink(self):
        for mode in ("weak", "fixed"):
            client = xss(mode).test_client()
            reflected = client.get("/reflected", query_string={"q": PAYLOAD})
            client.post("/stored", data={"message": PAYLOAD})
            stored = client.get("/stored")
            for response in (reflected, stored):
                if mode == "weak":
                    self.assertIn(PAYLOAD, response.text)
                else:
                    self.assertNotIn(PAYLOAD, response.text)
                    self.assertIn("&lt;img", response.text)
                    self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
            dom = client.get("/dom", query_string={"q": PAYLOAD})
            self.assertNotIn(PAYLOAD, dom.text)
            script = client.get("/dom.js").text
            self.assertIn("textContent" if mode == "fixed" else "innerHTML", script)
            self.assertIn("hello", client.get("/reflected", query_string={"q": "hello"}).text)

    def test_ownership_roles_authentication_and_logout(self):
        for mode in ("weak", "fixed"):
            app = access(mode)
            client = app.test_client()
            self.assertEqual(client.get("/api/orders/101").status_code, 401)
            self.assertEqual(client.get("/api/admin/summary").status_code, 401)
            self.assertEqual(client.post("/login", data={"username": "alice", "password": "lab-only-wrong"}).status_code, 401)
            self.assertEqual(client.post("/login", data={"username": "alice", "password": "lab-only-alice-pw"}).status_code, 200)
            self.assertEqual(client.get("/api/orders/101").status_code, 200)
            self.assertEqual(client.get("/api/orders/201").status_code, 200 if mode == "weak" else 404)
            self.assertEqual(client.get("/api/orders/999").status_code, 404)
            self.assertEqual(client.get("/api/admin/summary").status_code, 200 if mode == "weak" else 403)
            client.post("/logout")
            self.assertEqual(client.get("/api/orders/101").status_code, 401)
            client.post("/login", data={"username": "bob", "password": "lab-only-bob-pw"})
            self.assertEqual(client.get("/api/orders/201").status_code, 200)
            client.post("/login", data={"username": "admin", "password": "lab-only-admin-pw"})
            self.assertEqual(client.get("/api/admin/summary").status_code, 200)
            self.assertTrue(all(user["hash"].startswith("scrypt:131072:8:1$") for user in app.extensions["lab_users"].values()))


if __name__ == "__main__":
    unittest.main()
