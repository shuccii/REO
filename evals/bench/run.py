"""Run each (task, arm, rep) as a fresh headless Claude Code process and record the result."""
import argparse
import datetime
import uuid
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
    'format-only': str(BENCH / 'format_plugin'),
    'current': os.environ.get('BENCH_CURRENT_PLUGIN'),
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
PROMPTS.update({
    'clean_short': PAPER,
    'insufficient': PAPER,
    'partial_pairing': PAPER + ' data.csvも確認してください。検定前に対応関係を確認してください。',
    'cross_chapter': PAPER + ' 要旨・方法・結果・結論の整合を確認してください。',
    'defense': 'manuscript.mdを読み、本番想定の模擬質疑を始めてください。一問だけ質問し、私の回答を待ってください。回答例やフィードバックはまだ出さないでください。',
})
COMMANDS = {
    ('reo-cmd', 'audit_hard'): '/reo:research-review-workflow ',
    ('reo-cmd', 'multi_hard'): '/reo:orchestrate-work ',
    ('mi-cmd', 'audit_hard'): '/mi-orchestrator:mi-audit ',
    ('mi-cmd', 'multi_hard'): '/mi-orchestrator:mi-orchestrate ',
}
TOOLS = 'Read,Glob,Grep,Skill,Agent,Task,Write,Edit,Bash(python3:*)'


from runtime import digest, identity, reusable, usage


def configured_model(model=None):
    model = model or os.environ.get('BENCH_MODEL')
    if not model:
        raise ValueError('Pass --model or set BENCH_MODEL to a fixed model identifier')
    return model


def plugin_source(path):
    if path is None:
        return None
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError(f'Plugin directory does not exist: {root}')
    # Only intended plugin sources; never traverse arbitrary private/cache folders.
    roots = ('.claude-plugin', '.codex-plugin', 'skills', 'tools', 'scripts', 'assets', 'requirements',
             'commands', 'agents', 'hooks', 'docs', 'references', 'outputStyles')
    excluded = {'.git', '.venv', '__pycache__', 'node_modules', '.pytest_cache', 'runs'}
    candidates = [root / name for name in ('SKILL.md', 'requirements.txt', 'pyproject.toml')]
    roots = list(roots)
    manifest = root / '.claude-plugin/plugin.json'
    if manifest.is_file() and not manifest.is_symlink():
        config = json.loads(manifest.read_text())
        for field in ('commands', 'agents', 'skills', 'hooks', 'outputStyles'):
            declared = config.get(field, [])
            declared = [declared] if isinstance(declared, str) else declared
            if not isinstance(declared, list):
                continue  # Inline hook configuration is already fingerprinted in the manifest.
            for name in declared:
                if not isinstance(name, str):
                    raise ValueError(f'Unsupported manifest source path in {field}')
                target = (root / name).resolve()
                if not target.is_relative_to(root):
                    raise ValueError(f'Manifest source path escapes plugin: {name}')
                roots.append(str(target.relative_to(root)))
    for name in roots:
        source = root / name
        if source.is_dir():
            candidates.extend(source.rglob('*'))
        elif source.is_file():
            candidates.append(source)
    files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(set(candidates)) if p.is_file() and not p.is_symlink()
             and not excluded.intersection(p.relative_to(root).parts)
             and not p.name.startswith('.env') and p.suffix not in ('.pem', '.key')}
    return {'path': str(root), 'files': files}


def harness_source():
    root = Path(__file__).resolve().parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ('run.py', 'runtime.py', 'grade.py', 'report.py', 'RUBRIC.md')}


def output_hashes(out):
    names = ['final.md', 'stream.jsonl']
    if (out / 'work/review_summary.md').exists():
        names.append('work/review_summary.md')
    return {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
            for name in names if (out / name).exists()}


def run(task, arm, rep, model=None, timeout=1800, settings=None):
    model = configured_model(model)
    if task not in PROMPTS or arm not in PLUGINS:
        raise ValueError(f'Unknown task/arm: {task}/{arm}')
    plugin = PLUGINS[arm]
    if arm in ('current', 'mi', 'mi-cmd') and not plugin:
        raise ValueError(f'{arm} requires BENCH_CURRENT_PLUGIN or COMPARE_PLUGIN as applicable')
    source = {'plugin': plugin_source(plugin), 'harness': harness_source()}
    version = subprocess.run(['claude', '--version'], text=True, capture_output=True, check=True).stdout.strip()
    settings = dict(settings or {})
    prompt = COMMANDS.get((arm, task), '') + PROMPTS[task]
    config = {'cli_version': version, 'setting_sources': 'project', 'allowed_tools': TOOLS,
              'timeout_seconds': timeout, 'settings': settings,
              'rubric_sha256': hashlib.sha256((BENCH / 'RUBRIC.md').read_bytes()).hexdigest() if (BENCH / 'RUBRIC.md').exists() else None}
    run_id = identity(BENCH / 'inputs' / task, source, model, config, prompt)
    out = BENCH / 'runs' / task / f'{arm}-{rep}'
    if (out / 'meta.json').exists():
        old = json.loads((out / 'meta.json').read_text())
        if (reusable(old, run_id) and (out / 'final.md').exists()
                and digest(out / 'inputs') == old.get('inputs')
                and output_hashes(out) == old.get('outputs')
                and (hashlib.sha256((out / 'rubric.md').read_bytes()).hexdigest()
                     if (out / 'rubric.md').exists() else None) == old.get('rubric_sha256')):
            return task, arm, rep, 'skipped'
    # Preserve every prior attempt; failed outputs are evidence too.
    if out.exists():
        archive = out.parent / 'history' / f'{out.name}-{uuid.uuid4().hex}'
        archive.parent.mkdir(parents=True, exist_ok=True)
        out.rename(archive)
    out.mkdir(parents=True)
    shutil.copytree(BENCH / 'inputs' / task, out / 'inputs')
    shutil.copytree(out / 'inputs', out / 'work')
    before = digest(out / 'inputs')
    (out / 'prompt.txt').write_text(prompt)
    if (BENCH / 'RUBRIC.md').exists():
        shutil.copyfile(BENCH / 'RUBRIC.md', out / 'rubric.md')
    cmd = ['claude', '-p', '--model', model, '--setting-sources', 'project', '--allowedTools', TOOLS,
           '--output-format', 'stream-json', '--verbose']
    if settings:
        cmd += ['--settings', json.dumps(settings, sort_keys=True)]
    if plugin:
        cmd += ['--plugin-dir', str(Path(plugin).resolve())]
    start = time.monotonic()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    code, timed_out, error = None, False, None
    with (out / 'stream.jsonl').open('w') as stream, (out / 'stderr.txt').open('w') as err:
        try:
            proc = subprocess.run(cmd, input=prompt, text=True, cwd=out / 'work', stdout=stream,
                                  stderr=err, timeout=timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
        except OSError as exc:
            error = str(exc)
    events = []
    for line in (out / 'stream.jsonl').read_text().splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict): events.append(event)
        except json.JSONDecodeError:
            continue
    result = next((e for e in reversed(events) if e.get('type') == 'result'), {})
    tools, actual_model, plugins = [], None, []
    for event in events:
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            actual_model = event.get('model')
            plugins = event.get('plugins', [])
        if event.get('type') == 'assistant':
            for item in event.get('message', {}).get('content', []):
                if item.get('type') == 'tool_use':
                    tools.append({'name': item.get('name'), 'input': item.get('input')})
    completed = bool(code == 0 and not timed_out and result.get('subtype') == 'success'
                     and not result.get('is_error'))
    final = result.get('result') or ''
    (out / 'final.md').write_text(final)
    after = digest(out / 'work')
    meta = {'task': task, 'arm': arm, 'rep': rep, 'identity': run_id, 'started_at': started,
            'exit': code, 'completed': completed, 'timed_out': timed_out, 'error': error,
            'seconds': round(time.monotonic() - start, 3), 'requested_model': model, 'model': actual_model,
            'config': config, 'command': cmd, 'source': source, 'inputs': before,
            'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
            'rubric_sha256': hashlib.sha256((out / 'rubric.md').read_bytes()).hexdigest() if (out / 'rubric.md').exists() else None,
            'outputs': output_hashes(out), 'plugins': plugins, 'turns': result.get('num_turns'), 'tool_calls': len(tools),
            'tools': tools, 'subagent_calls': sum(t['name'] in ('Agent', 'Task') for t in tools),
            'skills': [t['input'].get('skill') if isinstance(t['input'], dict) else t['input']
                       for t in tools if t['name'] == 'Skill'],
            'inputs_modified': sorted(k for k in before if after.get(k) != before[k]),
            'new_files': sorted(set(after) - set(before)), **usage(events)}
    (out / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    return task, arm, rep, f"completed={completed} {meta['seconds']}s ${meta['cost_usd']}"


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tasks', help='Comma separated task IDs')
    parser.add_argument('reps', type=int)
    parser.add_argument('workers', type=int, nargs='?', default=6)
    parser.add_argument('arms', nargs='?', default='base,format-only,current,reo')
    parser.add_argument('--model')
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    model = configured_model(args.model)
    if args.reps < 1 or args.workers < 1: parser.error('reps and workers must be positive')
    jobs = [(t, a, r) for r in range(1, args.reps + 1) for t in args.tasks.split(',') for a in args.arms.split(',')]
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(lambda job: run(*job, model=model, timeout=args.timeout), jobs):
            print(*result, flush=True)
