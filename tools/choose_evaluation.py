#!/usr/bin/env python3
"""Recommend a validation scheme, metrics and baselines for a predictive model from the dataset.

Example:
    python tools/choose_evaluation.py data.csv --target yield
    python tools/choose_evaluation.py data.csv --target active --group compound_id --time date

Looks at the target (regression or classification, skew, zeros, class balance), the number of
independent units, repeated units (--group) and time order (--time), and recommends how to split,
which metrics to report, which baselines to include and how many repeats to run, with the reason for
each choice. It does not train a model. Prints JSON; exits 0, or 1 when a warning needs attention,
2 on invalid input. Standard library only.
"""
import argparse
import csv
import json
import statistics
from collections import Counter


def read(path, columns):
    with open(path, newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in columns if c and c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f'missing column(s): {", ".join(missing)}')
        return list(reader)


def is_number(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


def recommend(rows, target, group=None, time=None, task='auto'):
    values = [r[target].strip() for r in rows if r[target].strip() != '']
    if len(values) < 5:
        raise ValueError('need at least 5 rows with a target value')
    reasons, warnings = [], []
    numeric = all(is_number(v) for v in values)
    distinct = Counter(values)
    if task == 'auto':
        if not numeric or len(distinct) <= 2 or (len(distinct) <= 10 and all(float(v).is_integer() for v in values)):
            task = 'classification'
        else:
            task = 'regression'
        reasons.append(f'Task: {task} ({len(distinct)} distinct target values).')

    n_rows = len(values)
    units = len({r[group] for r in rows}) if group else n_rows
    if group and units < n_rows:
        reasons.append(f'{n_rows} rows but {units} distinct {group}: rows of the same {group} must stay in the same fold.')
    split, repeats = {}, None
    if time:
        split = {'scheme': 'forward-chaining time split (TimeSeriesSplit or rolling origin)',
                 'why': 'Rows are ordered in time; random splits use the future to predict the past.'}
        if group:
            split['also'] = f'keep each {group} in one fold, or split by time within groups'
    elif group and units < n_rows:
        if units < 10:
            split = {'scheme': f'leave-one-{group}-out', 'why': f'Only {units} groups: each group is held out once.'}
        else:
            split = {'scheme': f'GroupKFold (5 folds) on {group}' + (' with stratification (StratifiedGroupKFold)' if task == 'classification' else ''),
                     'why': f'Repeated {group} would leak across folds under a row-level split.'}
    elif units < 30:
        split = {'scheme': 'leave-one-out or repeated 5-fold CV (5 x 10)', 'why': f'Only {units} independent units: a single hold-out is unreliable.'}
    elif units <= 1000:
        split = {'scheme': '5-fold CV' + (' (stratified)' if task == 'classification' else ''), 'why': f'{units} independent units.'}
    else:
        split = {'scheme': 'hold-out test set (20%) plus 5-fold CV on the rest for tuning', 'why': f'{units} independent units.'}
    repeats = 10 if units < 30 else 5 if units <= 300 else 1
    reasons.append(f'Split: {split["scheme"]}. {split["why"]}')
    tuning = 'Tune hyperparameters inside the training folds only (nested CV); never select on the test fold.'

    metrics, baselines, notes = [], [], []
    if task == 'regression':
        y = [float(v) for v in values]
        mean, sd = statistics.fmean(y), statistics.pstdev(y)
        skew = (sum((v - mean) ** 3 for v in y) / len(y)) / sd ** 3 if sd > 0 else 0
        metrics = ['MAE', 'RMSE', 'R2']
        baselines = ['mean of the training targets', 'simple linear (or domain) model']
        if abs(skew) > 1:
            metrics.append('median absolute error')
            notes.append(f'Target is skewed (skewness {skew:.2f}): report median absolute error and consider modelling log(target) if values are positive.')
        if any(abs(v) < 1e-9 for v in y) or min(y) <= 0:
            notes.append('Target has zeros or negative values: do not use MAPE.')
        else:
            notes.append('MAPE is defined (all targets positive) but weights small targets heavily; use it only if relative error is the goal.')
        notes.append(f'Compare RMSE with the target SD ({sd:.4g}) and, if replicate measurements exist, with the measurement repeatability.')
    else:
        counts = Counter(values)
        minority = min(counts.values()) / n_rows
        reasons.append('Class balance: ' + ', '.join(f'{k}: {v}' for k, v in counts.most_common()) + '.')
        metrics = ['confusion matrix', 'balanced accuracy', 'MCC', 'F1 per class']
        baselines = ['majority class', 'stratified random guess']
        if minority < 0.2:
            metrics.append('PR-AUC (precision-recall)')
            notes.append(f'Minority class is {minority:.1%} of rows: accuracy is misleading (predicting the majority gives {1 - minority:.1%}).')
        else:
            metrics.append('ROC-AUC')
        if minority * n_rows < 10:
            warnings.append(f'Only {round(minority * n_rows)} rows in the smallest class: metrics will be unstable.')
    if units < 15:
        warnings.append(f'Only {units} independent units: any comparison has little power; report every prediction.')
    return {'task': task, 'n_rows': n_rows, 'independent_units': units, 'split': split,
            'repeats': repeats, 'tuning': tuning, 'metrics': metrics, 'baselines': baselines,
            'model_comparison': 'Compare models on the same folds with tools/compare_models.py (paired, with --fold and --group).',
            'reasons': reasons, 'notes': notes, 'warnings': warnings}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Recommend validation scheme, metrics and baselines.')
    parser.add_argument('csv_file')
    parser.add_argument('--target', required=True)
    parser.add_argument('--group', help='column identifying repeated units (sample, compound, patient)')
    parser.add_argument('--time', help='column giving time order')
    parser.add_argument('--task', choices=['auto', 'regression', 'classification'], default='auto')
    args = parser.parse_args(argv)
    try:
        report = recommend(read(args.csv_file, (args.target, args.group, args.time)), args.target, args.group, args.time, args.task)
    except (OSError, ValueError) as error:
        print(json.dumps({'error': str(error)}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['warnings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
