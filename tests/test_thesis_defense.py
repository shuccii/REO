"""Guards for the thesis-defense workflow (wording checks, not behavior scores)."""
import os
from pathlib import Path
import re
import unittest

ROOT = Path(os.environ.get('RDO_GUIDANCE_ROOT', Path(__file__).resolve().parents[1]))
SKILL = ROOT / 'skills/thesis-defense-workflow'


class ThesisDefenseTests(unittest.TestCase):
    def test_skill_frontmatter_and_links(self):
        text = (SKILL / 'SKILL.md').read_text()
        self.assertTrue(text.startswith('---\nname: thesis-defense-workflow\n'))
        for target in re.findall(r'\]\(([^)#]+\.md)\)', text):
            with self.subTest(link=target):
                self.assertTrue((SKILL / target).resolve().exists())

    def test_core_phases_and_boundaries(self):
        text = (SKILL / 'SKILL.md').read_text()
        for phrase in ('Fix the facts first', 'Backward schedule', 'Issue log',
                       'objective → result → conclusion', 'Track W', 'Track S', 'Track Q', 'Track R',
                       'Rehearsal', 'Day-of', 'never predicts a pass',
                       'never submits, uploads', 'never writes the thesis in place of the student unless AI drafting mode', 'unconfirmed'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_naist_reference_keeps_current_and_historical_apart(self):
        text = (SKILL / 'references/naist.md').read_text()
        for item in ('N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'no points or numeric thresholds',
                     'do not treat as current', 'https://www.naist.jp/campuslife/degree/criteria.html',
                     'November of year 2', 'education-record system', 'Not confirmed from official sources'):
            with self.subTest(item=item):
                self.assertIn(item, text)

    def test_track_references(self):
        checks = {
            'references/writing.md': ('Question ↔ answer', 'Outline first', 'One sentence, one idea', 'does not produce text'),
            'references/slides.md': ('Design backward', 'Slide numbers', 'Backup slides', 'outlook'),
            'references/questions.md': ('Method principles', 'Answer patterns', 'Yes/no question', 'You do not know', 'public information',
                                        'Where questions concentrate', 'follow-up chain'),
            'references/ai-drafting.md': ('opt-in', 'P1', 'A user\'s request alone does not satisfy P1', 'May not',
                                          'Add results, numbers, data, references', '[student-checked]',
                                          'The agent never changes the marker itself', 'Explain test', 'AI-use log'),
            'references/review-checks.md': ('Tier 0', 'Tier 1', 'Tier 2', 'thesis_skeleton.py', 'T1', 'F3', 'M6', 'D2', 'E3',
                                            'never the saving', 'Do not report a pass for an item that was not looked at'),
        }
        for name, phrases in checks.items():
            text = (SKILL / name).read_text()
            for phrase in phrases:
                with self.subTest(file=name, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_routed_from_entrypoints(self):
        for name in ('skills/orchestrate-work/SKILL.md', 'skills/research-review-workflow/SKILL.md'):
            with self.subTest(file=name):
                self.assertIn('thesis-defense-workflow', (ROOT / name).read_text())

    def test_no_private_markers(self):
        pattern = re.compile(r'/Users/|OneDrive|slack\.com|@gmail|@icloud')
        for path in SKILL.rglob('*.md'):
            with self.subTest(file=str(path)):
                self.assertIsNone(pattern.search(path.read_text()))


if __name__ == '__main__':
    unittest.main()
