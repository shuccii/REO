"""Blind grading: each run's output is scored against the fixed rubric by a fresh Claude process.

The grader sees the task inputs, the rubric items for that task and the output text, but not which plugin produced it.
"""
import concurrent.futures as cf
import json
import re
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parent
from run import configured_model, output_hashes
from runtime import digest
import argparse
import hashlib


def rubric_items(text):
    items, current = {}, None
    for line in text.splitlines():
        header = re.match(r'## (\w+)', line)
        if header:
            current = header.group(1)
            items[current] = []
        elif current and line.startswith('- '):
            items[current].append(line[2:])
    return items


def inputs_text(run_dir):
    root = run_dir / 'inputs'
    if not root.is_dir():
        raise ValueError('Cannot grade legacy run without retained inputs')
    parts = []
    for path in sorted(root.rglob('*')):
        if path.is_file():
            parts.append(f'--- {path.relative_to(root)} ---\n{path.read_text()}')
    return '\n\n'.join(parts)


def output_text(run_dir, task):
    text = (run_dir / 'final.md').read_text()
    if task == 'multi_hard':
        summary = run_dir / 'work' / 'review_summary.md'
        text += '\n\n=== review_summary.md ===\n' + (summary.read_text() if summary.exists() else '(file not created)')
    return text


def grade_payload_valid(run_dir):
    """Check active parsed scores against a separately retained generation hash."""
    try:
        metadata = json.loads((run_dir / 'grade-meta.json').read_text())
        return metadata.get('grade_sha256') == hashlib.sha256((run_dir / 'grade.json').read_bytes()).hexdigest()
    except (OSError, ValueError, TypeError):
        return False


def grade(run_dir, model=None):
    model = configured_model(model)
    meta = json.loads((run_dir / "meta.json").read_text())
    if not meta.get("completed"):
        return run_dir, {"error": "Run is incomplete", "scores": {}}
    task = run_dir.parent.name
    target = run_dir / 'grade.json'
    if output_hashes(run_dir) != meta.get('outputs'):
        raise ValueError('Run output hashes do not match retained provenance')
    rubric = (run_dir / 'rubric.md').read_text()
    if digest(run_dir / 'inputs') != meta.get('inputs'):
        raise ValueError('Retained input hashes do not match run provenance')
    if hashlib.sha256(rubric.encode()).hexdigest() != meta.get('rubric_sha256'):
        raise ValueError('Retained rubric hash does not match run provenance')
    items = '\n'.join(rubric_items(rubric)[task])
    prompt = f"""You are grading one AI-generated research review against a fixed rubric. Be strict and evidence-based.

TASK INPUTS:
{inputs_text(run_dir)}

RUBRIC ITEMS. Score defects 2 = identified with the correct mechanism (and correct numbers where relevant), 1 = vague, partial or wrong mechanism, 0 = missing. For decoy items (X...), score 1 if the output wrongly calls that correct practice an error/leak/flaw, otherwise 0 (falsely_flagged).
{items}

OUTPUT TO GRADE:
<<<
{output_text(run_dir, task)}
>>>

Also list incorrect_claims: statements in the output that are factually wrong about the inputs (not stylistic disagreements). Count only clear errors.
Reply with JSON only, no prose:
{{"scores": {{"<defect id>": {{"score": 0|1|2, "evidence": "<short quote or 'none'>"}}}}, "decoys": {{"<decoy id>": {{"falsely_flagged": 0|1, "evidence": "<short quote or 'none'>"}}}}, "incorrect_claims": ["..."], "extra_valid_findings": <integer count of additional valid, non-rubric findings>}}"""
    cli_version = subprocess.run(['claude', '--version'], text=True, capture_output=True, check=True).stdout.strip()
    provenance = {'run_identity': meta['identity'], 'model': model, 'cli_version': cli_version,
                  'grader_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                  'rubric_sha256': meta['rubric_sha256'], 'inputs': meta['inputs'],
                  'output_sha256': hashlib.sha256(output_text(run_dir, task).encode()).hexdigest()}
    if target.exists():
        previous = json.loads(target.read_text())
        if previous.get('_provenance') == provenance and 'error' not in previous and grade_payload_valid(run_dir):
            return run_dir, previous
        (run_dir / ('grade-' + hashlib.sha256(target.read_bytes()).hexdigest() + '.json')).write_bytes(target.read_bytes())
        grade_meta = run_dir / 'grade-meta.json'
        if grade_meta.exists():
            (run_dir / ('grade-meta-' + hashlib.sha256(target.read_bytes()).hexdigest() + '.json')).write_bytes(grade_meta.read_bytes())
            grade_meta.unlink()
        target.unlink()  # A failed replacement must never leave the stale grade active.
    (run_dir / 'grade-prompt.txt').write_text(prompt)
    data = None
    for attempt in range(1, 4):
        try:
            proc = subprocess.run(['claude', '-p', '--model', model, '--setting-sources', 'project',
                                   '--output-format', 'json', '--tools', ''],
                                  input=prompt, text=True, capture_output=True, cwd=run_dir, timeout=900)
            (run_dir / f'grade-stream-{attempt}.json').write_text(proc.stdout)
            (run_dir / f'grade-stderr-{attempt}.txt').write_text(proc.stderr)
            envelope = json.loads(proc.stdout)
            if proc.returncode or envelope.get('is_error'): continue
            result = envelope['result']
            data = json.loads(re.search(r'\{.*\}', result, re.S).group(0))
            expected = rubric_items(rubric)[task]
            defect_ids = {re.match(r'(\w+)', i).group(1) for i in expected if not i.startswith('X')}
            decoy_ids = {re.match(r'(\w+)', i).group(1) for i in expected if i.startswith('X')}
            if set(data['scores']) != defect_ids or set(data['decoys']) != decoy_ids:
                data = None; continue
            if any(v.get('score') not in (0, 1, 2) for v in data['scores'].values()):
                data = None; continue
            if any(v.get('falsely_flagged') not in (0, 1) for v in data['decoys'].values()):
                data = None; continue
            if not isinstance(data.get('incorrect_claims'), list):
                data = None; continue
            data['_usage'] = envelope.get('usage')
            data['_cost_usd'] = envelope.get('total_cost_usd')
            break
        except (json.JSONDecodeError, KeyError, AttributeError, TypeError, subprocess.TimeoutExpired) as exc:
            data = None
            (run_dir / f'grade-error-{attempt}.txt').write_text(str(exc))
    if data is None:
        return run_dir, {'scores': {}, 'decoys': {}, 'error': 'No valid complete rubric response after three attempts'}
    data['_provenance'] = provenance
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    (run_dir / 'grade-meta.json').write_text(json.dumps({'grade_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                                                     'provenance': provenance}, ensure_ascii=False, indent=2))
    return run_dir, data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model')
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    model = configured_model(args.model)
    runs = sorted(p for p in (BENCH / 'runs').glob('*/*') if (p / 'meta.json').exists())
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for run_dir, data in pool.map(lambda p: grade(p, model=model), runs):
            total = sum(v['score'] for v in data['scores'].values())
            print(run_dir.parent.name, run_dir.name, total, len(data.get('incorrect_claims', [])), data.get('error', ''), flush=True)
