#!/usr/bin/env python3
"""Extract a thesis skeleton for fast, low-cost review (standard library only).

Usage:
    python3 scripts/thesis_skeleton.py THESIS.(md|txt|docx) [--out skeleton.md] [--json]

Outputs, in one pass:
- headings (outline)
- the first sentence of every paragraph ("topic-sentence reading")
- figure and table captions
- sentences with strong claim verbs, to check claim strength (flagged on topic sentences)
- overlong sentences, to check one idea per sentence (flagged on topic sentences)
Long texts are clipped to 160 characters; open the block in the full text for the rest.

The output is evidence for a reviewer, not a judgement. Every finding still has to be
checked against the full text before it is reported.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
CLAIM = re.compile(
    r'\b(prove[sd]?|establish(?:ed|es)?|develop(?:ed|s)?|demonstrat(?:ed|es)|clarif(?:ied|ies)|reveal(?:ed|s)?|confirm(?:ed|s)?|novel|first)\b'
    r'|証明|確立|開発し|明らかに|解明|実証|示した|初めて|新規',
    re.IGNORECASE)
CAPTION = re.compile(r'^\s*(fig(?:ure)?\.?|table|図|表)\s*[0-9０-９]', re.IGNORECASE)
SENT_SPLIT = re.compile(r'(?<=[。．！？!?])|(?<=\.)\s+(?=[A-Z(])')


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read('word/document.xml'))
    blocks = []
    for p in root.iter(W + 'p'):
        style = p.find(f'{W}pPr/{W}pStyle')
        sval = style.get(W + 'val', '') if style is not None else ''
        text = ''.join(t.text or '' for t in p.iter(W + 't')).strip()
        if not text:
            continue
        level = 0
        m = re.search(r'(?:Heading|見出し)\s*([0-9])', sval)
        if m:
            level = int(m.group(1))
        elif sval.lower() == 'title':
            level = 1
        blocks.append((level, text))
    return blocks


def read_text(path):
    blocks, buf = [], []
    def flush():
        if buf:
            blocks.append((0, ' '.join(s.strip() for s in buf).strip()))
            buf.clear()
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            flush()
            blocks.append((len(m.group(1)), m.group(2).strip()))
        elif not line.strip():
            flush()
        else:
            buf.append(line)
    flush()
    return blocks


def sentences(text):
    return [s.strip() for s in SENT_SPLIT.split(text) if s and s.strip()]


def too_long(s):
    ascii_words = len(re.findall(r'[A-Za-z]+', s))
    cjk = len(re.findall(r'[぀-ヿ一-鿿]', s))
    return ascii_words > 40 or cjk > 80


def clip(s, n=160):
    return s if len(s) <= n else s[:n] + '…'


def build(blocks):
    out = {'outline': [], 'topic_sentences': [], 'captions': [], 'claims': [], 'long_sentences': []}
    section = ''
    for i, (level, text) in enumerate(blocks, 1):
        if level:
            section = text
            out['outline'].append({'level': level, 'heading': text, 'block': i})
            continue
        if CAPTION.match(text):
            out['captions'].append({'section': section, 'block': i, 'text': clip(text)})
            continue
        sents = sentences(text)
        if not sents:
            continue
        out['topic_sentences'].append({'section': section, 'block': i, 'text': clip(sents[0]),
                                       'flags': [f for f, hit in (('claim', CLAIM.search(sents[0])), ('long', too_long(sents[0]))) if hit]})
        for s in sents[1:]:
            if CLAIM.search(s):
                out['claims'].append({'section': section, 'block': i, 'text': clip(s)})
            if too_long(s):
                out['long_sentences'].append({'section': section, 'block': i, 'text': clip(s)})
    out['counts'] = {k: len(v) for k, v in out.items() if isinstance(v, list)}
    return out


def to_markdown(data, source):
    lines = [f'# Thesis skeleton: {source}', '',
             'Counts: ' + ', '.join(f'{k} {v}' for k, v in data['counts'].items()), '', '## Outline']
    lines += [f"{'  ' * (o['level'] - 1)}- {o['heading']} (block {o['block']})" for o in data['outline']]
    lines += ['', '## Topic sentences (read these alone: does the argument flow?)']
    last = None
    for d in data['topic_sentences']:
        if d['section'] != last:
            lines.append(f"### {d['section'] or '-'}")
            last = d['section']
        flag = f" [{','.join(d['flags'])}]" if d['flags'] else ''
        lines.append(f"- {d['block']}{flag}: {d['text']}")
    for key, title in (
                       ('captions', 'Figure and table captions'),
                       ('claims', 'Strong claim wording in later sentences (check against evidence)'),
                       ('long_sentences', 'Overlong later sentences (one idea per sentence?)')):
        lines += ['', f'## {title}']
        lines += [f"- {d['block']}: {d['text']}" for d in data[key]] or ['- none']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('path')
    ap.add_argument('--out')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    path = Path(a.path)
    if not path.exists():
        print(f'not found: {path}', file=sys.stderr)
        return 2
    blocks = read_docx(path) if path.suffix.lower() == '.docx' else read_text(path)
    data = build(blocks)
    text = json.dumps(data, ensure_ascii=False, indent=1) if a.json else to_markdown(data, path.name)
    if a.out:
        Path(a.out).write_text(text, encoding='utf-8')
        print(json.dumps({'written': a.out, 'counts': data['counts']}, ensure_ascii=False))
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
