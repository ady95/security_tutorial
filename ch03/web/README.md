# 03-4 / 03-6 / 03-8 Local Web Lab

Only fake data in an internal Docker network. The gateway publishes to loopback only.
Run one chapter lab at a time because the subnet is shared.

```bash
LAB_APP=sqli docker compose up -d --build
docker compose exec client curl -sG --data-urlencode "q=Book" http://weak:5000/search
docker compose down
LAB_APP=xss docker compose up -d --build
docker compose down
LAB_APP=access docker compose up -d --build
```

Browser URLs: http://127.0.0.1:18081 (weak), http://127.0.0.1:18082 (fixed).
Modes: sqli, xss, access. LAB_MODE selects intentionally vulnerable or fixed code.
Each process restarts its fake database/messages. This is a teaching lab, not a deployable service.
SQL trace logs contain fake lab-only credentials and must not be copied into real applications.
Access-mode passwords are stored as scrypt hashes; its Flask cookie does not implement server-side revocation.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest test_lab.py
```

Tests exercise Flask request handling, SQL/data separation, authorization and HTML encoding.
They do not verify browser script execution or Docker networking.
