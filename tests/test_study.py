"""Offline mechanism comparisons, including failed and unobserved attempts."""
import copy
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('study', Path(__file__).resolve().parents[1] / 'evals/bench/study.py')
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class StudyTests(unittest.TestCase):
    def spec(self):
        return {'model': 'fixed-version', 'settings_hash': 'settings', 'grader_hash': 'grader',
                'tasks': [{'id': 'paper', 'input_hash': 'input'}], 'repetitions': 3,
                'max_runs': 6, 'arms': {'full': {'reading': 'full', 'mode': 'standard'},
                                      'delta': {'reading': 'delta', 'mode': 'standard'}}}

    def rows(self):
        return [dict(job, attempt=1, completed=True, success=True, false_completion=False,
                     seconds=2 if job['arm'] == 'full' else 1, cost_usd=.1,
                     llm_calls=None, tokens=10) for job in study.matrix(self.spec())]

    def test_matrix_is_serial_dry_run_with_fixed_conditions(self):
        jobs = study.matrix(self.spec())
        self.assertEqual(len(jobs), 6)
        self.assertTrue(all(j['conditions']['model'] == 'fixed-version' for j in jobs))
        self.assertEqual(jobs[0]['rep'], 1)
        self.assertNotIn('command', jobs[0])

    def test_matrix_refuses_excess_runs_and_missing_fixed_model(self):
        for change in ({'max_runs': 5}, {'model': ''}, {'repetitions': True}, {'repetitions': 0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                study.matrix(dict(self.spec(), **change))

    def test_pairs_isolate_one_factor_and_keep_unknown_metrics_null(self):
        result = study.compare(self.rows(), 'reading')
        contrast = result['contrasts']['full_vs_delta']
        self.assertEqual(contrast['paired_runs'], 3)
        self.assertEqual(contrast['delta_mean']['seconds'], 1)
        self.assertIsNone(contrast['delta_mean']['llm_calls'])
        self.assertIsNone(result['arms']['full']['llm_calls']['total'])

    def test_failures_and_retries_count_towards_spend(self):
        rows = self.rows()
        failed = dict(rows[0], completed=False, success=False, seconds=5, attempt=1)
        rows[0]['attempt'] = 2
        result = study.compare([failed] + rows, 'reading')
        arm = rows[0]['arm']
        self.assertEqual(result['arms'][arm]['attempts'], 4)
        self.assertEqual(result['arms'][arm]['seconds']['total'], 5 + sum(r['seconds'] for r in rows if r['arm'] == arm))

    def test_model_input_grader_and_non_target_factor_must_match(self):
        for key in ('model', 'input_hash', 'settings_hash', 'grader_hash'):
            rows = self.rows()
            rows[0]['conditions'][key] = 'other'
            result = study.compare(rows, 'reading')['contrasts']['full_vs_delta']
            self.assertEqual(result['paired_runs'], 2)
        rows = self.rows()
        rows[0]['factors']['mode'] = 'deep'
        self.assertEqual(study.compare(rows, 'reading')['contrasts']['full_vs_delta']['paired_runs'], 2)

    def test_duplicate_nonfinite_negative_and_boolean_usage_rejected(self):
        rows = self.rows()
        with self.assertRaises(ValueError): study.compare(rows + [rows[0]], 'reading')
        for invalid in (float('nan'), float('inf'), -1, True):
            rows = self.rows()
            rows[0]['cost_usd'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError): study.compare(rows, 'reading')

    def test_missing_measurements_are_not_zero_in_totals(self):
        rows = self.rows()
        rows[0]['seconds'] = None
        result = study.compare(rows, 'reading')
        self.assertIsNone(result['arms'][rows[0]['arm']]['seconds']['total'])
        self.assertEqual(result['arms'][rows[0]['arm']]['seconds']['observed'], 2)

    def test_missing_quality_cannot_be_claimed_success_or_no_false_completion(self):
        rows = self.rows()
        rows[0]['success'] = None
        rows[0]['false_completion'] = None
        result = study.compare(rows, 'reading')
        self.assertEqual(result['arms'][rows[0]['arm']]['success']['observed'], 2)


if __name__ == '__main__': unittest.main()
