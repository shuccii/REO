import json
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
from review_routing import route_review


class ReviewRoutingTests(unittest.TestCase):
    def test_only_mechanical_uses_direct_route(self):
        r = route_review(task_kind='mechanical')
        self.assertEqual(r['route'], 'single_agent')
        self.assertEqual(r['status'], 'ready_for_direct_checks')
        self.assertEqual(r['reasons'], ['mechanical_only'])
        self.assertFalse(r['review_completed'])

    def test_all_semantic_boundaries_require_independence(self):
        kinds = ['implementation', 'research', 'statistical_design', 'data_leakage',
                 'central_claim', 'external_fact', 'security_sensitive', 'unknown']
        for kind in kinds:
            with self.subTest(kind=kind):
                r = route_review(task_kind=kind, available_reviewers=['worker-2'])
                self.assertEqual(r['route'], 'independent_semantic_review')
                self.assertEqual(r['assigned_reviewers'], ['worker-2'])
                self.assertEqual(r['actual_reviewers'], [])
                self.assertEqual(r['status'], 'ready_for_review')
                self.assertFalse(r['review_completed'])

    def test_quick_never_downgrades_any_gate(self):
        for risk in ['research_conclusion', 'statistical_design', 'data_leakage',
                     'central_claim', 'external_fact', 'security_sensitive',
                     'job_claim', 'implementation_change', 'interpretation']:
            quick = route_review(task_kind='mechanical', risks=[risk], mode='quick')
            standard = route_review(task_kind='mechanical', risks=[risk])
            self.assertEqual(quick['route'], standard['route'])
            self.assertTrue(quick['semantic_review_required'])
            self.assertIn('risk:' + risk, quick['reasons'])

    def test_strict_assurance_overrides_mechanical(self):
        r = route_review(task_kind='mechanical', assurance='research_strict')
        self.assertIn('assurance:research_strict', r['reasons'])
        self.assertTrue(r['manifest_required'])
        self.assertTrue(r['research_contract_required'])

    def test_research_automatically_selects_strict(self):
        for kind in ['research', 'statistical_design', 'data_leakage', 'central_claim']:
            self.assertEqual(route_review(task_kind=kind)['assurance'], 'research_strict')
        self.assertEqual(route_review(task_kind='mechanical', risks=['research_conclusion'])['assurance'], 'research_strict')

    def test_unavailable_and_unknown_are_blocked_not_completed(self):
        for pool, status in [(None, 'unknown'), ([], 'unavailable')]:
            r = route_review(task_kind='implementation', available_reviewers=pool)
            self.assertEqual(r['status'], 'blocked')
            self.assertEqual(r['availability_status'], status)
            self.assertIn('resource_unavailable', r['blocked_reasons'])
            self.assertEqual(r['actual_reviewers'], [])

    def test_explicit_requests_are_preserved_and_must_be_available(self):
        r = route_review(task_kind='implementation', requested_reviewers=['r2', 'r1'],
                         available_reviewers=['r1', 'r2', 'r3'])
        self.assertEqual(r['requested_reviewers'], ['r2', 'r1'])
        self.assertEqual(r['assigned_reviewers'], ['r2', 'r1'])
        self.assertEqual(r['required_reviewer_count'], 2)
        r = route_review(task_kind='implementation', requested_reviewers=['missing'], available_reviewers=['other'])
        self.assertEqual(r['status'], 'blocked')
        self.assertEqual(r['assigned_reviewers'], [])

    def test_explicit_empty_request_does_not_remove_mandatory_reviewer(self):
        r = route_review(task_kind='implementation', requested_reviewers=[], available_reviewers=['r1'])
        self.assertEqual(r['requested_reviewers'], [])
        self.assertEqual(r['required_reviewer_count'], 1)
        self.assertTrue(r['semantic_review_required'])

    def test_requested_reviewer_escalates_mechanical(self):
        r = route_review(task_kind='mechanical', requested_reviewers=['r1'], available_reviewers=['r1'])
        self.assertEqual(r['route'], 'independent_semantic_review')

    def test_budget_boundaries_and_exact_balance(self):
        for remaining, status in [(4, 'insufficient'), (5, 'sufficient'), (6, 'sufficient')]:
            r = route_review(task_kind='implementation', available_reviewers=['r1'],
                             budget={'metric': 'tokens', 'limit': 10, 'used': 10-remaining, 'required': 5})
            self.assertEqual(r['budget_status'], status)
            self.assertEqual(r['status'], 'blocked' if remaining < 5 else 'ready_for_review')
            self.assertTrue(r['semantic_review_required'])
        self.assertEqual(route_review(task_kind='mechanical')['budget_status'], 'not_constrained')

    def test_unobservable_hard_budget_blocks_without_proxy_counts(self):
        for budget in [dict(metric='tokens', limit=10, used=0, required=2, observable=False),
                       dict(metric='llm_calls', limit=10, required=2),
                       dict(metric='tokens', limit=10, used=0)]:
            r = route_review(task_kind='mechanical', budget=budget)
            self.assertEqual(r['budget_status'], 'unobservable')
            self.assertIn('budget_unobservable', r['blocked_reasons'])
        with self.assertRaises(ValueError):
            route_review(budget=dict(metric='turns', limit=10, used=0, required=1))

    def test_multiple_blocks_are_visible_and_deterministic(self):
        args = dict(task_kind='research', risks=['data_leakage', 'central_claim', 'data_leakage'],
                    available_reviewers=[], budget=dict(metric='llm_calls', limit=1, used=1, required=1))
        r = route_review(**args)
        self.assertEqual(r, route_review(**args))
        self.assertEqual(r['blocked_reasons'], ['budget_exceeded', 'resource_unavailable'])
        self.assertEqual(r['reasons'].count('risk:data_leakage'), 1)

    def test_retry_guidance_is_bounded(self):
        r = route_review(task_kind='research', budget={'retry_limit': 1})
        self.assertEqual(r['retry_limit'], 1)
        self.assertIn('unchanged blocked', r['retry_guidance'])
        self.assertEqual(route_review()['retry_limit'], 2)

    def test_invalid_inputs_fail_closed(self):
        for args in [dict(task_kind='simple'), dict(risks=['low']), dict(mode='cheap'),
                     dict(assurance='relaxed'), dict(risks='data_leakage'),
                     dict(available_reviewers=['']), dict(requested_reviewers=['r1', 'r1']),
                     dict(budget={'metric':'tokens','limit':True}),
                     dict(budget={'metric':'tokens','limit':float('nan')}),
                     dict(budget={'retry_limit':-1}), dict(budget={'unknown':1})]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                route_review(**args)

    def test_cli_emits_json_and_nonzero_for_blocked(self):
        result = subprocess.run([sys.executable, str(TOOLS / 'review_routing.py'),
                                 '--task-kind', 'research', '--mode', 'quick',
                                 '--risks', 'central_claim', '--available-reviewers', 'r1'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['actual_reviewers'], [])
        result = subprocess.run([sys.executable, str(TOOLS / 'review_routing.py'),
                                 '--task-kind', 'implementation'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'blocked')

    def test_large_integer_budget_is_handled_without_float_overflow(self):
        r=route_review(task_kind='mechanical',budget={'metric':'tokens','limit':10**1000,'used':0,'required':1,'observable':True})
        self.assertEqual(r['budget_status'],'sufficient')


if __name__ == '__main__':
    unittest.main()
