"""Aggregate observed benchmark evidence. No model calls; missing values stay null."""
import argparse
import hashlib
from runtime import digest
from run import output_hashes
from grade import output_text, grade_payload_valid
import itertools
import json
import statistics
from pathlib import Path

BENCH = Path(__file__).resolve().parent
MEASURES = ('seconds', 'cost_usd', 'input_tokens', 'output_tokens', 'cache_read_input_tokens',
            'cache_creation_input_tokens', 'reasoning_tokens', 'tool_calls', 'subagent_calls',
            'quality_score', 'defect_recall', 'decoy_false_positives', 'incorrect_claims_count')


def summarize(values):
    values = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return {'observed': len(values), 'mean': statistics.mean(values) if values else None,
            'median': statistics.median(values) if values else None,
            'total': sum(values) if values else None}


def quality(row):
    g = row.get('grade')
    if not row.get('completed') or not g or g.get('error') or not g.get('scores'):
        return {}
    scores = [v['score'] for v in g['scores'].values()]
    return {'quality_score': sum(scores), 'defect_recall': sum(v > 0 for v in scores) / len(scores),
            'decoy_false_positives': sum(v['falsely_flagged'] for v in g.get('decoys', {}).values()),
            'incorrect_claims_count': len(g.get('incorrect_claims', []))}


def aggregate(rows):
    rows = [{**r, **quality(r)} for r in rows]
    arms = {}
    for arm in sorted({r['arm'] for r in rows}):
        group = [r for r in rows if r['arm'] == arm]
        arms[arm] = {'runs': len(group), 'completed': sum(bool(r.get('completed')) for r in group),
                     'graded': sum('quality_score' in r for r in group),
                     **{m: summarize([r.get(m) for r in group]) for m in MEASURES}}
    paired = {}
    for left, right in itertools.combinations(sorted(arms), 2):
        a = {(r['task'], r['rep']): r for r in rows if r['arm'] == left and r.get('completed')}
        b = {(r['task'], r['rep']): r for r in rows if r['arm'] == right and r.get('completed')}
        candidates = [(a[k], b[k]) for k in sorted(a.keys() & b.keys())]
        keys = ('requested_model', 'model', 'inputs', 'config', 'rubric_sha256')
        judge_keys = ('model', 'cli_version', 'grader_source_sha256')
        pairs = [(x, y) for x, y in candidates
                 if all(x.get(k) is not None and x.get(k) == y.get(k) for k in keys)
                 and all((x.get('grade', {}).get('_provenance') or {}).get(k) is not None
                         and (x.get('grade', {}).get('_provenance') or {}).get(k)
                         == (y.get('grade', {}).get('_provenance') or {}).get(k) for k in judge_keys)]
        deltas = [y['quality_score'] - x['quality_score'] for x, y in pairs
                  if 'quality_score' in x and 'quality_score' in y]
        paired[f'{right}_vs_{left}'] = {'paired_runs': len(pairs), 'graded_pairs': len(deltas),
                                       'excluded_incompatible_pairs': len(candidates) - len(pairs),
                                       'quality_score_delta_mean': statistics.mean(deltas) if deltas else None,
                                       'quality_wins': sum(v > 0 for v in deltas),
                                       'quality_ties': sum(v == 0 for v in deltas)}
    return {'arms': arms, 'paired': paired,
            'limitations': 'Descriptive observations only. Missing metrics are null. Quality is model graded; paired deltas match task and repetition, not shared random seeds. Unnormalized scores across tasks differ in rubric size.'}


def grade_matches(run_dir, meta, grade):
    """Verify retained evidence before admitting quality into any report."""
    provenance = grade.get('_provenance') or {}
    try:
        inputs = digest(run_dir / 'inputs')
        rubric = hashlib.sha256((run_dir / 'rubric.md').read_bytes()).hexdigest()
        prompt = hashlib.sha256((run_dir / 'grade-prompt.txt').read_bytes()).hexdigest()
        output = hashlib.sha256(output_text(run_dir, meta['task']).encode()).hexdigest()
        return bool(meta.get('completed') and not grade.get('error') and meta.get('identity')
                    and grade_payload_valid(run_dir)
                    and provenance.get('run_identity') == meta['identity']
                    and provenance.get('model') and provenance.get('cli_version')
                    and inputs == meta.get('inputs') == provenance.get('inputs')
                    and rubric == meta.get('rubric_sha256') == provenance.get('rubric_sha256')
                    and output_hashes(run_dir) == meta.get('outputs')
                    and output == provenance.get('output_sha256')
                    and prompt == provenance.get('prompt_sha256'))
    except (OSError, KeyError, TypeError):
        return False


def load_rows(root):
    rows = []
    for p in sorted(root.glob('*/*/meta.json')):
        row = json.loads(p.read_text())
        grade_path = p.parent / 'grade.json'
        if grade_path.exists():
            g = json.loads(grade_path.read_text())
            # Legacy/unmatched grades cannot substantiate this run's quality.
            if grade_matches(p.parent, row, g):
                row['grade'] = g
        rows.append(row)
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, default=BENCH / 'runs')
    parser.add_argument('--output', type=Path, default=BENCH / 'report.json')
    args = parser.parse_args()
    args.output.write_text(json.dumps(aggregate(load_rows(args.runs)), ensure_ascii=False, indent=2))
    print(args.output)
