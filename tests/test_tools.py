"""Checks for the optional discipline tools. Each group is skipped when its dependency is missing."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


def has(module):
    return importlib.util.find_spec(module) is not None


def run(main, argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(argv)
    return code, json.loads(buffer.getvalue())


class SafeExpressionTests(unittest.TestCase):
    def test_rejects_code_and_undeclared_names(self):
        from _safe_expr import ExpressionError, evaluate
        self.assertEqual(evaluate('a*b + 2', {'a': 3, 'b': 4}), 14)
        for text in ('__import__("os")', 'a.real', 'c + 1', '[a]', 'a ** b'):
            with self.subTest(text=text), self.assertRaises(ExpressionError):
                evaluate(text, {'a': 3, 'b': 4})


@unittest.skipUnless(has('pint'), 'pint not installed')
class DimcheckTests(unittest.TestCase):
    def test_consistent_inconsistent_and_mixed_addition(self):
        from dimcheck import main
        self.assertEqual(run(main, ['E = 0.5*m*v**2', '--units', 'E:J,m:kg,v:m/s'])[0], 0)
        code, report = run(main, ['F = m*v', '--units', 'F:N,m:kg,v:m/s'])
        self.assertEqual((code, report['consistent']), (1, False))
        code, report = run(main, ['x = a + b', '--units', 'x:m,a:m,b:s'])
        self.assertEqual(code, 1)
        self.assertIn('added or subtracted', report['errors'][0])

    def test_invalid_input_exits_two(self):
        from dimcheck import main
        self.assertEqual(run(main, ['F = m*a', '--units', 'F:N,m:kg'])[0], 2)
        self.assertEqual(run(main, ['F = m*a', '--units', 'F:N,m:kg,a:notaunit'])[0], 2)


@unittest.skipUnless(has('uncertainties'), 'uncertainties not installed')
class UncertaintyTests(unittest.TestCase):
    def test_quotient_matches_hand_calculation(self):
        from uncertainty import main
        code, report = run(main, ['m / V', '--var', 'm=12.31:0.02,V=4.52:0.05'])
        expected = (12.31 / 4.52) * ((0.02 / 12.31) ** 2 + (0.05 / 4.52) ** 2) ** 0.5
        self.assertEqual(code, 0)
        self.assertAlmostEqual(report['standard_uncertainty'], expected, places=10)
        self.assertEqual(report['reported'], '2.723 ± 0.030')

    def test_repeated_symbol_is_correlated(self):
        from uncertainty import main
        _, report = run(main, ['x - x', '--var', 'x=5:0.1'])
        self.assertAlmostEqual(report['standard_uncertainty'], 0.0)


@unittest.skipUnless(has('statsmodels'), 'statsmodels not installed')
class StatisticsTests(unittest.TestCase):
    def test_textbook_sample_size(self):
        from power import main
        code, report = run(main, ['--effect', '0.5', '--power', '0.8'])
        self.assertEqual((code, report['n_group1']), (0, 64))
        self.assertEqual(run(main, ['--effect', '0.5'])[0], 2)

    def test_benjamini_hochberg(self):
        from multiplicity import main
        code, report = run(main, ['--p', '0.01', '0.04', '0.03', '0.20'])
        self.assertEqual(code, 0)
        self.assertEqual((report['significant_unadjusted'], report['significant_adjusted']), (3, 1))
        self.assertAlmostEqual(report['results'][0]['p_adjusted'], 0.04)
        self.assertEqual(run(main, ['--p', '1.5'])[0], 2)



@unittest.skipUnless(has('numpy') and has('scipy'), 'numpy/scipy not installed')
class CompareModelsTests(unittest.TestCase):
    def write(self, directory, rows, header='unit,fold,y,a,b'):
        path = Path(directory) / 'pred.csv'
        path.write_text(header + '\n' + '\n'.join(','.join(map(str, r)) for r in rows) + '\n')
        return path

    def test_detects_better_model_and_corrected_t_matches_hand_value(self):
        import random
        from compare_models import main
        rng = random.Random(3)
        rows = []
        for unit in range(40):
            y = rng.gauss(10, 2)
            rows.append([f'u{unit}', unit % 5, round(y, 4), round(y + rng.gauss(0, 1.0), 4), round(y + rng.gauss(0, 0.4), 4)])
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, rows)
            code, report = run(main, [str(path), '--truth', 'y', '--a', 'a', '--b', 'b', '--fold', 'fold', '--group', 'unit'])
        self.assertEqual(code, 0)
        self.assertTrue(report['paired_difference']['mae']['ci_excludes_zero'])
        self.assertGreater(report['paired_difference']['mae']['ci95'][0], 0)
        # Hand calculation of the Nadeau-Bengio statistic from per-fold MAE differences.
        folds = {}
        for _, fold, y, a, b in rows:
            folds.setdefault(fold, []).append((abs(a - y), abs(b - y)))
        d = [sum(x for x, _ in v) / len(v) - sum(z for _, z in v) / len(v) for v in folds.values()]
        mean = sum(d) / 5
        var = sum((x - mean) ** 2 for x in d) / 4
        expected_t = mean / ((1 / 5 + 0.2 / 0.8) * var) ** 0.5
        self.assertAlmostEqual(report['corrected_resampled_t_test']['mae']['t'], round(expected_t, 4), places=3)
        self.assertLess(report['corrected_resampled_t_test']['mae']['naive_p_uncorrected'],
                        report['corrected_resampled_t_test']['mae']['p'])

    def test_replicates_are_not_independent_units(self):
        from compare_models import main
        rows = [[f'u{i // 3}', 0, 1.0 + i, 1.1 + i, 1.2 + i] for i in range(9)]
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, rows)
            code, report = run(main, [str(path), '--truth', 'y', '--a', 'a', '--b', 'b', '--group', 'unit'])
        self.assertEqual(code, 1)
        self.assertEqual(report['n_units'], 3)
        self.assertTrue(any('independent units' in w for w in report['warnings']))

    def test_error_below_measurement_noise_is_flagged(self):
        from compare_models import main
        rows = [[f'u{i}', 0, float(i), i + 0.01 * (-1) ** i, i + 0.02 * (-1) ** i] for i in range(20)]
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, rows)
            reps = Path(directory) / 'reps.csv'
            reps.write_text('id,value\nr1,1.0\nr1,1.5\nr2,2.0\nr2,2.6\n')
            code, report = run(main, [str(path), '--truth', 'y', '--a', 'a', '--b', 'b', '--replicates', str(reps)])
        self.assertEqual(code, 1)
        self.assertTrue(any('below the measurement repeatability' in w for w in report['warnings']))

    def test_missing_column_exits_two(self):
        from compare_models import main
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, [[1, 0, 1, 1, 1]])
            self.assertEqual(run(main, [str(path), '--truth', 'y', '--a', 'a', '--b', 'missing'])[0], 2)

    def test_identical_predictions_do_not_report_significance(self):
        from compare_models import main
        rows = [[f'u{i}', i // 4, i + 0.1, i + 0.3, i + 0.3] for i in range(12)]
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, rows)
            code, report = run(main, [str(path), '--truth', 'y', '--a', 'a', '--b', 'b',
                                      '--fold', 'fold', '--task', 'regression', '--n-boot', '20'])
        self.assertEqual(code, 0)
        for metric in ('mae', 'rmse'):
            result = report['corrected_resampled_t_test'][metric]
            self.assertEqual(result['mean_difference'], 0.0)
            self.assertEqual(result['p'], 1.0)
            self.assertEqual(result['t'], 0.0)
            self.assertFalse(report['paired_difference'][metric]['ci_excludes_zero'])


def write_csv(directory, name, header, rows):
    path = Path(directory) / name
    path.write_text(','.join(header) + '\n' + '\n'.join(','.join(map(str, r)) for r in rows) + '\n')
    return path


@unittest.skipUnless(has('numpy') and has('scipy') and has('statsmodels'), 'statistics packages not installed')
class AutoTestTests(unittest.TestCase):
    def choose(self, header, rows, *args):
        from auto_test import main
        with tempfile.TemporaryDirectory() as directory:
            path = write_csv(directory, 'd.csv', header, rows)
            return run(main, [str(path), *args])

    def test_replicates_are_averaged_and_welch_is_chosen_for_normal_data(self):
        import random
        rng = random.Random(1)
        rows = [[f'{c}{i}', c, rng.gauss(10 if c == 'A' else 12, 1)] for c in 'AB' for i in range(15) for _ in range(3)]
        code, report = self.choose(['film', 'cond', 'y'], rows, '--value', 'y', '--condition', 'cond', '--unit', 'film')
        self.assertEqual(report['test'], 'Welch t-test')
        self.assertEqual(report['n_units_per_condition'], {'A': 15, 'B': 15})
        self.assertLess(report['p'], 0.05)

    def test_skewed_independent_data_uses_rank_test(self):
        import random
        rng = random.Random(2)
        rows = [[c, rng.expovariate(1.0) ** 3 * (1 if c == 'a' else 2)] for c in 'ab' for _ in range(20)]
        code, report = self.choose(['cond', 'y'], rows, '--value', 'y', '--condition', 'cond')
        self.assertEqual(report['test'], 'Mann-Whitney U')

    def test_paired_design_is_detected(self):
        import random
        rng = random.Random(3)
        rows = []
        for d in range(12):
            base = rng.gauss(5, 2)
            rows += [[f'd{d}', 'pre', base], [f'd{d}', 'post', base + rng.gauss(1, 0.3)]]
        code, report = self.choose(['donor', 'time', 'y'], rows, '--value', 'y', '--condition', 'time', '--unit', 'donor')
        self.assertEqual(report['design'], 'paired')
        self.assertIn(report['test'], ('Paired t-test', 'Wilcoxon signed-rank'))

    def test_partial_pairing_requires_design_confirmation(self):
        for shared in (7, 8, 9):
            for binary in (False, True):
                with self.subTest(shared=shared, binary=binary):
                    rows = [[f'u{i}', 'A', i % 2 if binary else i + 0.1] for i in range(10)]
                    rows += [[f'u{i}', 'B', (i + 1) % 2 if binary else i + 0.2]
                             for i in range(shared)]
                    code, report = self.choose(['unit', 'cond', 'y'], rows, '--value', 'y',
                                               '--condition', 'cond', '--unit', 'unit')
                    self.assertEqual(code, 2)
                    self.assertIn('partially paired', report['error'])
                    self.assertNotIn('p', report)

    def test_overlap_without_any_complete_units_is_not_independent(self):
        rows = [[f'u{i}', c, i + offset + 0.1]
                for i in range(6) for offset, c in enumerate(('AB', 'BC', 'AC')[i % 3])]
        code, report = self.choose(['unit', 'cond', 'y'], rows, '--value', 'y',
                                   '--condition', 'cond', '--unit', 'unit')
        self.assertEqual(code, 2)
        self.assertIn('partially paired', report['error'])
        self.assertNotIn('p', report)

    def test_unequal_variances_with_three_groups(self):
        import random
        rng = random.Random(4)
        rows = [[c, rng.gauss(m, sd)] for c, m, sd in (('a', 5, 0.3), ('b', 6, 3.0), ('c', 5.5, 1.0)) for _ in range(25)]
        code, report = self.choose(['cond', 'y'], rows, '--value', 'y', '--condition', 'cond')
        self.assertTrue(report['test'].startswith('Alexander-Govern'))
        self.assertEqual(len(report['post_hoc']), 3)

    def test_binary_outcomes(self):
        rows = [[f'u{i}', t, int(i % 3 == 0) if t == 'before' else int(i % 2 == 0)] for i in range(30) for t in ('before', 'after')]
        code, report = self.choose(['unit', 'time', 'ok'], rows, '--value', 'ok', '--condition', 'time', '--unit', 'unit')
        self.assertTrue(report['test'].startswith('McNemar'))
        rows = [[g, 1 if i < k else 0] for g, k in (('x', 2), ('y', 7)) for i in range(9)]
        code, report = self.choose(['g', 'ok'], rows, '--value', 'ok', '--condition', 'g')
        self.assertEqual(report['test'], "Fisher's exact")


@unittest.skipUnless(has('numpy') and has('scipy') and has('statsmodels'), 'statistics packages not installed')
class ClassificationCompareTests(unittest.TestCase):
    def test_labels_switch_to_classification(self):
        from compare_models import main
        rows = [[i % 2, i % 2, (i % 2) if i % 5 else 1 - i % 2] for i in range(100)]
        with tempfile.TemporaryDirectory() as directory:
            path = write_csv(directory, 'c.csv', ['y', 'a', 'b'], rows)
            code, report = run(main, [str(path), '--truth', 'y', '--a', 'a', '--b', 'b'])
        self.assertEqual(report['task'], 'classification')
        self.assertEqual(report['models']['a']['accuracy'], 1.0)
        self.assertEqual(report['mcnemar']['only_a_correct'], 20)
        self.assertTrue(report['paired_difference']['accuracy']['ci_excludes_zero'])


class ChooseEvaluationTests(unittest.TestCase):
    def recommend(self, header, rows, *args):
        from choose_evaluation import main
        with tempfile.TemporaryDirectory() as directory:
            path = write_csv(directory, 'e.csv', header, rows)
            return run(main, [str(path), *args])

    def test_groups_time_and_imbalance(self):
        rows = [[f'c{i // 4}', i, i * 0.5 + 1] for i in range(80)]
        code, report = self.recommend(['compound', 'x', 'y'], rows, '--target', 'y', '--group', 'compound')
        self.assertIn('GroupKFold', report['split']['scheme'])
        code, report = self.recommend(['t', 'y'], [[i, i * 1.5 + 0.3] for i in range(50)], '--target', 'y', '--time', 't')
        self.assertIn('time split', report['split']['scheme'])
        code, report = self.recommend(['y'], [[1 if i < 5 else 0] for i in range(100)], '--target', 'y')
        self.assertEqual(report['task'], 'classification')
        self.assertIn('PR-AUC (precision-recall)', report['metrics'])
        self.assertTrue(any('accuracy is misleading' in n for n in report['notes']))

@unittest.skipUnless(has('rdkit'), 'rdkit not installed')
class SmilesTests(unittest.TestCase):
    def test_invalid_duplicate_and_leakage(self):
        from smiles_check import main
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mols.csv'
            path.write_text('smiles,split\nCCO,train\nOCC,test\nc1ccccc1C,train\nc1ccccc1CC,test\nnot_a_smiles,train\n')
            code, report = run(main, [str(path), '--split-column', 'split'])
        self.assertEqual(code, 1)
        self.assertEqual(report['n_invalid'], 1)
        self.assertEqual(report['n_duplicate_groups'], 1)
        overlap = report['split_overlap'][0]
        self.assertEqual((overlap['shared_molecules'], overlap['shared_scaffolds']), (1, 1))


@unittest.skipUnless(has('Bio'), 'biopython not installed')
class SequenceTests(unittest.TestCase):
    def test_flags_near_identical_sequence(self):
        from sequence_identity import main
        with tempfile.TemporaryDirectory() as directory:
            train, test = Path(directory) / 'train.fa', Path(directory) / 'test.fa'
            train.write_text('>a\nMKTAYIAKQRQISFVKSHFSRQ\n>b\nGGGGSSSSPPPP\n')
            test.write_text('>close\nMKTAYIAKQRQISFVKSHFSRA\n>far\nWWWWYYYYHHHHCCCC\n')
            code, report = run(main, [str(train), str(test), '--threshold', '0.9'])
        self.assertEqual(code, 1)
        self.assertEqual([row['test'] for row in report['flagged']], ['close'])


if __name__ == '__main__':
    unittest.main()
