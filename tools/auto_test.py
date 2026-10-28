#!/usr/bin/env python3
"""Choose and run a statistical test for comparing conditions, from the data and the design.

Example:
    python tools/auto_test.py data.csv --value yield --condition catalyst
    python tools/auto_test.py data.csv --value migration --condition treatment --unit donor

The CSV is in long format: one row per measurement. --unit names the independent unit (sample,
donor, film). Replicate rows of the same unit and condition are averaged first. The design is
paired when most units were measured under every condition. The test is chosen from the design
(paired or independent, number of conditions), the data type (continuous or binary), the sample
size and diagnostic checks (normality of residuals or differences, equal variances). The decision
path, the test result, an effect size and the alternatives considered are reported as JSON.

Exits 0 when the analysis ran without warnings, 1 when it ran with warnings, 2 on invalid input or
a missing package. Requires: numpy, scipy, statsmodels (requirements/base.txt).
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from itertools import combinations

SMALL = 8     # below this many units per condition, rank tests cannot reach usual significance
LARGE = 30    # from this many units per condition, t-based tests are robust to non-normality


def read(path, value, condition, unit):
    with open(path, newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in (value, condition, unit) if c and c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f'missing column(s): {", ".join(missing)}')
        rows = [r for r in reader if (r.get(value) or '').strip() != '']
    if not rows:
        raise ValueError('no rows with a value')
    return rows


def classify(values):
    unique = set(values)
    if unique <= {0.0, 1.0}:
        return 'binary'
    return 'continuous'


def aggregate(rows, value, condition, unit):
    """Average replicates per (unit, condition). Without --unit every row is its own unit."""
    cells = defaultdict(list)
    for index, row in enumerate(rows):
        key = (row[unit] if unit else f'row{index}', row[condition])
        cells[key].append(float(row[value]))
    replicated = any(len(v) > 1 for v in cells.values())
    return {k: sum(v) / len(v) for k, v in cells.items()}, replicated


def holm(pvalues):
    from statsmodels.stats.multitest import multipletests
    return [float(p) for p in multipletests(pvalues, method='holm')[1]] if pvalues else []


def normal_enough(sample, path, label):
    """Shapiro-Wilk as a diagnostic. Returns True when no strong evidence against normality."""
    from scipy import stats
    if len(sample) < 3:
        path.append(f'{label}: too few values for a normality check.')
        return False
    p = float(stats.shapiro(sample).pvalue)
    ok = p >= 0.05
    path.append(f'{label}: Shapiro-Wilk p = {p:.3g} -> {"no strong evidence against normality" if ok else "not normal"}.')
    return ok


def standardized(groups):
    """Residuals scaled by each condition's SD, so unequal variances are not mistaken for non-normality."""
    import numpy as np
    parts = [(g - g.mean()) / g.std(ddof=1) for g in map(np.asarray, groups) if len(g) > 1 and g.std(ddof=1) > 0]
    return np.concatenate(parts) if parts else np.array([])


def hedges_g(a, b):
    import numpy as np
    a, b = np.asarray(a), np.asarray(b)
    na, nb = len(a), len(b)
    pooled = math.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if pooled == 0:
        return None
    return float((a.mean() - b.mean()) / pooled * (1 - 3 / (4 * (na + nb) - 9)))


def two_independent(a, b, names, path, warnings):
    import numpy as np
    from scipy import stats
    a, b = np.asarray(a), np.asarray(b)
    n_min = min(len(a), len(b))
    residuals = standardized([a, b])
    normal = n_min >= LARGE or normal_enough(residuals, path, 'Residuals (standardized within condition)')
    if n_min >= LARGE:
        path.append(f'At least {LARGE} units per condition: Welch t-test is robust.')
    if normal:
        test = stats.ttest_ind(a, b, equal_var=False)
        ci = test.confidence_interval()
        path.append('Chose Welch t-test (does not assume equal variances).')
        return {'test': 'Welch t-test', 'statistic': float(test.statistic), 'p': float(test.pvalue),
                'effect': {'mean_difference': float(a.mean() - b.mean()), 'ci95': [float(ci.low), float(ci.high)],
                           'hedges_g': hedges_g(a, b)},
                'alternatives': ['Mann-Whitney U if the distribution is strongly skewed or has outliers']}
    if n_min >= SMALL:
        test = stats.mannwhitneyu(a, b)
        r = 1 - 2 * float(test.statistic) / (len(a) * len(b))
        path.append('Chose Mann-Whitney U (rank-based; no normality assumption).')
        return {'test': 'Mann-Whitney U', 'statistic': float(test.statistic), 'p': float(test.pvalue),
                'effect': {'median_difference': float(np.median(a) - np.median(b)), 'rank_biserial': -r},
                'alternatives': ['Welch t-test if residuals were approximately normal']}
    test = stats.permutation_test((a, b), lambda x, y: np.mean(x) - np.mean(y), n_resamples=20000, random_state=0)
    path.append(f'Fewer than {SMALL} units per condition and not normal: chose a permutation test of the mean difference.')
    warnings.append(f'Small sample ({len(a)} vs {len(b)} units): low power; report every value.')
    return {'test': 'Permutation test (difference of means)', 'statistic': float(test.statistic), 'p': float(test.pvalue),
            'effect': {'mean_difference': float(a.mean() - b.mean()), 'hedges_g': hedges_g(a, b)},
            'alternatives': ['Welch t-test if normality can be assumed from prior knowledge']}


def two_paired(a, b, path, warnings):
    import numpy as np
    from scipy import stats
    a, b = np.asarray(a), np.asarray(b)
    d = a - b
    n = len(d)
    normal = n >= LARGE or normal_enough(d, path, 'Paired differences')
    sd = d.std(ddof=1) if n > 1 else 0
    if normal:
        test = stats.ttest_rel(a, b)
        ci = test.confidence_interval()
        path.append('Chose paired t-test.')
        return {'test': 'Paired t-test', 'statistic': float(test.statistic), 'p': float(test.pvalue),
                'effect': {'mean_difference': float(d.mean()), 'ci95': [float(ci.low), float(ci.high)],
                           'dz': float(d.mean() / sd) if sd else None},
                'alternatives': ['Wilcoxon signed-rank if differences are skewed']}
    if n >= SMALL:
        test = stats.wilcoxon(a, b)
        path.append('Chose Wilcoxon signed-rank test (no normality assumption).')
        return {'test': 'Wilcoxon signed-rank', 'statistic': float(test.statistic), 'p': float(test.pvalue),
                'effect': {'median_difference': float(np.median(d)), 'dz': float(d.mean() / sd) if sd else None},
                'alternatives': ['Paired t-test if differences were approximately normal']}
    test = stats.permutation_test((d,), np.mean, permutation_type='samples', n_resamples=20000, random_state=0)
    path.append(f'Fewer than {SMALL} pairs and not normal: chose a sign-flip permutation test.')
    warnings.append(f'Small sample ({n} pairs): low power; report every value.')
    return {'test': 'Sign-flip permutation test (paired)', 'statistic': float(test.statistic), 'p': float(test.pvalue),
            'effect': {'mean_difference': float(d.mean())}, 'alternatives': ['Paired t-test']}


def many_independent(groups, names, path, warnings):
    import numpy as np
    from scipy import stats
    arrays = [np.asarray(g) for g in groups]
    n_min = min(len(g) for g in arrays)
    residuals = standardized(arrays)
    normal = n_min >= LARGE or normal_enough(residuals, path, 'Residuals (standardized within condition)')
    pairs = list(combinations(range(len(arrays)), 2))
    if normal:
        lev = float(stats.levene(*arrays).pvalue)
        path.append(f'Levene p = {lev:.3g} -> {"equal" if lev >= 0.05 else "unequal"} variances.')
        if lev >= 0.05:
            test = stats.f_oneway(*arrays)
            tukey = stats.tukey_hsd(*arrays)
            post = [{'pair': [names[i], names[j]], 'p_tukey': float(tukey.pvalue[i, j])} for i, j in pairs]
            grand = np.concatenate(arrays)
            eta2 = sum(len(g) * (g.mean() - grand.mean()) ** 2 for g in arrays) / ((grand - grand.mean()) ** 2).sum()
            path.append('Chose one-way ANOVA with Tukey HSD post hoc.')
            return {'test': 'One-way ANOVA + Tukey HSD', 'statistic': float(test.statistic), 'p': float(test.pvalue),
                    'effect': {'eta_squared': float(eta2)}, 'post_hoc': post,
                    'alternatives': ['Kruskal-Wallis if residuals were not normal']}
        test = stats.alexandergovern(*arrays)
        raw = [float(stats.ttest_ind(arrays[i], arrays[j], equal_var=False).pvalue) for i, j in pairs]
        post = [{'pair': [names[i], names[j]], 'p_welch_holm': p} for (i, j), p in zip(pairs, holm(raw))]
        path.append('Chose Alexander-Govern test (unequal variances) with pairwise Welch t-tests, Holm-corrected.')
        return {'test': 'Alexander-Govern + pairwise Welch (Holm)', 'statistic': float(test.statistic), 'p': float(test.pvalue),
                'post_hoc': post, 'alternatives': ['One-way ANOVA if variances were equal']}
    test = stats.kruskal(*arrays)
    n_total = sum(len(g) for g in arrays)
    eps2 = (float(test.statistic) - len(arrays) + 1) / (n_total - len(arrays))
    raw = [float(stats.mannwhitneyu(arrays[i], arrays[j]).pvalue) for i, j in pairs]
    post = [{'pair': [names[i], names[j]], 'p_mannwhitney_holm': p} for (i, j), p in zip(pairs, holm(raw))]
    path.append('Chose Kruskal-Wallis with pairwise Mann-Whitney U, Holm-corrected.')
    if n_min < SMALL:
        warnings.append(f'Some conditions have fewer than {SMALL} units: post hoc tests have little power.')
    return {'test': 'Kruskal-Wallis + pairwise Mann-Whitney (Holm)', 'statistic': float(test.statistic),
            'p': float(test.pvalue), 'effect': {'epsilon_squared': eps2}, 'post_hoc': post,
            'alternatives': ['One-way ANOVA if residuals were normal']}


def many_paired(matrix, names, path, warnings):
    import numpy as np
    from scipy import stats
    data = np.asarray(matrix)  # units x conditions
    residuals = (data - data.mean(axis=1, keepdims=True) - data.mean(axis=0, keepdims=True) + data.mean()).ravel()
    normal = len(data) >= LARGE or normal_enough(residuals, path, 'Residuals (unit and condition removed)')
    pairs = list(combinations(range(data.shape[1]), 2))
    if normal:
        import pandas as pd
        from statsmodels.stats.anova import AnovaRM
        long = pd.DataFrame([{'unit': u, 'condition': names[c], 'value': data[u, c]}
                             for u in range(data.shape[0]) for c in range(data.shape[1])])
        result = AnovaRM(long, 'value', 'unit', within=['condition']).fit().anova_table
        raw = [float(stats.ttest_rel(data[:, i], data[:, j]).pvalue) for i, j in pairs]
        post = [{'pair': [names[i], names[j]], 'p_paired_t_holm': p} for (i, j), p in zip(pairs, holm(raw))]
        path.append('Chose repeated-measures ANOVA with pairwise paired t-tests, Holm-corrected.')
        warnings.append('Repeated-measures ANOVA assumes sphericity; it is not tested here.')
        return {'test': 'Repeated-measures ANOVA + paired t (Holm)', 'statistic': float(result['F Value'].iloc[0]),
                'p': float(result['Pr > F'].iloc[0]), 'post_hoc': post, 'alternatives': ['Friedman test']}
    test = stats.friedmanchisquare(*[data[:, c] for c in range(data.shape[1])])
    kendall_w = float(test.statistic) / (data.shape[0] * (data.shape[1] - 1))
    raw = [float(stats.wilcoxon(data[:, i], data[:, j]).pvalue) for i, j in pairs]
    post = [{'pair': [names[i], names[j]], 'p_wilcoxon_holm': p} for (i, j), p in zip(pairs, holm(raw))]
    path.append('Chose Friedman test with pairwise Wilcoxon signed-rank tests, Holm-corrected.')
    return {'test': 'Friedman + pairwise Wilcoxon (Holm)', 'statistic': float(test.statistic), 'p': float(test.pvalue),
            'effect': {'kendall_w': kendall_w}, 'post_hoc': post, 'alternatives': ['Repeated-measures ANOVA']}


def binary_tests(cells, units, names, paired, path, warnings):
    import numpy as np
    from scipy import stats
    if paired and len(names) == 2:
        from statsmodels.stats.contingency_tables import mcnemar
        a = [cells[(u, names[0])] for u in units]
        b = [cells[(u, names[1])] for u in units]
        table = [[sum(1 for x, y in zip(a, b) if x == 1 and y == 1), sum(1 for x, y in zip(a, b) if x == 1 and y == 0)],
                 [sum(1 for x, y in zip(a, b) if x == 0 and y == 1), sum(1 for x, y in zip(a, b) if x == 0 and y == 0)]]
        exact = table[0][1] + table[1][0] < 25
        result = mcnemar(table, exact=exact)
        path.append(f'Binary outcome, paired, two conditions: chose McNemar test ({"exact" if exact else "chi-square"}).')
        return {'test': 'McNemar' + (' (exact)' if exact else ''), 'statistic': float(result.statistic),
                'p': float(result.pvalue), 'table': table,
                'effect': {'difference_in_proportions': (table[0][1] - table[1][0]) / len(units)}}
    if paired:
        from statsmodels.stats.contingency_tables import cochrans_q
        matrix = np.array([[cells[(u, c)] for c in names] for u in units])
        result = cochrans_q(matrix)
        path.append("Binary outcome, paired, more than two conditions: chose Cochran's Q.")
        return {'test': "Cochran's Q", 'statistic': float(result.statistic), 'p': float(result.pvalue)}
    counts = [[sum(1 for (u, c), v in cells.items() if c == name and v == k) for k in (1, 0)] for name in names]
    table = np.array(counts)
    expected = stats.contingency.expected_freq(table)
    if len(names) == 2 and expected.min() < 5:
        result = stats.fisher_exact(table)
        path.append("Binary outcome, two independent conditions, expected count < 5: chose Fisher's exact test.")
        name, stat = "Fisher's exact", float(result.statistic)
        p = float(result.pvalue)
    else:
        chi = stats.chi2_contingency(table)
        if expected.min() < 5:
            warnings.append('Some expected counts are below 5: the chi-square approximation is unreliable.')
        path.append('Binary outcome, independent conditions: chose chi-square test of independence.')
        name, stat, p = 'Chi-square', float(chi.statistic), float(chi.pvalue)
    props = {names[i]: float(table[i, 0] / table[i].sum()) for i in range(len(names))}
    return {'test': name, 'statistic': stat, 'p': p, 'table': counts, 'effect': {'proportions': props}}


def analyse(rows, value, condition, unit=None, design='auto'):
    path, warnings = [], []
    raw_values = [float(r[value]) for r in rows]
    kind = classify(raw_values)
    path.append(f'Outcome type: {kind}.')
    cells, replicated = aggregate(rows, value, condition, unit)
    if replicated:
        path.append(f'Replicate rows of the same {unit} and condition were averaged: the {unit} is the unit of analysis.')
        if kind == 'binary':
            kind = 'continuous'
            path.append('Averaged binary replicates are proportions: treated as continuous.')
    names = sorted({c for _, c in cells})
    if len(names) < 2:
        raise ValueError('need at least two conditions')
    units = sorted({u for u, _ in cells})
    complete = [u for u in units if all((u, c) in cells for c in names)]
    if design == 'auto':
        design = 'paired' if unit and len(complete) >= 0.8 * len(units) and len(complete) >= 2 else 'independent'
        path.append(f'Design: {design} ({len(complete)} of {len(units)} units measured under every condition).')
    if design == 'paired':
        if len(complete) < len(units):
            warnings.append(f'{len(units) - len(complete)} units without every condition were dropped for the paired analysis.')
        units = complete
    path.append(f'Conditions: {len(names)} ({", ".join(names)}).')

    if kind == 'binary':
        result = binary_tests(cells, units, names, design == 'paired', path, warnings)
    elif design == 'paired':
        matrix = [[cells[(u, c)] for c in names] for u in units]
        if len(names) == 2:
            result = two_paired([m[0] for m in matrix], [m[1] for m in matrix], path, warnings)
            result['effect']['direction'] = f'{names[0]} minus {names[1]}'
        else:
            result = many_paired(matrix, names, path, warnings)
    else:
        groups = [[v for (u, c), v in cells.items() if c == name] for name in names]
        if len(names) == 2:
            result = two_independent(groups[0], groups[1], names, path, warnings)
            result['effect']['direction'] = f'{names[0]} minus {names[1]}'
        else:
            result = many_independent(groups, names, path, warnings)
    counts = {name: sum(1 for (u, c) in cells if c == name and (design != 'paired' or u in units)) for name in names}
    return {'design': design, 'outcome': kind, 'unit': unit or 'row', 'n_units_per_condition': counts,
            'decision_path': path, **result, 'warnings': warnings,
            'note': ('The test was chosen from the design and data shape. Do not switch tests after seeing the p-value; '
                     'report the chosen test, the effect with its interval, n per condition and any correction. '
                     'If several outcomes or comparisons are tested, correct across them (tools/multiplicity.py).')}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Choose and run a test for comparing conditions.')
    parser.add_argument('csv_file')
    parser.add_argument('--value', required=True, help='measured outcome column')
    parser.add_argument('--condition', required=True, help='condition / group column')
    parser.add_argument('--unit', help='independent unit column (sample, donor, film)')
    parser.add_argument('--design', choices=['auto', 'paired', 'independent'], default='auto')
    args = parser.parse_args(argv)
    try:
        import numpy, scipy, statsmodels  # noqa: F401,E401
    except ImportError:
        print(json.dumps({'error': 'numpy, scipy and statsmodels are required. Install requirements/base.txt.'}))
        return 2
    try:
        report = analyse(read(args.csv_file, args.value, args.condition, args.unit), args.value, args.condition,
                         args.unit, args.design)
    except (OSError, ValueError) as error:
        print(json.dumps({'error': str(error)}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['warnings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
