"""12장 승인 도구 시험 — 한 요청은 최대 한 번만 실행되고, 상세 보기는 인자를 자르지 않는다

    python test_approve.py

실제 도구 대신 호출 횟수만 세는 가짜 도구와 임시 폴더를 쓴다. 메일·파일은 만들지 않는다.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

TMP = tempfile.mkdtemp()
os.environ["AUDIT_DIR"] = TMP
import approve  # noqa: E402  (AUDIT_DIR 을 정한 뒤 불러온다)

CALLS = []
approve.FUNCS = {"send_email": lambda **kw: CALLS.append(kw) or "메일 발송(실습용 보관)"}


def ticket(tid: str, body: str = "lab-only-body") -> None:
    (Path(TMP) / "approvals").mkdir(exist_ok=True)
    (Path(TMP) / "approvals" / f"{tid}.json").write_text(json.dumps(
        {"ticket": tid, "trace_id": "t1", "tool": "send_email", "reason": "외부 주소",
         "args": {"to": "partner@outside.example", "subject": "s", "body": body},
         "status": "pending"}, ensure_ascii=False), encoding="utf-8")


def run(*argv) -> str:
    sys.argv = ["approve.py", *argv]
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            approve.main()
    except SystemExit as e:
        return out.getvalue() + str(e.code)
    return out.getvalue()


class ApproveTest(unittest.TestCase):
    def setUp(self):
        CALLS.clear()

    def test_detail_shows_full_args(self):
        ticket("aaaaa1", "x" * 200 + "lab-only-tail")
        self.assertNotIn("lab-only-tail", run())             # 목록은 줄여 보여 준다
        self.assertIn("lab-only-tail", run("aaaaa1"))        # 상세 보기는 끝까지

    def test_double_approve_runs_once(self):
        ticket("aaaaa2")
        run("aaaaa2", "yes")
        self.assertIn("이미 처리된", run("aaaaa2", "yes"))
        self.assertEqual(len(CALLS), 1)

    def test_reject_then_approve_never_runs(self):
        ticket("aaaaa3")
        run("aaaaa3", "no")
        self.assertIn("이미 처리된", run("aaaaa3", "yes"))
        self.assertEqual(len(CALLS), 0)

    def test_claim_blocks_concurrent_decision(self):
        ticket("aaaaa4")
        self.assertTrue(approve.claim("aaaaa4"))             # 다른 사람이 먼저 결정을 시작함
        self.assertIn("이미 처리된", run("aaaaa4", "yes"))
        self.assertEqual(len(CALLS), 0)

    def test_bad_ticket_id(self):
        self.assertIn("형식이 아닙니다", run("../x", "yes"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    unittest.main(verbosity=2)
