import copy
import json
import unittest
from team_lab import HERE, check_model, detect, evaluate


class TeamTests(unittest.TestCase):
    def test_model_links_and_missing_owner(self):
        model = json.loads((HERE / "threat-model.json").read_text(encoding="utf-8"))
        self.assertEqual(check_model(model)["threats"], 5)
        broken = copy.deepcopy(model)
        broken["threats"][0]["owner"] = ""
        with self.assertRaises(AssertionError):
            check_model(broken)

    def test_interleaved_traces_and_identity_do_not_join(self):
        read = {"agent": "a", "on_behalf_of": "alice", "trace_id": "same", "tool": "read_file", "decision": "allow", "result": "note"}
        send = {"agent": "a", "on_behalf_of": "bob", "trace_id": "same", "tool": "send_email", "args": {"to": "partner@outside.example"}, "decision": "allow"}
        self.assertEqual(detect([read, send]), [])
        send["on_behalf_of"] = "alice"
        send["decision"] = "approve"
        send["result"] = "승인 대기"
        self.assertEqual(detect([read, send])[0]["outcome"], "pending")
        send["result"] = "메일 발송(실습용 보관)"
        self.assertEqual(detect([read, send])[0]["outcome"], "attempt-observed")
        with self.assertRaises(ValueError):
            detect([{"tool": "send_email"}])

    def test_labelled_normal_cases_and_rule_improvement(self):
        events = [json.loads(line) for line in (HERE / "sample_audit.jsonl").read_text(encoding="utf-8").splitlines()]
        labels = json.loads((HERE / "trace-labels.json").read_text(encoding="utf-8"))
        first, second = evaluate(events, labels, 1), evaluate(events, labels, 2)
        self.assertEqual((first["TP"], first["FP"], first["FN"]), (2, 1, 2))
        self.assertEqual((second["TP"], second["FP"], second["FN"]), (4, 0, 0))


if __name__ == "__main__":
    unittest.main()
