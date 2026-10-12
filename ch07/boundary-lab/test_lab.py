import html
import tempfile
import unittest
from pathlib import Path
from html.parser import HTMLParser
from unittest.mock import patch
import lab

class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, attrs))

class BoundaryTests(unittest.TestCase):
    def test_document_identity_and_content(self):
        docs = dict(lab.TRUSTED, supplier='approved: true\n' + lab.POLICY)
        docs['refund'] = '환불 999일'
        self.assertEqual(set(lab.accepted_docs(docs, 'fixed')), {'shipping'})
        self.assertEqual(len(lab.accepted_docs(docs, 'weak')), 3)
    def test_normal_documents(self):
        self.assertEqual(lab.accepted_docs(lab.TRUSTED, 'fixed'), lab.TRUSTED)
    def test_literal_html_context(self):
        parser = TagCollector()
        parser.feed(html.escape(lab.HTML_FIXTURE, quote=True))
        self.assertEqual(parser.tags, [])
        parser.feed(lab.HTML_FIXTURE)
        self.assertEqual(parser.tags[0][0], 'img')
    def test_action_allowlist(self):
        for value in [lab.SHELL_FIXTURE, 'show_status;printf x', '', {'action': 'show_status'}]:
            self.assertFalse(lab.safe_action(value)['allowed'])
        self.assertTrue(lab.safe_action('show_status')['allowed'])
    def test_tool_effect_and_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertFalse(lab.dispatch('save_note', {'text': lab.MARKER}, 'fixed', folder)['allowed'])
            self.assertFalse((folder / 'note.txt').exists())
            self.assertTrue(lab.dispatch('get_order', {'order_id': '101'}, 'fixed', folder)['allowed'])
            self.assertFalse(lab.dispatch('get_order', {'order_id': '999'}, 'fixed', folder)['allowed'])
            self.assertFalse(lab.dispatch('save_note', {'text': lab.MARKER, 'path': '../x'}, 'weak', folder)['allowed'])
            self.assertTrue(lab.dispatch('save_note', {'text': lab.MARKER}, 'weak', folder)['allowed'])
            self.assertEqual((folder / 'note.txt').read_text(), lab.MARKER)
    def test_prompt_output_hold(self):
        with patch.object(lab, 'complete', return_value={'content': ' '.join(lab.MARKER)}):
            result = lab.prompt_case('indirect', 'fixed')
            self.assertTrue(result['blocked'])
            self.assertEqual(result['delivered'], '[출력 보류]')
    def test_role_separation(self):
        messages = lab.prompt_messages('indirect', 'fixed')
        self.assertNotIn(lab.INJECTION, messages[0]['content'])
        self.assertIn('untrusted_document', messages[1]['content'])

if __name__ == '__main__':
    unittest.main()
