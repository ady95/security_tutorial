"""09-9 분석기 회귀 시험 — 실행 시도와 실행 성공을 구분하는지 확인한다

    python test_map_frameworks.py
"""
import unittest

from map_frameworks import analyze, executed, outcome


def call(result, tool="send_email", to="partner@outside.example"):
    e = {"trace_id": "t1", "step": 1, "tool": tool, "args": {"to": to},
         "tainted": True, "decision": "allow", "reason": "정책 꺼짐"}
    if result is not None:
        e["result"] = result
    return e


class OutcomeTest(unittest.TestCase):
    def test_success(self):
        self.assertEqual(outcome(call("메일 발송(실습용 보관): partner@outside.example / s")), "실행")

    def test_error_is_not_executed(self):
        e = call("오류: 연결 실패")
        self.assertEqual(outcome(e), "실패")
        self.assertFalse(executed(e))

    def test_missing_result_is_unknown(self):
        e = call(None)
        self.assertEqual(outcome(e), "미확인")
        self.assertFalse(executed(e))

    def test_denied_and_pending(self):
        self.assertEqual(outcome(call("거부")), "거부")
        self.assertEqual(outcome(call("승인 대기 4c5ec5")), "승인 대기")

    def test_failed_send_does_not_count_as_sent(self):
        goal = {"trace_id": "t1", "step": 0, "tool": "-", "decision": "goal", "reason": "메일 보내 줘"}
        final = {"trace_id": "t1", "step": 9, "tool": "-", "decision": "final", "reason": "메일을 보냈습니다"}
        _, tagged, extra = analyze([goal, call("오류: 연결 실패"), final])
        self.assertTrue(any(r["id"] == "R6" for r in extra))   # 발송 실패인데 보냈다고 보고


if __name__ == "__main__":
    unittest.main(verbosity=2)
