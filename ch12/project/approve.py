"""12장 승인 도구 — 사람이 승인 대기 목록을 보고 승인·거부한다 (Agent 가 쓸 수 없는 별도 경로)

    python approve.py                 # 대기 목록 보기 (인자는 한 줄로 줄여 보여 준다)
    python approve.py <요청번호>       # 실행될 인자 전체 보기 — 승인 전에 반드시 확인
    python approve.py <요청번호> yes   # 승인하고 실행
    python approve.py <요청번호> no    # 거부

한 요청은 한 번만 결정된다. 결정을 시작할 때 <요청번호>.decided 파일을 '없을 때만 만들기'로 잡으므로,
같은 요청을 두 번 승인하거나, 거부한 뒤 다시 승인하거나, 두 사람이 동시에 처리해도 실행은 최대 한 번이다.
"""
import json
import os
import re
import sys
from pathlib import Path

from guard import Guard
from tools import FUNCS

HERE = Path(__file__).resolve().parent
AUDIT_DIR = Path(os.environ.get("AUDIT_DIR", HERE))
APPROVALS = AUDIT_DIR / "approvals"


def load(ticket: str) -> tuple[Path, dict]:
    if not re.fullmatch(r"[0-9a-f]{6}", ticket):
        sys.exit(f"요청 번호 형식이 아닙니다: {ticket}")
    path = APPROVALS / f"{ticket}.json"
    if not path.exists():
        sys.exit(f"[{ticket}] 없는 요청입니다")
    return path, json.loads(path.read_text(encoding="utf-8"))


def claim(ticket: str) -> bool:
    """결정 권한을 원자적으로 잡는다. 이미 누가 결정했거나 결정 중이면 False."""
    try:
        fd = os.open(APPROVALS / f"{ticket}.decided", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def main():
    if len(sys.argv) < 2:
        for t in sorted(APPROVALS.glob("*.json")):
            d = json.loads(t.read_text(encoding="utf-8"))
            if d["status"] == "pending":
                brief = json.dumps(d["args"], ensure_ascii=False)
                brief = brief if len(brief) <= 100 else brief[:100] + " …(줄임)"
                print(f"[{d['ticket']}] {d['tool']}({brief})  ← {d['reason']}")
        print("\n승인 전에 python approve.py <요청번호> 로 실행될 인자 전체를 확인하세요.")
        return
    ticket = sys.argv[1]
    path, d = load(ticket)
    if len(sys.argv) < 3:                          # 상세 보기: 실제로 실행될 인자 그대로
        print(f"[{ticket}] 상태 {d['status']} · 이유 {d['reason']}\n도구 {d['tool']}")
        print(json.dumps(d["args"], ensure_ascii=False, indent=2))
        return
    answer = sys.argv[2]
    if answer not in ("yes", "no"):
        sys.exit("yes 또는 no 로 답하세요")
    if d["status"] != "pending" or not claim(ticket):
        sys.exit(f"[{ticket}] 이미 처리된 요청입니다 (상태 {d['status']}). 다시 실행하지 않습니다")
    guard = Guard(HERE, FUNCS, agent="approver", on_behalf_of=os.environ.get("APPROVER", "operator"))
    if answer == "yes":
        d["status"] = "approved"
        try:
            result = FUNCS[d["tool"]](**d["args"])  # 승인된 동작은 사람의 결정으로 한 번만 실행된다
        except Exception as e:
            d["status"], result = "failed", f"오류: {e}"
    else:
        d["status"], result = "rejected", "거부"
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    guard.audit(trace_id=d["trace_id"], tool=d["tool"], decision=d["status"], reason="사람 판단", result=result[:120])
    print(f"[{ticket}] {d['status']}: {result}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
