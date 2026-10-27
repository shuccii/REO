"""Blind grading: each run's output is scored against the fixed rubric by a fresh Claude process.

The grader sees the task inputs, the rubric items for that task and the output text, but not which plugin produced it.
"""
import concurrent.futures as cf
import json
import re
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ITEMS = {}
current = None
for line in (BENCH / 'RUBRIC.md').read_text().splitlines():
    header = re.match(r'## (\w+)', line)
    if header:
        current = header.group(1)
        ITEMS[current] = []
    elif current and line.startswith('- '):
        ITEMS[current].append(line[2:])


def inputs_text(task):
    parts = []
    for path in sorted((BENCH / 'inputs' / task).rglob('*')):
        if path.is_file() and path.suffix in ('.md', '.py') and path.name != 'README_GRADER.md':
            parts.append(f'--- {path.relative_to(BENCH / "inputs" / task)} ---\n{path.read_text()}')
    if task == 'audit_hard':
        parts.append('--- data.csv (facts for the grader) ---\n440 rows, 400 unique (40 exact duplicates of Lab A rows). 100 films x 4 replicates. '
                     'Lab B temperatures are in kelvin (about 293-353), Lab A in Celsius. Running analysis.py prints: n_rows=440 folds=5 k_chosen=[1, 1, 1, 1, 1] / '
                     'R2 = 0.947 +/- 0.002 / corr(temperature, conductivity) = -0.025. After converting to Celsius and removing duplicates, r = +0.309; '
                     'film-grouped 5-fold CV of kNN (k=9) gives R2 = -0.68.')
    return '\n\n'.join(parts)


def output_text(run_dir, task):
    text = (run_dir / 'final.md').read_text()
    if task == 'multi_hard':
        summary = run_dir / 'work' / 'review_summary.md'
        text += '\n\n=== review_summary.md ===\n' + (summary.read_text() if summary.exists() else '(file not created)')
    return text


def grade(run_dir):
    task = run_dir.parent.name
    target = run_dir / 'grade.json'
    if target.exists():
        return run_dir, json.loads(target.read_text())
    items = '\n'.join(ITEMS[task])
    prompt = f"""You are grading one AI-generated research review against a fixed rubric. Be strict and evidence-based.

TASK INPUTS:
{inputs_text(task)}

RUBRIC ITEMS. Score defects 2 = identified with the correct mechanism (and correct numbers where relevant), 1 = vague, partial or wrong mechanism, 0 = missing. For decoy items (X...), score 1 if the output wrongly calls that correct practice an error/leak/flaw, otherwise 0 (falsely_flagged).
{items}

OUTPUT TO GRADE:
<<<
{output_text(run_dir, task)}
>>>

Also list incorrect_claims: statements in the output that are factually wrong about the inputs (not stylistic disagreements). Count only clear errors.
Reply with JSON only, no prose:
{{"scores": {{"<defect id>": {{"score": 0|1|2, "evidence": "<short quote or 'none'>"}}}}, "decoys": {{"<decoy id>": {{"falsely_flagged": 0|1, "evidence": "<short quote or 'none'>"}}}}, "incorrect_claims": ["..."], "extra_valid_findings": <integer count of additional valid, non-rubric findings>}}"""
    data = None
    for _ in range(3):
        proc = subprocess.run(['claude', '-p', '--setting-sources', 'project', '--output-format', 'json'],
                              input=prompt, text=True, capture_output=True, cwd=BENCH, timeout=900)
        try:
            result = json.loads(proc.stdout)['result']
            data = json.loads(re.search(r'\{.*\}', result, re.S).group(0))
            break
        except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
            continue
    if data is None:
        return run_dir, {'scores': {}, 'decoys': {}, 'error': (proc.stdout or proc.stderr)[:300]}
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return run_dir, data


if __name__ == '__main__':
    runs = sorted(p for p in (BENCH / 'runs').glob('*/*') if (p / 'meta.json').exists())
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        for run_dir, data in pool.map(grade, runs):
            total = sum(v['score'] for v in data['scores'].values()); data.setdefault('decoys', {})
            print(run_dir.parent.name, run_dir.name, total, len(data.get('incorrect_claims', [])), flush=True)
