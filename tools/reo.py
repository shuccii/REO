#!/usr/bin/env python3
"""Re.O local entry point. Inspection is read-only unless --save is explicit."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import tempfile
import zipfile
from xml.etree.ElementTree import ParseError
from collections import Counter,defaultdict
from pathlib import Path
from reo_profile import load,resolve_path
from review_plan import plan
from review_state import build,compare

ROOT=Path(__file__).resolve().parents[1]


def version():
    return json.loads((ROOT/'.codex-plugin/plugin.json').read_text())['version']


def doctor(workspace):
    deps={name:importlib.util.find_spec(module) is not None for name,module in
          [('numpy','numpy'),('scipy','scipy'),('pint','pint'),('uncertainties','uncertainties'),
           ('statsmodels','statsmodels'),('biopython','Bio'),('rdkit','rdkit')]}
    supported=sys.version_info>=(3,12)
    return {'plugin_version':version(),'python':{'version':sys.version.split()[0],'supported':supported,
            'executable':sys.executable},'dependencies':deps,'profile':load(resolve_path(workspace=workspace)),
            'notes':['No dependency installation performed. Missing optional domain packages do not block text review.']}


def check_document(path):
    suffix=path.suffix.lower()
    if suffix not in ('.md','.txt','.docx'):raise ValueError('supported documents: .md, .txt, .docx')
    # Reuse the existing document parser; no model tokens required.
    sys.path.insert(0,str(ROOT/'scripts'))
    from thesis_skeleton import read_docx,read_text,CLAIM,CAPTION
    blocks=read_docx(path) if suffix=='.docx' else read_text(path)
    numbers=[]
    for i,(level,text) in enumerate(blocks,1):
        for match in re.finditer(r'(?<![\w])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?\s*(?:%|[A-Za-zμ°]+(?:/[A-Za-z]+)?)?',text):
            numbers.append({'block':i,'text':match.group().strip()})
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'blocks':len(blocks),
            'headings':[{'block':i,'level':level,'text':text} for i,(level,text) in enumerate(blocks,1) if level],
            'captions':[{'block':i,'text':text} for i,(_,text) in enumerate(blocks,1) if CAPTION.search(text)],
            'claim_candidates':[{'block':i,'text':text[:240]} for i,(_,text) in enumerate(blocks,1) if CLAIM.search(text)],
            'number_ledger':numbers,'locator_note':'Block indices identify parser blocks, not page or line numbers. Open the full block before a finding.'}


def check_csv(path,unit=None,split=None,target=None):
    with path.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f,strict=True);cols=reader.fieldnames or []
        if len(cols)!=len(set(cols)):raise ValueError('duplicate CSV column names')
        for column in (unit,split,target):
            if column and column not in cols:raise ValueError('missing column: '+column)
        rows=list(reader)
    if not cols or not rows:raise ValueError('CSV requires header and data rows')
    if any(None in row or any(v is None for v in row.values()) for row in rows):raise ValueError('ragged CSV rows')
    duplicates=sum(n-1 for n in Counter(tuple(r[c] for c in cols) for r in rows).values())
    missing={c:sum(not r[c].strip() for r in rows) for c in cols}
    if any(missing[c] for c in (unit,split) if c):raise ValueError('missing unit/split identifiers')
    nonfinite={}
    for c in cols:
        n=0
        for row in rows:
            try:n+=not math.isfinite(float(row[c]))
            except ValueError:pass
        if n:nonfinite[c]=n
    overlap=None
    if unit and split:
        assignments=defaultdict(set)
        for r in rows:assignments[r[unit]].add(r[split])
        overlap=sorted(u for u,s in assignments.items() if len(s)>1)
    result={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'n_rows':len(rows),'columns':cols,
            'duplicate_rows':duplicates,'missing':missing,'nonfinite':nonfinite,'cross_split_units':overlap,
            'roles':{'unit':unit,'split':split,'target':target}}
    if target:
        from choose_evaluation import recommend
        if nonfinite.get(target) or missing.get(target):
            result['evaluation_recommendation']={'status':'not_run','reason':'Target contains missing or nonfinite values; inspect source before recommending evaluation.'}
        else:
            result['evaluation_recommendation']=recommend(rows,target,unit,None,'auto')
    return result


def save_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    # Atomic replacement avoids a truncated review state after interruption.
    handle=tempfile.NamedTemporaryFile('w',dir=path.parent,delete=False,encoding='utf-8')
    try:
        with handle:json.dump(data,handle,ensure_ascii=False,indent=2,allow_nan=False);handle.write('\n')
        os.replace(handle.name,path)
    finally:
        if Path(handle.name).exists():Path(handle.name).unlink()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('doctor');d.add_argument('--workspace',default='.')
    profile=sub.add_parser('profile');profile.add_argument('--workspace',default='.');profile.add_argument('--path')
    c=sub.add_parser('check');c.add_argument('document');c.add_argument('--data');c.add_argument('--unit');c.add_argument('--split');c.add_argument('--target');c.add_argument('--save');c.add_argument('--full',action='store_true',help='Print complete ledgers; default prints first 20 entries with totals')
    r=sub.add_parser('plan');r.add_argument('--mode',choices=['quick','standard','deep'],default='standard');r.add_argument('--task',choices=['audit','peer_review','defense','supervision'],default='peer_review');r.add_argument('--field',default='');r.add_argument('--long',action='store_true');r.add_argument('--previous',action='store_true')
    state=sub.add_parser('state');state.add_argument('graph');state.add_argument('--workspace',default='.');state.add_argument('--context');state.add_argument('--previous');state.add_argument('--save')
    a=p.parse_args(argv);code=0
    try:
        if a.command=='doctor':
            result=doctor(a.workspace);code=0 if result['python']['supported'] else 1
        elif a.command=='profile':result=load(resolve_path(a.path,a.workspace))
        elif a.command=='plan':result=plan(**{k:v for k,v in vars(a).items() if k!='command'})
        elif a.command=='check':
            result={'document':check_document(Path(a.document)),'data':None,'scientific_validity_assessed':False,
                    'limitations':['Number ledger and claim candidates require semantic verification; no automated manuscript-to-data correspondence is inferred.'],
                    'summary':[]}
            if a.data:
                result['data']=check_csv(Path(a.data),a.unit,a.split,a.target);data=result['data']
                if not (a.unit and a.split):result['limitations'].append('Unit/split roles not supplied; cross-split unit overlap not assessed.')
                for name,value in [('duplicate rows',data['duplicate_rows']),('units spanning splits',len(data['cross_split_units'] or [])),
                                   ('missing cells',sum(data['missing'].values())),('nonfinite numeric values',sum(data['nonfinite'].values()))]:
                    if value:result['summary'].append(f'{name}: {value}')
                if data.get('evaluation_recommendation',{}).get('warnings'):result['summary']+=data['evaluation_recommendation']['warnings']
            else:result['limitations'].append('No CSV supplied; data checks not assessed.')
            code=1 if result['summary'] else 0
            if not result['summary']:result['summary']=['Deterministic checks completed; scientific validity is unassessed.']
            if a.save:
                protected={Path(a.document).resolve()}
                if a.data:protected.add(Path(a.data).resolve())
                if Path(a.save).resolve() in protected:raise ValueError('save path must not overwrite input document or CSV')
                save_json(a.save,result)
            if not a.full:
                for key in ('headings','captions','claim_candidates','number_ledger'):
                    values=result['document'][key]
                    result['document'][key+'_total']=len(values)
                    result['document'][key]=values[:20]
                result['limitations'].append('Console ledgers show at most 20 entries each; use --full or --save for complete evidence.')
        else:
            graph=json.loads(Path(a.graph).read_text());context=json.loads(Path(a.context).read_text()) if a.context else {}
            # Context covers actual bundled tool bytes and local profile, not just a version label.
            source_files=sorted(x for folder in ('tools','scripts','assets') for x in (ROOT/folder).rglob('*') if x.is_file() and x.suffix in ('.py','.json'))
            tool_hash=hashlib.sha256(b''.join(str(x.relative_to(ROOT)).encode()+b'\0'+x.read_bytes()+b'\0' for x in source_files)).hexdigest()
            profile_path=resolve_path(workspace=a.workspace)
            context={**context,'plugin_version':version(),'tools_hash':tool_hash,
                     'profile_hash':hashlib.sha256(profile_path.read_bytes()).hexdigest() if profile_path.is_file() else None}
            current=build(graph,a.workspace,context)
            previous=json.loads(Path(a.previous).read_text()) if a.previous else None
            result={'state':current,'delta':compare(previous,current)}
            if a.save:
                inputs={Path(a.graph).resolve(),*( (Path(a.previous).resolve(),) if a.previous else ())}
                inputs|={(Path(a.workspace)/n['path']).resolve() for n in current['nodes'].values()}
                inputs.add(profile_path.resolve())
                if a.context:inputs.add(Path(a.context).resolve())
                if Path(a.save).resolve() in inputs:raise ValueError('save path must not overwrite graph, previous state or evidence')
                save_json(a.save,current)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False));return code
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile,ParseError,csv.Error) as error:
        print(json.dumps({'error':str(error)},ensure_ascii=False));return 2

if __name__=='__main__':raise SystemExit(main())
