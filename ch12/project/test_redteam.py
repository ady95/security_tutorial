import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from redteam_lab import MARKER, approved_docs, artifacts, prepare, replay, run_one


class BoundaryTests(unittest.TestCase):
    def run_case(self, case, mode):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, os.environ.copy()):
            root = prepare(Path(folder), case, mode)
            return artifacts(root, case, replay(root, case, mode))

    def test_actual_weak_effects_and_guard_pending(self):
        for case in ("P1", "T1", "C1"):
            with self.subTest(case=case):
                weak = self.run_case(case, "weak")
                safe = self.run_case(case, "guard")
                self.assertTrue(weak["attack_success"])
                self.assertFalse(safe["attack_success"])
                self.assertEqual(safe["pending_count"], 1)
        # Approval prevents outgoing action; it does not remove readable fake secrets.
        self.assertTrue(safe["marker_in_audit"])
        self.assertTrue(safe["marker_in_pending"])

    def test_source_selection_and_normal_operation(self):
        self.assertTrue(self.run_case("P2", "weak")["attack_success"])
        self.assertFalse(self.run_case("P2", "guard")["attack_success"])
        self.assertTrue(self.run_case("N1", "guard")["normal_order_observed"])
        self.assertEqual(len(approved_docs()), 4)

    def test_approved_manifest_rejects_source_drift(self):
        with patch("redteam_lab.hashlib.sha256") as digest:
            digest.return_value.hexdigest.return_value = "changed"
            with self.assertRaises(ValueError):
                approved_docs()
            with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
                result = run_one("P2", "guard", "replay", Path(folder))
                self.assertEqual(result["status"], "error")
                self.assertIsNone(result["attack_success"])


if __name__ == "__main__":
    unittest.main()
