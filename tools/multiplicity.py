#!/usr/bin/env python3
"""Adjust p-values for multiple comparisons (statsmodels multipletests).

Examples:
    python tools/multiplicity.py --p 0.01 0.04 0.03 0.20
    python tools/multiplicity.py --file pvalues.txt --method holm

Prints JSON; exits 2 on invalid input. Requires: statsmodels (requirements/base.txt).
"""
import argparse
import json
from pathlib import Path

METHODS = {'fdr_bh': 'Benjamini-Hochberg (FDR)', 'bonferroni': 'Bonferroni (FWER)', 'holm': 'Holm (FWER)', 'fdr_by': 'Benjamini-Yekutieli (FDR, dependent tests)'}


def adjust(pvalues, method='fdr_bh', alpha=0.05, labels=None):
    from statsmodels.stats.multitest import multipletests
    if not pvalues:
        raise ValueError('no p-values given')
    if any(not 0 <= p <= 1 for p in pvalues):
        raise ValueError('p-values must be between 0 and 1')
    if method not in METHODS:
        raise ValueError(f'unsupported method: {method}')
    labels = labels or [f'test{i + 1}' for i in range(len(pvalues))]
    reject, adjusted, _, _ = multipletests(pvalues, alpha=alpha, method=method)
    rows = [{'label': label, 'p': p, 'p_adjusted': float(q), 'significant': bool(r)}
            for label, p, q, r in zip(labels, pvalues, adjusted, reject)]
    naive = sum(p < alpha for p in pvalues)
    return {
        'method': METHODS[method], 'alpha': alpha, 'n_tests': len(pvalues),
        'significant_unadjusted': naive, 'significant_adjusted': int(sum(reject)), 'results': rows,
        'note': 'Count every test that was run (all outcomes, subgroups and models), not only the ones reported.',
    }


def read_file(path):
    labels, pvalues = [], []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [part.strip() for part in line.replace('\t', ',').split(',')]
        if len(parts) == 1:
            pvalues.append(float(parts[0]))
        else:
            labels.append(parts[0])
            pvalues.append(float(parts[1]))
    return pvalues, (labels if len(labels) == len(pvalues) else None)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Multiple-comparison correction.')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--p', type=float, nargs='+', help='p-values')
    source.add_argument('--file', help='one p-value per line, or "label,p"')
    parser.add_argument('--method', choices=sorted(METHODS), default='fdr_bh')
    parser.add_argument('--alpha', type=float, default=0.05)
    args = parser.parse_args(argv)
    try:
        pvalues, labels = (args.p, None) if args.p else read_file(args.file)
        report = adjust(pvalues, args.method, args.alpha, labels)
    except (ValueError, OSError) as error:
        print(json.dumps({'error': str(error)}))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
