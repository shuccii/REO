"""Bounded, explicit local stage execution. Commands are trusted, not sandboxed."""
import hashlib
import json
import math
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from review_state import canonical

METRICS = ('seconds', 'llm_calls', 'tokens', 'cost_usd')
KINDS = ('mechanical', 'implementation', 'research', 'experiment', 'review', 'consistency')
RISKY = ('implementation', 'research', 'experiment')


def number(value, label, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0 or (positive and value == 0)):
        raise ValueError(label + ' must be a finite nonnegative number')
    if label == 'llm_calls' and int(value) != value:
        raise ValueError('llm_calls must be a whole count')
    return value


def local(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError('paths must be workspace-relative')
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError('path escapes workspace')
    return path


def aliases(left, right):
    """Reject lexical collisions, parent/file collisions and existing hard links."""
    if left == right or left in right.parents or right in left.parents:
        return True
    return left.exists() and right.exists() and left.samefile(right)


def hashes(root, names):
    result = {}
    for name in names:
        path = local(root, name)
        if not path.is_file():
            raise ValueError('missing artifact: ' + name)
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=path.parent, encoding='utf-8', delete=False) as f:
            name = f.name
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()


def journal(path, state):
    state.pop('checkpoint_hash', None)
    state['checkpoint_hash'] = canonical(state)
    atomic(path, state)


def read_checkpoint(path, root):
    state = json.loads(path.read_text())
    if not isinstance(state, dict):
        raise ValueError('invalid checkpoint object')
    checksum = state.pop('checkpoint_hash', None)
    if checksum != canonical(state):
        raise ValueError('checkpoint checksum mismatch')
    if state.get('schema_version') != 1 or state.get('workspace') != str(root):
        raise ValueError('checkpoint schema/workspace mismatch')
    attempts = state.get('attempts')
    if not isinstance(attempts, list):
        raise ValueError('invalid checkpoint attempts')
    for attempt in attempts:
        if (not isinstance(attempt, dict) or attempt.get('status') not in ('running', 'passed', 'failed')
                or not isinstance(attempt.get('stage'), str)
                or not isinstance(attempt.get('fingerprint'), str)
                or not isinstance(attempt.get('usage'), dict)
                or not isinstance(attempt.get('outputs'), dict)):
            raise ValueError('invalid checkpoint attempt')
        for metric, value in attempt['usage'].items():
            if metric not in METRICS:
                raise ValueError('invalid checkpoint usage metric')
            if value is not None:
                number(value, metric)
        if attempt['status'] != 'running' and attempt['usage'].get('seconds') is None:
            raise ValueError('checkpoint missing observed duration')
        for name, sha in attempt['outputs'].items():
            local(root, name)
            if not isinstance(sha, str) or len(sha) != 64:
                raise ValueError('invalid checkpoint artifact hash')
    return state


def fingerprint(stage, plan, root, dependencies):
    source = Path(__file__).read_bytes() + Path(__file__).with_name('review_state.py').read_bytes()
    return canonical({'stage': stage, 'context': plan['context'],
                      'engine': hashlib.sha256(source).hexdigest(),
                      'inputs': hashes(root, stage.get('inputs', plan.get('inputs', []))),
                      'dependencies': dependencies})


def validate(plan, root, checkpoint, protected=()):
    if not isinstance(plan, dict) or not isinstance(plan.get('context'), dict):
        raise ValueError('plan requires a context object')
    canonical(plan)
    inputs = plan.get('inputs', [])
    if not isinstance(inputs, list) or not all(isinstance(x, str) for x in inputs):
        raise ValueError('inputs must be a list of paths')
    if not isinstance(plan.get('limits'), dict) or 'seconds' not in plan['limits']:
        raise ValueError('a wall-time limit in seconds is required')
    for metric, limit in plan['limits'].items():
        if metric not in METRICS:
            raise ValueError('unknown budget metric: ' + metric)
        number(limit, metric, positive=metric == 'seconds')
    stages = plan.get('stages')
    if not isinstance(stages, list) or not stages:
        raise ValueError('nonempty stages required')
    if not checkpoint.is_relative_to(root):
        raise ValueError('checkpoint must remain inside workspace')
    blocked_paths = {local(root, x) for x in inputs} | {Path(x).resolve() for x in protected}
    if any(aliases(checkpoint, path) for path in blocked_paths):
        raise ValueError('checkpoint cannot overwrite an input')
    blocked_paths.add(checkpoint)
    lock_path = local(root, str(checkpoint.relative_to(root)) + '.lock')
    if any(aliases(lock_path, path) for path in blocked_paths):
        raise ValueError('checkpoint lock cannot overwrite an input')
    blocked_paths.add(lock_path)
    seen, ancestors, output_paths = {}, {}, set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise ValueError('stage must be an object')
        key, kind = stage.get('id'), stage.get('kind')
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('unique nonempty stage IDs required')
        if kind not in KINDS:
            raise ValueError('unknown stage kind')
        if not isinstance(stage.get('actor'), str) or not stage['actor'].strip():
            raise ValueError('host-declared actor identity required')
        deps = stage.get('depends_on', [])
        if (not isinstance(deps, list) or not all(isinstance(d, str) for d in deps)
                or len(deps) != len(set(deps)) or any(d not in seen for d in deps)):
            raise ValueError('dependencies must name earlier unique stages')
        ancestors[key] = set(deps)
        for dep in deps:
            ancestors[key] |= ancestors[dep]
        command = stage.get('command')
        if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
            raise ValueError('command must be a nonempty argv list')
        number(stage.get('timeout'), 'timeout', positive=True)
        estimate = stage.get('estimate', {})
        if not isinstance(estimate, dict):
            raise ValueError('estimate must be an object')
        for metric, value in estimate.items():
            if metric not in METRICS:
                raise ValueError('unknown estimate metric')
            number(value, metric)
        names = stage.get('inputs', inputs)
        if not isinstance(names, list) or any(name not in inputs for name in names):
            raise ValueError('stage inputs must be declared global inputs')
        outputs = stage.get('outputs')
        if not isinstance(outputs, list) or not outputs:
            raise ValueError('each stage needs retained output artifacts')
        paths = [local(root, x) for x in outputs]
        if any(x.exists() and not x.is_file() for x in paths):
            raise ValueError('output must be a file')
        if (any(aliases(x, other) for i, x in enumerate(paths) for other in paths[:i])
                or any(aliases(x, other) for x in paths for other in blocked_paths | output_paths)):
            raise ValueError('outputs cannot overwrite inputs, checkpoint or another stage')
        output_paths.update(paths)
        if kind == 'review':
            workers = {seen[d]['actor'] for d in ancestors[key] if seen[d]['kind'] != 'review'}
            if stage['actor'] in workers:
                raise ValueError('review requires an independent host-declared actor')
        seen[key] = stage
    hashes(root, inputs)
    return seen, ancestors


def usage_total(attempts):
    return {metric: (sum(a['usage'][metric] for a in attempts)
                     if all(a.get('usage', {}).get(metric) is not None for a in attempts) else None)
            for metric in METRICS}


def admission(limits, used, pending):
    for metric, limit in limits.items():
        value = used[metric]
        if value is None:
            return 'budget_unobservable'
        if value > limit:
            return 'budget_exceeded'
        estimates = [s.get('estimate', {}).get(metric) if metric != 'seconds' else s['timeout'] for s in pending]
        if any(v is None for v in estimates):
            return 'budget_unobservable'
        if value + sum(estimates) > limit:
            return 'budget_insufficient'
    return None


def invoke(stage, root, request, timeout):
    """File-backed output avoids pipe deadlocks and unbounded in-memory capture."""
    started = time.monotonic()
    receipt, reason, code = {}, None, None
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = None
        try:
            proc = subprocess.Popen(stage['command'], cwd=root, stdin=subprocess.PIPE,
                                    stdout=out, stderr=err, start_new_session=True)
            proc.communicate(json.dumps(request, allow_nan=False).encode(), timeout=timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            reason = 'timeout'
        except OSError:
            reason = 'launch_failed'
        finally:
            if proc is not None:
                # Clean up descendants even if their original parent exited normally.
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
        out.seek(0)
        raw = out.read(1024 * 1024 + 1)
        try:
            if len(raw) > 1024 * 1024:
                raise ValueError('receipt exceeds 1 MiB')
            receipt = json.loads(raw)
            if not isinstance(receipt, dict):
                raise ValueError('receipt must be an object')
            observed = receipt.get('usage', {})
            if not isinstance(observed, dict):
                raise ValueError('usage must be an object')
            for metric in METRICS[1:]:
                if observed.get(metric) is not None:
                    number(observed[metric], metric)
        except (ValueError, UnicodeError, TypeError):
            receipt, reason = {}, reason or 'invalid_receipt'
        err.seek(0, 2)
        size = err.tell()
        err.seek(max(0, size - 4000))
        stderr = err.read().decode(errors='replace')
    observed = {k: receipt.get('usage', {}).get(k) for k in METRICS[1:]}
    observed['seconds'] = time.monotonic() - started
    if reason is None and (code != 0 or receipt.get('status') != 'passed'):
        reason = 'stage_failed'
    return {'status': 'failed' if reason else 'passed', 'reason': reason, 'exit': code,
            'usage': observed, 'receipt': receipt, 'stderr_tail': stderr}


def execute(plan, workspace, checkpoint, resume=False, protected=()):
    """One writer per checkpoint; local commands require POSIX process groups."""
    if os.name != 'posix':
        raise ValueError('bounded execution requires POSIX process-group support')
    import fcntl
    root, checkpoint = Path(workspace).resolve(), Path(checkpoint).resolve()
    validate(plan, root, checkpoint, protected)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    # Keep the lock inode in place. Unlinking it would allow two lock owners.
    with Path(str(checkpoint) + '.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('checkpoint is in use by another executor') from exc
        return _execute(plan, root, checkpoint, resume, protected)


def _execute(plan, workspace, checkpoint, resume=False, protected=()):
    root, checkpoint = Path(workspace).resolve(), Path(checkpoint).resolve()
    stages, ancestors = validate(plan, root, checkpoint, protected)
    if checkpoint.exists() and not resume:
        raise ValueError('checkpoint exists; use a new path or verified --resume')
    state = (read_checkpoint(checkpoint, root) if resume else
             {'schema_version': 1, 'workspace': str(root), 'attempts': []})
    state['reused'] = []
    state['plan_hash'] = canonical(plan)

    def finish(reason=None):
        state.update(status='blocked' if reason else 'completed', reason=reason,
                     usage=usage_total(state['attempts']), scientific_validity_assessed=False)
        journal(checkpoint, state)
        return state

    if any(a['status'] == 'running' for a in state['attempts']):
        return finish('interrupted_usage_unknown')

    experiments = [s for s in stages.values() if s['kind'] == 'experiment']
    cap = plan.get('max_experiments', 0)
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 0:
        raise ValueError('max_experiments must be a nonnegative integer')
    if experiments and (plan.get('allow_experiments') is not True or len(experiments) > cap):
        return finish('experiments_not_authorized')
    risky = {k for k, s in stages.items() if s['kind'] in RISKY}
    reviewed = {d for k, s in stages.items() if s['kind'] == 'review' for d in ancestors[k]}
    if risky - reviewed:
        return finish('review_required')
    if risky:
        last = next(reversed(stages))
        if stages[last]['kind'] != 'consistency' or ancestors[last] != set(stages) - {last}:
            return finish('consistency_required')
    retry_limit = plan.get('retry_limit', 0)
    if isinstance(retry_limit, bool) or not isinstance(retry_limit, int) or not 0 <= retry_limit <= 2:
        raise ValueError('retry_limit must be 0, 1 or 2')
    # Plan conservative reuse before budget admission. A rerun ancestor invalidates
    # descendants even when it later reproduces identical bytes.
    reusable = {}
    for key, stage in stages.items():
        if stage['kind'] != 'mechanical' or not ancestors[key] <= reusable.keys():
            continue
        dependencies = {d: {'fingerprint': reusable[d]['fingerprint'],
                            'outputs': reusable[d]['outputs']} for d in sorted(ancestors[key])}
        stamp = fingerprint(stage, plan, root, dependencies)
        latest = next((a for a in reversed(state['attempts']) if a['stage'] == key), None)
        if latest and latest['status'] == 'passed' and latest['fingerprint'] == stamp:
            try:
                if hashes(root, stage['outputs']) == latest['outputs']:
                    reusable[key] = latest
            except (OSError, ValueError):
                pass
    completed = {}
    ordered = list(stages.values())
    for index, stage in enumerate(ordered):
        if stage['id'] in reusable:
            try:
                still_valid = hashes(root, stage['outputs']) == reusable[stage['id']]['outputs']
            except (OSError, ValueError):
                still_valid = False
            if still_valid:
                completed[stage['id']] = reusable[stage['id']]
                state['reused'].append(stage['id'])
                continue
            invalid = {stage['id']} | {key for key in reusable if stage['id'] in ancestors[key]}
            for key in invalid:
                reusable.pop(key, None)
        pending = [s for s in ordered[index:] if s['id'] not in reusable]
        reason = admission(plan['limits'], usage_total(state['attempts']), pending)
        if reason:
            return finish(reason)
        if stage['kind'] == 'experiment' and sum(a.get('kind') == 'experiment' for a in state['attempts']) >= cap:
            return finish('experiment_limit_reached')
        dep_identity = {d: {'fingerprint': completed[d]['fingerprint'],
                            'outputs': completed[d]['outputs']} for d in sorted(ancestors[stage['id']])}
        stamp = fingerprint(stage, plan, root, dep_identity)
        failures = sum(a['fingerprint'] == stamp and a['status'] == 'failed' for a in state['attempts'])
        if failures > retry_limit:
            return finish('retry_limit_reached')
        dependencies = {path: sha for d in ancestors[stage['id']]
                        for path, sha in completed[d]['outputs'].items()}
        before = hashes(root, plan.get('inputs', []))
        retained = {path: sha for evidence in completed.values() for path, sha in evidence['outputs'].items()}
        attempt = {'stage': stage['id'], 'kind': stage['kind'], 'fingerprint': stamp,
                   'status': 'running', 'usage': {}, 'inputs': before,
                   'outputs': {}, 'actor': stage['actor']}
        state['attempts'].append(attempt)
        journal(checkpoint, state)  # Journal before launch, including interrupted attempts.
        request = {'stage': stage['id'], 'context': plan['context'],
                   'dependency_outputs': dependencies, 'inputs': before}
        remaining = plan['limits']['seconds'] - usage_total(state['attempts'][:-1])['seconds']
        attempt.update(invoke(stage, root, request, min(stage['timeout'], remaining)))
        try:
            if before != hashes(root, plan.get('inputs', [])):
                raise ValueError('input modified')
            if dependencies != hashes(root, dependencies):
                raise ValueError('dependency modified')
            if retained != hashes(root, retained):
                raise ValueError('retained evidence modified')
            attempt['outputs'] = hashes(root, stage['outputs'])
        except (ValueError, OSError):
            attempt.update(status='failed', reason=attempt['reason'] or 'artifact_invalid')
        if attempt['status'] == 'passed' and stage['kind'] == 'review':
            review = attempt['receipt'].get('review', {})
            if (not isinstance(review, dict) or review.get('actor') != stage['actor']
                    or review.get('decision') != 'passed' or review.get('reviewed') != dependencies):
                attempt.update(status='failed', reason='review_evidence_invalid')
        journal(checkpoint, state)
        if attempt['status'] != 'passed':
            return finish(attempt['reason'])
        reason = admission(plan['limits'], usage_total(state['attempts']), [])
        if reason:
            return finish(reason)
        completed[stage['id']] = attempt
    reason = admission(plan['limits'], usage_total(state['attempts']), [])
    if reason:
        return finish(reason)
    return finish()
