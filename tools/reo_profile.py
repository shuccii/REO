#!/usr/bin/env python3
"""Read the user's Re.O profile and list the discipline probes that apply.

Example:
    python3 tools/reo_profile.py
    python3 tools/reo_profile.py --path ./profile.md

Looks for $REO_PROFILE, then ~/.config/reo/profile.md. Prints JSON and always exits 0
when the file is missing (`exists: false`), so callers can continue without a profile.
Standard library only.
"""
import argparse
import json
import os
from pathlib import Path

DEFAULT_PATH = Path('~/.config/reo/profile.md')
PROBE_DIR = 'skills/research-review-workflow/references/probes'
FIELDS = {
    '分野': 'field', '主な手法': 'methods', '今の段階': 'phase', '所属大学': 'institution',
    '公式の基準の有無と出典(確認日)': 'criteria', '研究室規程の登録': 'lab_policies',
}
# Keyword -> probe file. Checked against the field and the methods.
FIELD_PROBES = [
    ('材料', 'materials-ml.md'), ('生物', 'bio-experimental.md'), ('医学', 'bio-experimental.md'),
    ('薬学', 'bio-experimental.md'), ('化学', 'chemistry-synthesis.md'), ('物理', 'physics-engineering.md'),
    ('工学', 'physics-engineering.md'), ('地球', 'field-observational.md'), ('環境', 'field-observational.md'),
    ('情報', 'simulation-theory.md'), ('数理', 'simulation-theory.md'),
]
METHOD_PROBES = [
    ('計算', 'simulation-theory.md'), ('シミュレーション', 'simulation-theory.md'), ('理論', 'simulation-theory.md'),
    ('観察', 'field-observational.md'), ('調査', 'field-observational.md'),
]
UNSET = {'', '未設定', 'なし', '-'}


def resolve_path(explicit=None):
    if explicit:
        return Path(explicit).expanduser()
    if os.environ.get('REO_PROFILE'):
        return Path(os.environ['REO_PROFILE']).expanduser()
    return DEFAULT_PATH.expanduser()


def parse(text):
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('- ') or ':' not in line:
            continue
        label, value = line[2:].split(':', 1)
        key = FIELDS.get(label.strip())
        if key:
            value = value.strip()
            values[key] = None if value in UNSET else value
    return values


def probes_for(values):
    chosen = []
    for text, table in ((values.get('field') or '', FIELD_PROBES), (values.get('methods') or '', METHOD_PROBES)):
        for keyword, probe in table:
            if keyword in text and probe not in chosen:
                chosen.append(probe)
    return chosen


def load(path):
    if not path.is_file():
        return {'exists': False, 'path': str(path),
                'note': 'No profile. Continue with general checks and suggest the setup-profile skill once.'}
    values = parse(path.read_text(encoding='utf-8'))
    probes = probes_for(values)
    methods = values.get('methods') or ''
    return {
        'exists': True, 'path': str(path),
        'profile': {key: values.get(key) for key in FIELDS.values()},
        'unset': [key for key in FIELDS.values() if not values.get(key)],
        'probes': [f'{PROBE_DIR}/{name}' for name in probes],
        'use_research_ml_workflow': any(word in methods for word in ('機械学習', 'データ解析')),
        'phase_expectations': 'skills/research-review-workflow/references/phase-expectations.md',
        'note': 'The current request overrides the profile. Say which probes were used.',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read the Re.O user profile.')
    parser.add_argument('--path', help='profile file (default: $REO_PROFILE or ~/.config/reo/profile.md)')
    args = parser.parse_args(argv)
    try:
        report = load(resolve_path(args.path))
    except (OSError, UnicodeDecodeError) as error:
        report = {'exists': False, 'error': str(error)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
