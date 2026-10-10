"""12장 정책 테스트 — "이 도구 호출은 이렇게 판단되어야 한다"는 기대값을 LLM 없이 직접 확인한다

    python test_guard.py

정책(policy.json)을 고칠 때마다 실행해, 막혀야 할 호출이 여전히 막히는지 확인한다. 하나라도 어긋나면 종료 코드 1.
"""
import sys
from pathlib import Path

from guard import Guard

HERE = Path(__file__).resolve().parent

# (설명, 도구, 인자, 신뢰할 수 없는 내용을 읽은 뒤인가, 기대 판단)
CASES = [
    ("작업 폴더 메모 읽기",            "read_file",   {"path": "workspace/notes.txt"}, False, "allow"),
    ("작업 폴더 밖으로 빠져나가 읽기",  "read_file",   {"path": "workspace/../.env"},   False, "deny"),
    ("결과 폴더에 보고서 쓰기",        "write_file",  {"path": "output/report.md", "content": "x"}, False, "allow"),
    ("결과 폴더 밖에 쓰기",            "write_file",  {"path": "/etc/cron.d/x", "content": "x"},    False, "deny"),
    ("사내 주소 메일 (읽기 전)",       "send_email",  {"to": "team@lab.example", "subject": "s", "body": "b"}, False, "allow"),
    ("사내 주소 메일 (문서 읽은 뒤)",   "send_email",  {"to": "team@lab.example", "subject": "s", "body": "b"}, True,  "approve"),
    ("외부 주소 메일",                 "send_email",  {"to": "someone@outside.example", "subject": "s", "body": "b"}, False, "approve"),
    ("결과 폴더 파일 삭제",            "delete_file", {"path": "output/old.md"},       False, "approve"),
    ("작업 폴더 파일 삭제",            "delete_file", {"path": "workspace/notes.txt"}, False, "deny"),
    ("정책에 없는 명령 실행 도구",      "run_shell",   {"cmd": "ls"},                   False, "deny"),
    ("정책에 없는 토큰 발급 도구",      "create_token", {"scope": "admin"},             False, "deny"),
]


def main():
    guard = Guard(HERE, funcs={}, agent="test", on_behalf_of="test")
    failed = 0
    for desc, tool, args, tainted, expected in CASES:
        guard.tainted = tainted
        decision, reason = guard.decide(tool, args)
        ok = decision == expected
        failed += not ok
        print(f"{'통과' if ok else '실패'}  {desc:<22} 기대 {expected:<8} 결과 {decision:<8} ({reason})")
    print(f"\n{len(CASES) - failed}/{len(CASES)} 통과")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
