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
