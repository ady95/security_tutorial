# 03-2 Burp Proxy Lab

Run `docker compose up -d`, then open http://127.0.0.1:13000 in Burp's browser.
The deliberately vulnerable Juice Shop target only joins the internal lab network.
The gateway binds the host port to loopback. Do not use the public demo as a target.
Run `docker compose down` before switching to ../web for authorization verification.
No cloud accounts, real credentials or external AI providers are required for search requests.
