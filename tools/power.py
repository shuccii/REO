#!/usr/bin/env python3
"""Sample size or achieved power for a two-group comparison (statsmodels).

Examples:
    python tools/power.py --test ttest-ind --effect 0.5 --power 0.8
    python tools/power.py --test ttest-paired --effect 0.5 --n 20

`--effect` is Cohen's d. Give either --power (returns required n) or --n (returns power).
Prints JSON; exits 2 on invalid input. Requires: statsmodels (requirements/base.txt).
"""
import argparse
import json
import math


def analyse(test, effect, alpha=0.05, power=None, n=None, ratio=1.0, alternative='two-sided'):
    from statsmodels.stats.power import TTestIndPower, TTestPower
    if (power is None) == (n is None):
        raise ValueError('give exactly one of power or n')
    if effect <= 0:
        raise ValueError('effect size must be positive')
    report = {'test': test, 'effect_size_d': effect, 'alpha': alpha, 'alternative': alternative}
    if test == 'ttest-ind':
        solver = TTestIndPower()
        if n is None:
            n1 = solver.solve_power(effect_size=effect, alpha=alpha, power=power, ratio=ratio, alternative=alternative)
            report.update(power=power, n_group1=math.ceil(n1), n_group2=math.ceil(n1 * ratio))
        else:
            achieved = solver.power(effect_size=effect, nobs1=n, alpha=alpha, ratio=ratio, alternative=alternative)
            report.update(n_group1=n, n_group2=math.ceil(n * ratio), power=float(achieved))
    elif test == 'ttest-paired':
        solver = TTestPower()
        if n is None:
            pairs = solver.solve_power(effect_size=effect, alpha=alpha, power=power, alternative=alternative)
            report.update(power=power, n_pairs=math.ceil(pairs))
        else:
            report.update(n_pairs=n, power=float(solver.power(effect_size=effect, nobs=n, alpha=alpha, alternative=alternative)))
    else:
        raise ValueError(f'unsupported test: {test}')
    report['note'] = ('The effect size must come from prior data, a pilot or the smallest effect that matters, '
                      'not from the result being evaluated. Post hoc power from the observed effect is not informative.')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Sample size / power for t-tests.')
    parser.add_argument('--test', choices=['ttest-ind', 'ttest-paired'], default='ttest-ind')
    parser.add_argument('--effect', type=float, required=True, help="Cohen's d")
    parser.add_argument('--alpha', type=float, default=0.05)
    parser.add_argument('--power', type=float)
    parser.add_argument('--n', type=int, help='n per group (ind) or number of pairs (paired)')
    parser.add_argument('--ratio', type=float, default=1.0, help='n2 / n1 for ttest-ind')
    parser.add_argument('--alternative', choices=['two-sided', 'larger', 'smaller'], default='two-sided')
    args = parser.parse_args(argv)
    try:
        report = analyse(args.test, args.effect, args.alpha, args.power, args.n, args.ratio, args.alternative)
    except ValueError as error:
        print(json.dumps({'error': str(error)}))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
