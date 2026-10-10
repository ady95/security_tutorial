"""12장 승인 도구 — 사람이 승인 대기 목록을 보고 승인·거부한다 (Agent 가 쓸 수 없는 별도 경로)

    python approve.py                 # 대기 목록 보기
    python approve.py <요청번호> yes   # 승인하고 실행
    python approve.py <요청번호> no    # 거부
"""
import json
import os
import sys
from pathlib import Path

from guard import Guard
from tools import FUNCS

HERE = Path(__file__).resolve().parent
AUDIT_DIR = Path(os.environ.get("AUDIT_DIR", HERE))


def main():
    tickets = sorted((AUDIT_DIR / "approvals").glob("*.json"))
    if len(sys.argv) < 3:
        for t in tickets:
            d = json.loads(t.read_text(encoding="utf-8"))
            if d["status"] == "pending":
                print(f"[{d['ticket']}] {d['tool']}({json.dumps(d['args'], ensure_ascii=False)[:100]})  ← {d['reason']}")
        return
    ticket, answer = sys.argv[1], sys.argv[2]
    path = AUDIT_DIR / "approvals" / f"{ticket}.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    guard = Guard(HERE, FUNCS, agent="approver", on_behalf_of=os.environ.get("APPROVER", "operator"))
    if answer == "yes":
        result = FUNCS[d["tool"]](**d["args"])     # 승인된 동작은 사람의 결정으로 실행된다
        d["status"] = "approved"
    else:
        result = "거부"
        d["status"] = "rejected"
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    guard.audit(trace_id=d["trace_id"], tool=d["tool"], decision=d["status"], reason="사람 판단", result=result[:120])
    print(f"[{ticket}] {d['status']}: {result}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
