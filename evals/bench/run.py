"""Run each (task, arm, rep) as a fresh headless Claude Code process and record the result."""
import concurrent.futures as cf
import hashlib
import os
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
PLUGINS = {
    'reo': str(BENCH.parents[1]),
    'mi': os.environ.get('COMPARE_PLUGIN'),
    'base': None,
    'reo-cmd': str(BENCH.parents[1]),
    'mi-cmd': os.environ.get('COMPARE_PLUGIN'),
}
PAPER = ('manuscript.md は投稿前の研究論文の原稿です。査読者の立場で、主張と根拠の対応、方法の妥当性、数値の整合性、代替の説明を点検してください。'
         '日本語で、重大な指摘から順に、修正案と、修正できたと判断する条件も書いてください。')
PROMPTS = {
    'paper_mat': PAPER,
    'paper_bio': PAPER,
    'audit_hard': ('このフォルダの解析(README.md, data.csv, analysis.py, report.md)を監査してください。報告書の主張が、コードとデータで裏づけられているかを確かめ、'
                   '問題を重大な順に日本語で報告してください。ファイルは変更しないでください。'),
    'multi_hard': ('papers/ にある6つの原稿を、それぞれ査読者の立場で点検してください。原稿ごとの主な指摘、6本を比べる表、重大さによる優先順位をまとめ、'
                   'review_summary.md に日本語で保存してください。'),
}
COMMANDS = {
    ('reo-cmd', 'audit_hard'): '/reo:research-review-workflow ',
    ('reo-cmd', 'multi_hard'): '/reo:orchestrate-work ',
    ('mi-cmd', 'audit_hard'): '/mi-orchestrator:mi-audit ',
    ('mi-cmd', 'multi_hard'): '/mi-orchestrator:mi-orchestrate ',
}
TOOLS = 'Read,Glob,Grep,Skill,Agent,Task,Write,Edit,Bash(python3:*)'


def digest(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file()}


def run(task, arm, rep):
    out = BENCH / 'runs' / task / f'{arm}-{rep}'
    if (out / 'meta.json').exists():
        return task, arm, rep, 'skipped'
    work = out / 'work'
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(BENCH / 'inputs' / task, work)
    before = digest(work)
    cmd = ['claude', '-p', '--setting-sources', 'project', '--allowedTools', TOOLS,
           '--output-format', 'stream-json', '--verbose']
    if PLUGINS[arm]:
        cmd += ['--plugin-dir', PLUGINS[arm]]
    start = time.time()
    with open(out / 'stream.jsonl', 'w') as stream, open(out / 'stderr.txt', 'w') as err:
        proc = subprocess.run(cmd, input=COMMANDS.get((arm, task), '') + PROMPTS[task], text=True, cwd=work, stdout=stream, stderr=err, timeout=1800)
    elapsed = time.time() - start
    final, cost, turns, tools, model, plugins = '', None, None, [], None, []
    for line in (out / 'stream.jsonl').read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            model = event.get('model')
            plugins = [p['name'] for p in event.get('plugins', []) if p.get('path') != 'builtin']
        if event.get('type') == 'assistant':
            for item in event['message'].get('content', []):
                if item.get('type') == 'tool_use':
                    tools.append({'name': item['name'], 'input': json.dumps(item['input'], ensure_ascii=False)[:160]})
        if event.get('type') == 'result':
            final, cost, turns = event.get('result') or '', event.get('total_cost_usd'), event.get('num_turns')
    after = {k: v for k, v in digest(work).items()}
    modified = sorted(k for k in before if after.get(k) != before[k])
    (out / 'final.md').write_text(final)
    meta = {'task': task, 'arm': arm, 'rep': rep, 'exit': proc.returncode, 'seconds': round(elapsed, 1), 'cost_usd': cost,
            'turns': turns, 'model': model, 'plugins': plugins, 'tool_calls': len(tools),
            'subagent_calls': sum(t['name'] in ('Agent', 'Task') for t in tools),
            'skills': [t['input'] for t in tools if t['name'] == 'Skill'],
            'subagents': [t['input'] for t in tools if t['name'] in ('Agent', 'Task')],
            'inputs_modified': modified, 'new_files': sorted(set(after) - set(before))}
    (out / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    return task, arm, rep, f"exit={proc.returncode} {meta['seconds']}s ${cost}"


if __name__ == '__main__':
    tasks = sys.argv[1].split(',')
    reps = int(sys.argv[2])
    arms = sys.argv[4].split(',') if len(sys.argv) > 4 else ['reo', 'mi', 'base']
    jobs = [(t, a, r) for r in range(1, reps + 1) for t in tasks for a in arms]
    with cf.ThreadPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for result in pool.map(lambda job: run(*job), jobs):
            print(*result, flush=True)
