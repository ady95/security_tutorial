"""12-6 Sandbox 확인 — Agent 컨테이너 안에서 제한이 실제로 걸렸는지 본다 (표준 라이브러리만 사용)

    docker compose run --rm agent python sandbox_check.py

외부 연결 시험은 문서용 예약 도메인(example.com)에 연결을 시도만 한다. 데이터는 보내지 않는다.
"""
import os
import socket
import sys
import urllib.request
from pathlib import Path


def status_field(name: str) -> str:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith(name + ":"):
            return line.split(":", 1)[1].strip()
    return "?"


def can_write(folder: str) -> str:
    probe = Path(folder) / ".sandbox_probe"
    try:
        probe.write_text("x")
        probe.unlink()
        return "열림"
    except OSError:
        return "막힘"


def can_connect(host: str, port: int) -> str:
    try:
        socket.create_connection((host, port), timeout=5).close()
        return "열림"
    except OSError:
        return "막힘"


def ollama() -> str:
    try:
        with urllib.request.urlopen("http://ollama:11434/api/version", timeout=5) as r:
            return str(r.status)
    except OSError as e:
        return f"실패 ({e.__class__.__name__})"


def main():
    print(f"id {os.getuid()}:{os.getgid()} CapEff {status_field('CapEff')} NoNewPrivs {status_field('NoNewPrivs')}")
    print(f"app 쓰기 {can_write('/app')}")
    print(f"workspace 쓰기 {can_write(os.environ.get('WORKSPACE', '/workspace'))}")
    print(f"output 쓰기 {can_write(os.environ.get('OUTPUT', '/output'))}")
    print(f"인터넷 {can_connect('example.com', 80)}")
    print(f"ollama 연결 {ollama()}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
