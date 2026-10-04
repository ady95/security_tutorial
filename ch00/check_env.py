"""00-4. 실습 환경 점검 스크립트 (표준 라이브러리만 사용)

책의 실습에 필요한 도구가 준비되었는지 한 번에 확인합니다.
    python ch00/check_env.py
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path):
    """간단한 .env 파서 — python-dotenv 설치 전에도 동작하도록 직접 읽는다."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def run(cmd):
    """명령을 실행해 (성공 여부, 첫 줄 출력)을 돌려준다."""
    if shutil.which(cmd[0]) is None:
        return False, "설치되어 있지 않음"
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return False, "응답 없음 (30초 초과)"
    text = (out.stdout or out.stderr).strip().splitlines()
    return out.returncode == 0, text[0] if text else ""


def check_llm():
    base = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
    key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("OPENAI_MODEL", "")
    if not base or not model:
        return False, ".env 의 OPENAI_BASE_URL / OPENAI_MODEL 이 비어 있음"
    req = urllib.request.Request(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ids = [m["id"] for m in (json.load(resp).get("data") or [])]
    except Exception as e:  # 연결 실패·인증 실패 등
        return False, f"{base} 연결 실패 ({e.__class__.__name__})"
    if model not in ids:
        return False, f"{model} 모델이 없음 (설치된 모델: {', '.join(ids[:5]) or '없음'})"
    return True, f"{base} · {model}"


def main():
    load_env(ROOT / ".env")
    checks = [
        ("Python 3.10 이상", (sys.version_info >= (3, 10), sys.version.split()[0])),
        ("Git", run(["git", "--version"])),
        ("Docker", run(["docker", "--version"])),
        ("Docker 엔진 실행 중", run(["docker", "info", "--format", "{{.ServerVersion}}"])),
        ("Docker Compose", run(["docker", "compose", "version"])),
        ("LLM 연결", check_llm()),
    ]
    failed = 0
    for name, (ok, detail) in checks:
        print(f"[{'OK' if ok else '실패'}] {name} — {detail}")
        failed += not ok
    print()
    print("모든 항목 통과 — 실습을 시작할 수 있습니다." if not failed else f"{failed}개 항목을 확인하세요.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
