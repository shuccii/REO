"""Regression checks for the v0.3.3 portable instructions (not behavior scores)."""
import os
from pathlib import Path
import unittest

ROOT = Path(os.environ.get('RDO_GUIDANCE_ROOT', Path(__file__).resolve().parents[1]))

class EfficiencyGuidanceTests(unittest.TestCase):
    def text(self, name):
        return (ROOT / name).read_text()

    def test_worker_inline_debugging_bundle(self):
        text = self.text('skills/orchestrate-work/SKILL.md')
        for phrase in ('Worker instructions to copy into each handoff',
                       'one hypothesis', 'one cause-directed repair',
                       'three ineffective repair attempts', 'one diagnostic invocation',
                       'shapes, columns, missing/non-finite counts, values and ranges'):
            with self.subTest(phrase=phrase): self.assertIn(phrase, text)

    def test_independent_batching_preserves_observation_boundary(self):
        text = self.text('skills/orchestrate-work/SKILL.md')
        for phrase in ('Promise.allSettled', 'Inspect every result',
                       'dependent operations, edits, approvals and adaptive follow-ups sequential',
                       'about five decisive output lines'):
            with self.subTest(phrase=phrase): self.assertIn(phrase, text)

    def test_compact_file_handoff_and_per_card_review(self):
        text = self.text('skills/orchestrate-work/references/execution-control.md')
        for phrase in ('risk_class=low', 'risk_class=normal',
                       'at most three', 'separate result', 'each card',
                       'no numerical results', 'at most two artifact files',
                       'three-line summary', 'stage 1 and stage 2 each use one line',
                       'still opens final artifacts'):
            with self.subTest(phrase=phrase): self.assertIn(phrase, text)

    def test_detailed_debugging_matches_single_probe_rule(self):
        text = self.text('skills/root-cause-debugging/SKILL.md')
        self.assertIn('one diagnostic invocation', text)
        self.assertIn('before choosing a repair', text)

if __name__ == '__main__': unittest.main()
