"""Tests for scripts/thesis_skeleton.py (standard library only)."""
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/thesis_skeleton.py'

MD = """# Introduction

Machine learning can predict material properties. However, few data exist for irradiated alloys.

This study asks whether simulation data improve predictions.

## Results

Figure 1 parity plot of predicted and measured values.

We established a new framework that proved superior accuracy.

# Conclusion

Simulation data improved predictions within the tested composition range.
"""

DOCX_BODY = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
             '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>序論</w:t></w:r></w:p>'
             '<w:p><w:r><w:t>本研究は外挿予測を扱う。手法を開発した。</w:t></w:r></w:p>'
             '<w:p><w:r><w:t>図1 予測値と実測値。</w:t></w:r></w:p>'
             '</w:body></w:document>')


def run(path, *extra):
    p = subprocess.run([sys.executable, '-B', str(SCRIPT), str(path), '--json', *extra],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


class ThesisSkeletonTests(unittest.TestCase):
    def test_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 't.md'; f.write_text(MD, encoding='utf-8')
            code, out = run(f)
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual([o['heading'] for o in data['outline']], ['Introduction', 'Results', 'Conclusion'])
            self.assertEqual(data['topic_sentences'][0]['text'], 'Machine learning can predict material properties.')
            self.assertEqual(len(data['captions']), 1)
            self.assertTrue(any('established' in c['text'] for c in data['claims'] + data['topic_sentences']))

    def test_docx(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 't.docx'
            with zipfile.ZipFile(f, 'w') as z:
                z.writestr('word/document.xml', DOCX_BODY)
            code, out = run(f)
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data['outline'][0]['heading'], '序論')
            self.assertEqual(data['captions'][0]['text'], '図1 予測値と実測値。')
            self.assertTrue(any('開発' in c['text'] for c in data['claims']))
            self.assertEqual(data['topic_sentences'][0]['flags'], [])

    def test_missing_file(self):
        code, _ = run(Path('/nonexistent/thesis.md'))
        self.assertEqual(code, 2)


if __name__ == '__main__':
    unittest.main()
