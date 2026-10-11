import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import analysis_lab as lab
from samples import weak, fixed

class AnalysisTests(unittest.TestCase):
    def test_streaming_summary_and_unknown_log_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'access.jsonl'
            lab.generate(path)
            prepared = lab.prepare(path)
        self.assertEqual(prepared['total_records'], 10000)
        self.assertNotIn('cookie', json.dumps(prepared))
        self.assertLess(len(json.dumps(prepared)), 16000)
        self.assertTrue(any(g['candidate'] and g['count'] == 4 for g in prepared['summary']))
        proposal = lab.load(lab.HERE / 'logs-proposal.fixture.json')
        lab.check_logs(proposal, prepared)
        malformed = copy.deepcopy(proposal)
        malformed['findings'].append('not a finding object')
        with self.assertRaises(ValueError):
            lab.check_logs(malformed, prepared)
        proposal['findings'][0]['evidence_ids'] = ['L99999']
        with self.assertRaises(ValueError):
            lab.check_logs(proposal, prepared)

    def test_review_references_and_actual_code_behavior(self):
        proposal = lab.load(lab.HERE / 'review-proposal.fixture.json')
        source = lab.HERE / 'samples/weak.py'
        lab.check_review(proposal, source)
        bad = copy.deepcopy(proposal)
        bad['findings'][0]['line'] = 999
        with self.assertRaises(ValueError):
            lab.check_review(bad, source)
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.execute('CREATE TABLE products (name TEXT)')
        conn.executemany('INSERT INTO products VALUES (?)', [('Book',), ('USB key',)])
        self.assertEqual(weak.find_product(conn, 'Book'), fixed.find_product(conn, 'Book'))
        self.assertEqual(len(weak.find_product(conn, "' OR 1=1 --")), 2)
        self.assertEqual(fixed.find_product(conn, "' OR 1=1 --"), [])
        self.assertIn('<b>', weak.render_message('<b>lab-only</b>'))
        self.assertIn('&lt;b&gt;', fixed.render_message('<b>lab-only</b>'))
        with self.assertRaises(ValueError):
            lab.compare(proposal, {'results': [], 'errors': [{'message': 'scan failed'}]})

    def test_case_evidence_and_priority_floor(self):
        cases = lab.load(lab.HERE / 'cases.fixture.json')
        proposal = lab.load(lab.HERE / 'hunt-proposal.fixture.json')
        result = lab.check_hunt(proposal, cases)
        self.assertEqual([c['effective_priority'] for c in result['cases']], ['high', 'medium', 'low'])
        self.assertFalse(result['response_executed'])
        bad = copy.deepcopy(proposal)
        bad['cases'][0]['event_ids'] = ['E007']
        with self.assertRaises(ValueError):
            lab.check_hunt(bad, cases)
        with self.assertRaises(ValueError):
            lab.check_hunt({'cases': []}, cases)

if __name__ == '__main__':
    unittest.main()
