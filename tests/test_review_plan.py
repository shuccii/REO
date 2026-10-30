import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from review_plan import plan

class ReviewPlanTests(unittest.TestCase):
    def test_quick_loads_only_core_and_preserves_scope(self):
        r = plan(mode='quick', task='peer_review')
        self.assertEqual(r['mode'], 'quick')
        self.assertNotIn('references/output-template.md', r['references'])
        self.assertIn('coverage', r['required_output'])
        self.assertIn('compute_before_numeric_claim', r['invariants'])

    def test_standard_and_deep_keep_integrity(self):
        for mode in ('standard', 'deep'):
            r = plan(mode=mode, task='audit', field='材料', long=True, previous=True)
            self.assertIn('references/long-manuscripts.md',r['references'])
            self.assertIn('references/local-context-and-continuity.md',r['references'])
            self.assertIn('references/probes/materials-ml.md',r['references'])
            self.assertTrue(r['cross_claim_check'])

    def test_defense_does_not_force_full_report(self):
        r=plan(task='defense')
        self.assertIn('references/defense-and-feedback.md',r['references'])
        self.assertNotIn('references/output-template.md',r['references'])
        self.assertIn('wait_for_answer',r['invariants'])

    def test_invalid_options_rejected(self):
        with self.assertRaises(ValueError):plan(mode='cheap')
