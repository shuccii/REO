#!/usr/bin/env python3
"""Compare two regression models on the same samples with paired statistics.

Example:
    python tools/compare_models.py predictions.csv --truth y --a pred_rf --b pred_gp
    python tools/compare_models.py predictions.csv --truth y --a pred_rf --b pred_gp --fold fold --group sample_id
    python tools/compare_models.py predictions.csv --truth y --a pred_rf --b pred_gp --replicates repeats.csv

The CSV has one row per (sample, fold) prediction made on held-out data. Reports, for A and B:
MAE, RMSE and R2; the paired difference with a bootstrap confidence interval (resampling groups
when --group is given); a Wilcoxon signed-rank test and a paired effect size on per-unit errors;
and, with --fold, the corrected resampled t-test (Nadeau and Bengio) on per-fold metrics.
With --replicates (columns: id,value), the RMSE is compared with the measurement repeatability.

Prints JSON. Exits 0 when the comparison ran without warnings, 1 when it ran but a warning needs
attention (for example, too few independent units or error below measurement noise), and 2 on
invalid input or a missing package. Requires: numpy, scipy (requirements/base.txt).
"""
import argparse
import csv
import json
import math
from collections import defaultdict

METRICS = ('mae', 'rmse')


def metric(errors, name):
    import numpy as np
    errors = np.asarray(errors, dtype=float)
    return float(np.mean(np.abs(errors))) if name == 'mae' else float(np.sqrt(np.mean(errors ** 2)))


def r2(truth, pred):
    import numpy as np
    truth, pred = np.asarray(truth, float), np.asarray(pred, float)
    return float(1 - ((truth - pred) ** 2).sum() / ((truth - truth.mean()) ** 2).sum())


def read_rows(path, columns):
    with open(path, newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in columns if c and c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f'missing column(s): {", ".join(missing)}')
        rows = list(reader)
    if not rows:
        raise ValueError('no rows')
    return rows


def unit_errors(rows, truth, a, b, group):
    """Per-unit absolute and squared errors. A unit is a row, or a group mean when --group is given."""
    units = defaultdict(lambda: {'ea': [], 'eb': []})
    for index, row in enumerate(rows):
        key = row[group] if group else index
        y = float(row[truth])
        units[key]['ea'].append(float(row[a]) - y)
        units[key]['eb'].append(float(row[b]) - y)
    return list(units.keys()), [u['ea'] for u in units.values()], [u['eb'] for u in units.values()]


def bootstrap_difference(errors_a, errors_b, name, n_boot, seed):
    """Bootstrap CI of metric(A) - metric(B), resampling units (rows or whole groups)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    n = len(errors_a)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.integers(0, n, n)
        ea = [e for j in pick for e in errors_a[j]]
        eb = [e for j in pick for e in errors_b[j]]
        diffs[i] = metric(ea, name) - metric(eb, name)
    low, high = np.percentile(diffs, [2.5, 97.5])
    return float(low), float(high)


def corrected_t_test(rows, truth, a, b, fold, name, test_fraction):
    """Nadeau-Bengio corrected resampled t-test on per-fold metric differences."""
    import numpy as np
    from scipy import stats
    by_fold = defaultdict(lambda: {'ea': [], 'eb': []})
    for row in rows:
        y = float(row[truth])
        by_fold[row[fold]]['ea'].append(float(row[a]) - y)
        by_fold[row[fold]]['eb'].append(float(row[b]) - y)
    d = np.array([metric(v['ea'], name) - metric(v['eb'], name) for v in by_fold.values()])
    k = len(d)
    if k < 2:
        return None
    ratio = test_fraction / (1 - test_fraction)
    variance = (1 / k + ratio) * d.var(ddof=1)
    t = float(d.mean() / math.sqrt(variance)) if variance > 0 else float('inf') * np.sign(d.mean())
    p = float(2 * stats.t.sf(abs(t), df=k - 1)) if math.isfinite(t) else 0.0
    return {'n_folds': k, 'test_fraction': round(test_fraction, 4), 'mean_difference': float(d.mean()),
            't': round(t, 4) if math.isfinite(t) else None, 'df': k - 1, 'p': p,
            'naive_p_uncorrected': float(stats.ttest_1samp(d, 0).pvalue) if d.var() > 0 else None}


def repeatability(path):
    """Pooled within-id standard deviation of repeated measurements (columns: id,value)."""
    import numpy as np
    groups = defaultdict(list)
    for row in read_rows(path, ('id', 'value')):
        groups[row['id']].append(float(row['value']))
    usable = [np.asarray(v) for v in groups.values() if len(v) > 1]
    if not usable:
        raise ValueError('replicates file needs at least one id with two or more values')
    pooled = sum(((v - v.mean()) ** 2).sum() for v in usable) / sum(len(v) - 1 for v in usable)
    return float(math.sqrt(pooled)), len(usable)


def analyse(rows, truth, a, b, fold=None, group=None, test_fraction=None, replicates=None, n_boot=2000, seed=0):
    import numpy as np
    from scipy import stats
    y = [float(r[truth]) for r in rows]
    pa, pb = [float(r[a]) for r in rows], [float(r[b]) for r in rows]
    ea, eb = np.subtract(pa, y), np.subtract(pb, y)
    report = {'n_rows': len(rows), 'models': {
        a: {'mae': metric(ea, 'mae'), 'rmse': metric(ea, 'rmse'), 'r2': r2(y, pa)},
        b: {'mae': metric(eb, 'mae'), 'rmse': metric(eb, 'rmse'), 'r2': r2(y, pb)}}}
    warnings = []
    keys, unit_a, unit_b = unit_errors(rows, truth, a, b, group)
    report['independent_unit'] = group or 'row'
    report['n_units'] = len(keys)
    if len(keys) < 10:
        warnings.append(f'Only {len(keys)} independent units: intervals and tests are unreliable.')

    comparison = {}
    for name in METRICS:
        low, high = bootstrap_difference(unit_a, unit_b, name, n_boot, seed)
        comparison[name] = {'difference_a_minus_b': report['models'][a][name] - report['models'][b][name],
                            'ci95': [low, high], 'ci_excludes_zero': low > 0 or high < 0}
    report['paired_difference'] = comparison

    abs_a = np.array([np.mean(np.abs(u)) for u in unit_a])
    abs_b = np.array([np.mean(np.abs(u)) for u in unit_b])
    diff = abs_a - abs_b
    if np.any(diff != 0):
        w = stats.wilcoxon(abs_a, abs_b)
        report['wilcoxon_abs_error'] = {'statistic': float(w.statistic), 'p': float(w.pvalue),
                                        'unit': report['independent_unit']}
    sd = diff.std(ddof=1) if len(diff) > 1 else 0.0
    report['effect_size_dz'] = float(diff.mean() / sd) if sd > 0 else None

    if fold:
        if test_fraction is None:
            n_folds = len({r[fold] for r in rows})
            # 1 / n_folds is only right for a single k-fold run; repeated CV must pass --test-fraction.
            test_fraction = 1 / n_folds if 1 < n_folds <= 10 else None
        if test_fraction is None or not 0 < test_fraction < 1:
            warnings.append('Corrected t-test skipped: give --test-fraction (test size / total).')
        else:
            report['corrected_resampled_t_test'] = {
                name: corrected_t_test(rows, truth, a, b, fold, name, test_fraction) for name in METRICS}

    if replicates:
        noise_sd, n_ids = repeatability(replicates)
        report['measurement_noise'] = {'repeatability_sd': noise_sd, 'n_ids': n_ids}
        for model in (a, b):
            ratio = report['models'][model]['rmse'] / noise_sd if noise_sd > 0 else None
            report['measurement_noise'][f'{model}_rmse_over_noise'] = ratio
            if ratio is not None and ratio < 1:
                warnings.append(f'{model}: RMSE is below the measurement repeatability. Check for leakage or '
                                'evaluation on replicates of training samples before claiming this accuracy.')
    report['warnings'] = warnings
    report['note'] = ('Differences are A minus B: negative means A has the smaller error. A bootstrap interval that '
                      'excludes zero and the corrected t-test are the main evidence; the uncorrected fold t-test is shown '
                      'only for comparison and overstates significance. Statistics quantify evidence; they do not prove a claim.')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Paired statistical comparison of two regression models.')
    parser.add_argument('csv_file')
    parser.add_argument('--truth', required=True, help='column with measured values')
    parser.add_argument('--a', required=True, help='column with predictions of model A')
    parser.add_argument('--b', required=True, help='column with predictions of model B')
    parser.add_argument('--fold', help='column with the CV fold (or repeat-fold) id of each held-out prediction')
    parser.add_argument('--group', help='column with the independent unit (sample, film, patient)')
    parser.add_argument('--test-fraction', type=float, help='test size / total per fold (default: 1 / number of folds)')
    parser.add_argument('--replicates', help='CSV with columns id,value of repeated measurements')
    parser.add_argument('--n-boot', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError:
        print(json.dumps({'error': 'numpy and scipy are required. Install requirements/base.txt.'}))
        return 2
    try:
        rows = read_rows(args.csv_file, (args.truth, args.a, args.b, args.fold, args.group))
        report = analyse(rows, args.truth, args.a, args.b, args.fold, args.group, args.test_fraction,
                         args.replicates, args.n_boot, args.seed)
    except (OSError, ValueError) as error:
        print(json.dumps({'error': str(error)}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['warnings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
