"""Offline experiment matrices and descriptive one-factor comparisons. No LLM calls."""
import argparse
import copy
import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

METRICS = ('seconds', 'cost_usd', 'llm_calls', 'tokens')
CONDITIONS = ('model', 'input_hash', 'settings_hash', 'grader_hash')


def count(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(label + ' must be a positive integer')
    return value


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be a nonempty string')
    return value


def factors(value):
    if not isinstance(value, dict) or not value:
        raise ValueError('nonempty factors object required')
    for k, v in value.items():
        text(k, 'factor name')
        text(v, 'factor value')
    return value


def matrix(spec):
    if not isinstance(spec, dict):
        raise ValueError('study specification must be an object')
    fixed = {k: text(spec.get(k), k) for k in ('model', 'settings_hash', 'grader_hash')}
    reps = count(spec.get('repetitions', 3), 'repetitions')
    cap = count(spec.get('max_runs'), 'max_runs')
    arms, tasks = spec.get('arms'), spec.get('tasks')
    if not isinstance(arms, dict) or len(arms) < 2:
        raise ValueError('at least two named arms required')
    for arm, value in arms.items():
        text(arm, 'arm')
        factors(value)
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('nonempty tasks required')
    seen = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError('task must be an object')
        key = text(task.get('id'), 'task ID')
        text(task.get('input_hash'), 'input_hash')
        if key in seen:
            raise ValueError('duplicate task ID')
        seen.add(key)
    if len(arms) * len(tasks) * reps > cap:
        raise ValueError('matrix exceeds max_runs; narrow the study before execution')
    # Repetition-major interleaving reduces fixed arm-order effects. No concurrency.
    jobs = []
    for rep in range(1, reps + 1):
        order = sorted(arms)
        order = order[(rep - 1) % len(order):] + order[:(rep - 1) % len(order)]
        for task in tasks:
            for arm in order:
                jobs.append({'task': task['id'], 'rep': rep, 'arm': arm,
                             'conditions': dict(fixed, input_hash=task['input_hash']),
                             'factors': copy.deepcopy(arms[arm])})
    return jobs


def summary(values):
    observed = [v for v in values if v is not None]
    return {'observed': len(observed), 'missing': len(values) - len(observed),
            'mean': statistics.mean(observed) if observed else None,
            'median': statistics.median(observed) if observed else None,
            'total': sum(observed) if len(observed) == len(values) and observed else None}


def compare(rows, factor):
    text(factor, 'contrast factor')
    if not isinstance(rows, list):
        raise ValueError('observations must be a list')
    attempts, logical = set(), defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('observation must be an object')
        for key in ('task', 'arm'):
            text(row.get(key), key)
        count(row.get('rep'), 'rep')
        count(row.get('attempt'), 'attempt')
        key = (row['task'], row['rep'], row['arm'])
        attempt_key = key + (row['attempt'],)
        if attempt_key in attempts:
            raise ValueError('duplicate task/rep/arm/attempt observation')
        attempts.add(attempt_key)
        conditions = row.get('conditions')
        if not isinstance(conditions, dict) or set(conditions) != set(CONDITIONS):
            raise ValueError('exact frozen model/input/settings/grader conditions required')
        for name in CONDITIONS:
            text(conditions[name], name)
        factors(row.get('factors'))
        if not isinstance(row.get('completed'), bool):
            raise ValueError('completed must be boolean')
        for name in ('success', 'false_completion'):
            if row.get(name) is not None and not isinstance(row[name], bool):
                raise ValueError(name + ' must be boolean or null')
        if row.get('success') is True and not row['completed']:
            raise ValueError('an incomplete attempt cannot be successful')
        for name in METRICS:
            value = row.get(name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                      or not math.isfinite(value) or value < 0):
                raise ValueError('invalid ' + name)
            if name == 'llm_calls' and value is not None and int(value) != value:
                raise ValueError('llm_calls must be a whole count')
        logical[key].append(row)
    runs = {}
    for key, group in logical.items():
        group = sorted(group, key=lambda r: r['attempt'])
        last = group[-1]
        if any(r['conditions'] != last['conditions'] or r['factors'] != last['factors'] for r in group):
            raise ValueError('retry conditions changed; use a different run identity')
        runs[key] = dict(last, **{m: summary([r.get(m) for r in group])['total'] for m in METRICS})
    arms = {}
    for arm in sorted({r['arm'] for r in rows}):
        group = [r for r in rows if r['arm'] == arm]
        finals = [r for k, r in runs.items() if k[2] == arm]
        arms[arm] = {'attempts': len(group), 'runs': len(finals),
                     'completed': sum(r['completed'] for r in finals),
                     **{m: summary([r.get(m) for r in group]) for m in METRICS},
                     **{m: summary([r.get(m) for r in finals]) for m in ('success', 'false_completion')}}
    contrasts = {}
    for left, right in itertools.combinations(sorted(arms), 2):
        a = {(k[0], k[1]): r for k, r in runs.items() if k[2] == left}
        b = {(k[0], k[1]): r for k, r in runs.items() if k[2] == right}
        pairs = []
        keys = a.keys() & b.keys()
        for key in sorted(keys):
            x, y = a[key], b[key]
            xf, yf = x['factors'], y['factors']
            if (x['conditions'] == y['conditions'] and set(xf) == set(yf)
                    and factor in xf and xf[factor] != yf[factor]
                    and all(xf[k] == yf[k] for k in xf if k != factor)):
                pairs.append((x, y))
        deltas = {}
        observed = {}
        for metric in METRICS + ('success', 'false_completion'):
            values = [y[metric] - x[metric] for x, y in pairs
                      if x.get(metric) is not None and y.get(metric) is not None]
            deltas[metric] = statistics.mean(values) if values else None
            observed[metric] = len(values)
        contrasts[f'{right}_vs_{left}'] = {'paired_runs': len(pairs),
            'excluded_incompatible_pairs': len(keys) - len(pairs),
            'unmatched_runs': len(a.keys() ^ b.keys()),
            'delta_mean': deltas, 'observed_pairs': observed}
    return {'arms': arms, 'contrasts': contrasts, 'factor': factor,
            'limitations': 'Offline descriptive evidence only; host-supplied observations are not authenticated. '
            'Failed attempts count in resource totals. Unknown totals remain null. '
            'Matched repetition IDs are not common random seeds. Small samples do not establish noninferiority.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'compare'))
    parser.add_argument('input', type=Path)
    parser.add_argument('--factor')
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text())
        result = ({'dry_run': True, 'workers': 1, 'jobs': matrix(payload)} if args.operation == 'plan'
                  else compare(payload, args.factor))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
