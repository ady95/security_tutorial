# 04-3 Container Boundary Lab

Only weak (root with a writable dedicated lab-share) and fixed containers run.
No privileged container, actual Docker socket or host-root mount is launched.
The risky inspect fixture is synthetic input for policy review; it is not a Compose file.
The policy flags a deliberately strict subset of configuration risks, not all vulnerabilities.

```bash
python prepare.py
python audit.py risky-inspect.fixture.json
python audit.py fixed-inspect.fixture.json
docker compose up -d
docker compose exec weak sh -c 'printf "lab-only-created\n" > /shared/lab-only-output.txt'
docker compose exec fixed cat /shared/lab-only-note.txt
docker compose exec fixed sh -c 'printf "lab-only-created\n" > /shared/lab-only-fixed.txt'
docker compose down
```

The last write should fail. Existing lab-share files are kept; only lab-only files are created.
Do not substitute a real project directory for the dedicated mount.
Generated inspect JSON can contain host paths and is excluded from Git.
