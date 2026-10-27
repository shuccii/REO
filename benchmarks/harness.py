"""Common evaluator, not a scheduler. Run each frozen case in a fresh Codex process.

The outer process observes timing and events; worker declarations never become telemetry.
Raw events stay local because installed skill metadata can contain private paths.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

from cases import CASES, HOLDOUT, independent_module_tasks, score
from validate_task_result import check_one
from validate_research_contract import evidence_references, validate_research_contract

ROOT = Path(__file__).resolve().parents[1]


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def evaluator_digest():
    paths=['benchmarks/harness.py','benchmarks/cases.py','benchmarks/PROTOCOL.md','scripts/manifest_helper.py','scripts/schema_subset.py','scripts/validate_task_result.py','scripts/validate_research_contract.py','assets/task-manifest.schema.json','assets/task-result.schema.json','assets/research-contract.schema.json','assets/verification-policy.json']
    value={name:(ROOT/name).read_text() for name in paths}
    return digest(value)


def frozen_files(ref):
    if ref == 'working':
        paths = ['.codex-plugin/plugin.json'] + [str(p.relative_to(ROOT)) for folder in ('skills','scripts','assets') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name!='.DS_Store']
        return {p:(ROOT/p).read_text() for p in paths}
    paths = subprocess.check_output(['git','ls-tree','-r','--name-only',ref],cwd=ROOT,text=True).splitlines()
    return {p:subprocess.check_output(['git','show',f'{ref}:{p}'],cwd=ROOT,text=True) for p in paths if p.startswith(('skills/','scripts/','assets/','.codex-plugin/'))}


def summarize_events(events):
    usage = {k:0 for k in ('input_tokens','output_tokens','cached_input_tokens','reasoning_output_tokens')}
    present = set()
    counts = {'turn_count':0, 'tool_call_count':0, 'observed_subagent_events':0, 'observed_collaboration_events':0, 'observed_spawn_calls':0, 'observed_unbound_waits':0}
    seen = set(); collaboration={}; observed_agents=set()
    for event in events:
        if event.get('type') == 'turn.completed':
            counts['turn_count'] += 1
            for key, value in event.get('usage',{}).items():
                if key in usage and isinstance(value,int) and not isinstance(value,bool):
                    usage[key] += value
                    present.add(key)
        item = event.get('item',{})
        if event.get('type') in ('item.started','item.completed') and item.get('id') is not None and item.get('type') in ('collab_agent_tool_call','collab_tool_call'):
            record=collaboration.setdefault(item['id'],{'tools':set(),'bound':False})
            if item.get('tool'): record['tools'].add(item['tool'])
            record['bound'] |= bool(item.get('receiver_thread_ids') or item.get('agents_states'))
            observed_agents.update(value for value in (item.get('receiver_thread_ids') or []) if isinstance(value,str))
            observed_agents.update(value for value in (item.get('agents_states') or {}) if isinstance(value,str))
        elif event.get('type') in ('item.started','item.completed') and item.get('id') is not None and item.get('id') not in seen:
            seen.add(item.get('id'))
            if item.get('type') in ('command_execution','mcp_tool_call','web_search'):
                counts['tool_call_count'] += 1
    for record in collaboration.values():
        counts['observed_collaboration_events'] += 1; counts['tool_call_count'] += 1
        if 'wait' in record['tools'] and not record['bound']: counts['observed_unbound_waits'] += 1
        if record['tools'] & {'spawn','spawn_agent'}: counts['observed_spawn_calls'] += 1; counts['observed_subagent_events'] += 1
    return {**{k:(v if k in present else None) for k,v in usage.items()}, **counts, 'observed_agent_ids':sorted(observed_agents), 'llm_call_count':None, 'review_count':None, 'subagent_count':None, 'model_observed':None, 'cost':None,
            'unavailable_reason':{'llm_call_count':'turns are not model requests','review_count':'CLI does not identify semantic reviewer roles','subagent_count':'coverage of nested agent telemetry unverified','model_observed':'requested model is not an observed model identity','cost':'no billing data exposed'}}


def score_observed_behavior(case_id, grade, telemetry):
    if case_id in ('format','holdout_format'):
        grade['critical']['no_collaboration_calls']=telemetry['observed_collaboration_events']==0
        grade['critical_pass']=grade['critical_pass'] and grade['critical']['no_collaboration_calls']
    if case_id=='independent_modules':
        grade['critical']['no_unbound_collaboration_waits']=telemetry['observed_unbound_waits']==0
        grade['critical_pass']=grade['critical_pass'] and grade['critical']['no_unbound_collaboration_waits']
    return grade


def score_review_completion(root, grade, telemetry):
    """Require v0.2 semantic contracts plus externally observed reviewer identity."""
    schema=json.loads((ROOT/'assets/task-result.schema.json').read_text())
    observed=set(telemetry['observed_agent_ids']); passed=False
    for manifest_path in root.glob('**/tasks.json'):
        try:
            manifest=json.loads(manifest_path.read_text())
            targets=independent_module_tasks(manifest)
            if not targets: continue
            tasks={task['task_id']:task for task in manifest['tasks']}
            target_ids={task['task_id'] for task in targets}; reviewed=set()
            for result_path in manifest_path.parent.rglob('result.json'):
                owner=next((parent/'tasks.json' for parent in (result_path.parent,*result_path.parents) if (parent/'tasks.json').exists()),None)
                if owner!=manifest_path: continue
                data=json.loads(result_path.read_text())
                if not isinstance(data,dict) or data.get('task_id') not in target_ids: continue
                task=tasks[data['task_id']]
                verdict=check_one(result_path,schema,manifest,False)
                reviewer=data.get('verification',{}).get('validity_review',{}).get('reviewer_id')
                if verdict['completion_eligible'] and reviewer in observed: reviewed.add(task['task_id'])
            if reviewed==target_ids: passed=True; break
        except (OSError,ValueError,TypeError,KeyError): continue
    grade['critical']['independent_review_completed']=passed
    grade['critical_pass']=grade['critical_pass'] and passed
    return grade

def score_strict_research_completion(root, grade, telemetry):
    """Require a valid strict contract, integrated result, and observed independent reviewer."""
    schema=json.loads((ROOT/'assets/task-result.schema.json').read_text()); observed=set(telemetry['observed_agent_ids'])
    manifest_ok=contract_ok=result_ok=review_ok=False
    for manifest_path in root.glob('**/tasks.json'):
        try:
            manifest=json.loads(manifest_path.read_text())
            if manifest.get('assurance_profile')!='research_strict': continue
            from manifest_helper import validate_manifest
            if validate_manifest(manifest): continue
            manifest_ok=True; contract_path=manifest_path.parent/manifest['research_contract']
            if contract_path.is_symlink() or not contract_path.resolve().is_relative_to(manifest_path.parent.resolve()): continue
            contract=json.loads(contract_path.read_text())
            if validate_research_contract(contract,manifest,contract_path.parent): continue
            contract_ok=True
            for result_path in manifest_path.parent.rglob('result.json'):
                data=json.loads(result_path.read_text())
                verdict=check_one(result_path,schema,manifest,False); review=data.get('verification',{}).get('validity_review',{}); reviewer=review.get('reviewer_id')
                bundle=data.get('reproduction_bundle'); bundle_ok=isinstance(bundle,str) and bundle in data.get('artifacts',[]) and (result_path.parent/bundle).is_file()
                if verdict['valid'] and data.get('status')=='needs_revision' and strict_result_contract_matches(contract,data) and bundle_ok and review.get('status')=='passed' and reviewer and reviewer!=data.get('worker_id'):
                    result_ok=True
                    if reviewer in observed: review_ok=True
        except (OSError,ValueError,TypeError,KeyError): continue
    grade['critical'].update(strict_manifest=manifest_ok,strict_contract=contract_ok,strict_needs_revision_result=result_ok,strict_observed_reviewer=review_ok)
    grade['critical_pass']=grade['critical_pass'] and all((manifest_ok,contract_ok,result_ok,review_ok))
    return grade

def strict_result_contract_matches(contract,data):
    expected={gate['gate_id']:gate['status'] for gate in contract['validation_gates']}
    actual={gate['gate_id']:gate['status'] for gate in data.get('research_validation',[])}
    invalidated={product['artifact_id'] for product in contract['products'] if product['status']=='invalidated'}
    return actual==expected and evidence_references(contract) <= set(data.get('evidence',[])) and set(data.get('invalidated_artifacts',[]))==invalidated


def run_case(case_id, ref, output, model, effort, timeout, phase, pair, session_id, attempt=0):
    case = (CASES | HOLDOUT)[case_id]
    version_files = frozen_files(ref)
    run_id = f'{phase}-{case_id}-{pair}-{attempt}-{time.time_ns()}'
    raw = output/'raw'/run_id
    raw.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='rdo-eval-') as tmp:
        work = Path(tmp)
        for path, body in case['files'].items():
            dest = work/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(body)
        for path, body in version_files.items():
            dest = work/'selected-pack'/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(body)
        instructions = version_files['skills/orchestrate-work/SKILL.md']
        if case['skill']:
            instructions += '\n' + version_files[f"skills/{case['skill']}/SKILL.md"]
        # Excludes answers/scoring and keeps both versions' environment identical.
        prompt = ('You are executing a public synthetic benchmark, not modifying the real plugin. '
                  'Use only the fixture files in this working directory and selected-pack. No network, private data, or other project files. '
                  'Do not inspect evaluation source or grading files. Native subagents are permitted when the selected workflow requires them. '
                  'Do not create sidebar tasks. Follow the selected workflow below; shared scripts/assets are relative to selected-pack.\n'
                  + instructions + '\nUSER TASK:\n' + case['prompt'])
        (work/'AGENTS.md').write_text('This is an isolated synthetic evaluation. Follow only the selected-pack workflow supplied in the task. Keep all output here. No network or private files.\n')
        command = ['codex','exec','--ignore-user-config','--ephemeral','--json','--model',model,'-c',f'model_reasoning_effort="{effort}"','--sandbox','workspace-write','--skip-git-repo-check','-']
        started = utc()
        tick = time.monotonic()
        events = []
        timed_out = False
        with (raw/'stderr.log').open('w') as err, (raw/'events.jsonl').open('w') as log:
            proc = subprocess.Popen(command,cwd=work,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,start_new_session=True)
            proc.stdin.write(prompt.encode())
            proc.stdin.close()
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout,selectors.EVENT_READ)
            buffer = b''
            while selector.get_map():
                if time.monotonic()-tick >= timeout:
                    timed_out = True
                    os.killpg(proc.pid,signal.SIGTERM)
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL)
                    break
                for key,_ in selector.select(timeout=.2):
                    chunk = os.read(key.fileobj.fileno(),65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffer += chunk
                    while b'\n' in buffer:
                        line,buffer = buffer.split(b'\n',1)
                        try:
                            event = json.loads(line)
                            events.append(event)
                            log.write(json.dumps({'observed_at':utc(),'event':event})+'\n')
                        except ValueError: pass
            proc.wait()
            selector.close()
        elapsed = time.monotonic()-tick
        unsafe_links=[str(path.relative_to(work)) for path in work.rglob('*') if path.is_symlink()]
        grade = score(case_id,work) if not unsafe_links else {'critical':{},'critical_pass':False,'noncritical_score':0,'findings':[],'semantic_adjudication':'pending','error':f'workspace contains symlink(s): {unsafe_links}'}
        telemetry=summarize_events(events)
        grade=score_observed_behavior(case_id,grade,telemetry)
        if ref=='working' and case_id=='independent_modules' and not unsafe_links:
            grade=score_review_completion(work,grade,telemetry)
        if ref=='working' and case_id=='research_strict_defects' and not unsafe_links:
            grade=score_strict_research_completion(work,grade,telemetry)
        # Only selected outputs, never the real home/config, are retained.
        import shutil
        shutil.copytree(work,raw/'workspace',symlinks=True,ignore=shutil.ignore_patterns('selected-pack','__pycache__'))
        errors = [e for e in events if e.get('type') in ('error','turn.failed')]
        infrastructure_failure = timed_out or proc.returncode != 0 or not any(e.get('type')=='turn.completed' for e in events)
        row = {'benchmark_session_id':session_id,'run_id':run_id,'task_id':case_id,'case_id':case_id,'version':ref,'phase':phase,'pair':pair,'attempt':attempt,'started_at':started,'ended_at':utc(),
               'elapsed_wall_clock':elapsed,'active_wall_clock':elapsed,'approval_wait':0.0,'approval_wait_basis':'noninteractive pre-set permissions; no human approval channel',
               'status':'infrastructure_error' if infrastructure_failure else 'completed','timed_out':timed_out,'exit_code':proc.returncode,'retries':attempt,
               'requested_model':model,'reasoning_effort':effort,'errors':errors,'grade':grade,'raw_path':str(raw),
               'pack_sha256':digest(version_files),'case_sha256':digest(case),'evaluator_sha256':evaluator_digest(),**telemetry}
        output.mkdir(parents=True,exist_ok=True)
        with (output/'metrics.jsonl').open('a') as handle: handle.write(json.dumps(row,ensure_ascii=False)+'\n')
        print(json.dumps({'case':case_id,'version':ref,'phase':phase,'pair':pair,'status':row['status'],'seconds':round(elapsed,2),'critical_pass':grade['critical_pass'] }),flush=True)
        return row


def validate_adjudications(rows, path):
    if not path.exists(): return {}
    known={row['run_id']:row for row in rows}; result={}
    for number,line in enumerate(path.read_text().splitlines(),1):
        try: item=json.loads(line)
        except ValueError as exc: raise ValueError(f'{path}:{number}: {exc}') from exc
        required={'benchmark_session_id','run_id','case_id','version','passed','critical_failures','reviewer_id','reviewed_at'}
        if set(item) != required: raise ValueError(f'{path}:{number}: fields must be exactly {sorted(required)}')
        row=known.get(item['run_id'])
        if not row or any(item[key]!=row[key] for key in ('benchmark_session_id','case_id','version')): raise ValueError(f'{path}:{number}: adjudication does not match a measured run')
        if item['run_id'] in result: raise ValueError(f'{path}:{number}: duplicate run_id')
        if not isinstance(item['passed'],bool) or not isinstance(item['critical_failures'],list) or not all(isinstance(v,str) for v in item['critical_failures']): raise ValueError(f'{path}:{number}: invalid decision fields')
        if item['passed'] == bool(item['critical_failures']): raise ValueError(f'{path}:{number}: passed must be true exactly when critical_failures is empty')
        if not isinstance(item['reviewer_id'],str) or not item['reviewer_id'].strip(): raise ValueError(f'{path}:{number}: reviewer_id required')
        try: datetime.fromisoformat(item['reviewed_at'].replace('Z','+00:00'))
        except (ValueError,AttributeError): raise ValueError(f'{path}:{number}: reviewed_at must be ISO-8601')
        result[item['run_id']]=item
    return result


def compare(rows, cases=None, config=None, adjudications=None):
    cases = list(CASES) if cases is None else cases
    session_id=config.get('benchmark_session_id') if config else None
    rows=[row for row in rows if session_id is None or row.get('benchmark_session_id')==session_id]
    adjudications=adjudications or {}
    ratios = []
    per_case = {}
    reasons = []
    quality_failure = False
    for case in cases:
        values = []
        for pair in range(3):
            selected = {}; duplicates=set()
            for row in rows:
                if row['phase']=='comparison' and row['case_id']==case and row['pair']==pair and row['status']=='completed':
                    if row['version'] in selected: duplicates.add(row['version'])
                    selected[row['version']] = row
            if duplicates:
                reasons.append(f'{case} pair {pair}: duplicate rows for {sorted(duplicates)}'); continue
            if not all(k in selected for k in ('v0.1.0','working')):
                reasons.append(f'{case} pair {pair}: missing valid pair')
                continue
            old,new = selected['v0.1.0'],selected['working']
            for row in (old,new):
                expected_pack=(config or {}).get('pack_sha256',{}).get(row['version'])
                expected_case=(config or {}).get('case_sha256',{}).get(case)
                if config and (row.get('requested_model')!=config['model'] or row.get('reasoning_effort')!=config['effort'] or row.get('pack_sha256')!=expected_pack or row.get('case_sha256')!=expected_case or row.get('evaluator_sha256')!=config['evaluator_sha256']):
                    reasons.append(f'{case} pair {pair}: frozen configuration mismatch')
            if not new['grade']['critical_pass'] or new['grade']['noncritical_score'] < old['grade']['noncritical_score']:
                quality_failure = True
            if case not in ('format',):
                decisions=[adjudications.get(row['run_id']) for row in (old,new)]
                if any(decision is None for decision in decisions): reasons.append(f'{case} pair {pair}: independent semantic adjudication pending')
                elif any(decision['passed'] is False for decision in decisions):
                    quality_failure=True; reasons.append(f'{case} pair {pair}: independent semantic adjudication failed')
            values.append(new['active_wall_clock']/old['active_wall_clock'])
        per_case[case] = statistics.median(values) if values else None
        ratios.extend(values)
    median = statistics.median(ratios) if ratios else None
    speed = median is not None and median <= .90 and all(v is not None and v <= 1.15 for v in per_case.values())
    return {'decision':'fail' if quality_failure else ('insufficient_measurement' if reasons else ('pass' if speed else 'fail')),
            'quality_failure':quality_failure,'speed_pass':speed,'paired_ratio_median':median,'per_case_ratio_median':per_case,'reasons':sorted(set(reasons))}


def evaluate_holdout(rows, holdout_config, primary_config, adjudications=None):
    adjudications=adjudications or {}; reasons=[]; quality_failure=False
    selected=[row for row in rows if row.get('benchmark_session_id')==holdout_config['benchmark_session_id'] and row.get('phase')=='holdout']
    for case in HOLDOUT:
        matches=[row for row in selected if row['case_id']==case and row['version']=='working' and row['status']=='completed']
        if len(matches)!=1: reasons.append(f'{case}: expected exactly one completed holdout run'); continue
        row=matches[0]
        if (row.get('pack_sha256')!=primary_config['pack_sha256']['working'] or row.get('case_sha256')!=primary_config['holdout_case_sha256'][case]
                or row.get('requested_model')!=primary_config['model'] or row.get('reasoning_effort')!=primary_config['effort'] or row.get('evaluator_sha256')!=primary_config['evaluator_sha256']): reasons.append(f'{case}: frozen configuration mismatch')
        if not row['grade']['critical_pass']: quality_failure=True; reasons.append(f'{case}: critical checks failed')
        if case!='holdout_format':
            decision=adjudications.get(row['run_id'])
            if decision is None: reasons.append(f'{case}: independent semantic adjudication pending')
            elif decision['passed'] is False: quality_failure=True; reasons.append(f'{case}: independent semantic adjudication failed')
    return {'decision':'fail' if quality_failure else ('insufficient_measurement' if reasons else 'pass'),'quality_failure':quality_failure,'reasons':reasons}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode',choices=['pilot','compare','report','holdout','holdout-report','adjudication-template'])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',default='gpt-5.6-terra')
    p.add_argument('--effort',default='high')
    p.add_argument('--timeout',type=float,default=300)
    p.add_argument('--case',choices=list(CASES))
    p.add_argument('--max-llm-calls',type=int)
    p.add_argument('--max-total-tokens',type=int)
    args = p.parse_args()
    if not math.isfinite(args.timeout) or args.timeout<=0: p.error('--timeout must be finite and positive')
    if args.max_total_tokens is not None and args.max_total_tokens<=0: p.error('--max-total-tokens must be positive')
    if args.max_llm_calls is not None and args.max_llm_calls<=0: p.error('--max-llm-calls must be positive')
    args.output.mkdir(parents=True,exist_ok=True)
    if args.mode == 'report':
        config=json.loads((args.output/'benchmark-session.json').read_text())
        if evaluator_digest()!=config['evaluator_sha256']: p.error('evaluator changed after primary comparison')
        rows=[json.loads(l) for l in (args.output/'metrics.jsonl').read_text().splitlines()]
        adjudications=validate_adjudications(rows,args.output/'adjudications.jsonl')
        report=compare(rows,cases=config['cases'],config=config,adjudications=adjudications)
        print(json.dumps(report,indent=2)); raise SystemExit(0 if report['decision']=='pass' else 1)
    if args.mode == 'holdout-report':
        primary=json.loads((args.output/'benchmark-session.json').read_text()); holdout=json.loads((args.output/'holdout-session.json').read_text()); rows=[json.loads(l) for l in (args.output/'metrics.jsonl').read_text().splitlines()]
        if evaluator_digest()!=primary['evaluator_sha256']: p.error('evaluator changed after primary comparison')
        adjudications=validate_adjudications(rows,args.output/'adjudications.jsonl'); report=evaluate_holdout(rows,holdout,primary,adjudications)
        print(json.dumps(report,indent=2)); raise SystemExit(0 if report['decision']=='pass' else 1)
    if args.mode == 'adjudication-template':
        rows=[json.loads(l) for l in (args.output/'metrics.jsonl').read_text().splitlines()]
        target=args.output/'adjudications.template.jsonl'
        target.write_text('\n'.join(json.dumps({'benchmark_session_id':row['benchmark_session_id'],'run_id':row['run_id'],'case_id':row['case_id'],'version':row['version'],'passed':False,'critical_failures':['REVIEW_REQUIRED'],'reviewer_id':'REPLACE_WITH_INDEPENDENT_REVIEWER_ID','reviewed_at':utc()}) for row in rows if row['case_id']!='format')+'\n')
        print(target); return
    if args.max_llm_calls is not None:
        result={'status':'blocked','blocked_reason':'budget_unobservable','message':'LLM request count is not exposed by the supported CLI event adapter.'}
        (args.output/'preflight.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
        raise SystemExit(2)
    cases = [args.case] if args.case else list(CASES)
    if args.mode == 'holdout':
        config=json.loads((args.output/'benchmark-session.json').read_text()); rows=[json.loads(l) for l in (args.output/'metrics.jsonl').read_text().splitlines()]; adjudications=validate_adjudications(rows,args.output/'adjudications.jsonl')
        if set(config['cases'])!=set(CASES): p.error('holdout requires a full primary comparison, not a scoped diagnostic')
        report=compare(rows,cases=config['cases'],config=config,adjudications=adjudications)
        if report['decision'] != 'pass': p.error('holdout requires a passing primary comparison')
        if digest(frozen_files('working'))!=config['pack_sha256']['working']: p.error('working pack changed after primary comparison')
        if evaluator_digest()!=config['evaluator_sha256']: p.error('evaluator changed after primary comparison')
        if args.model!=config['model'] or args.effort!=config['effort']: p.error('holdout model and effort must match primary comparison')
        if any(digest(HOLDOUT[case])!=expected for case,expected in config['holdout_case_sha256'].items()): p.error('holdout fixtures changed after primary comparison')
        cases=list(HOLDOUT)
    session_id=str(uuid.uuid4())
    if args.mode=='compare':
        args.output.mkdir(parents=True,exist_ok=True)
        config_path=args.output/'benchmark-session.json'
        if config_path.exists(): p.error('comparison output already contains a benchmark session; choose a new directory')
        config_path.write_text(json.dumps({'benchmark_session_id':session_id,'model':args.model,'effort':args.effort,'timeout':args.timeout,'cases':cases,'created_at':utc(),'evaluator_sha256':evaluator_digest(),'case_sha256':{case:digest(CASES[case]) for case in cases},'holdout_case_sha256':{case:digest(HOLDOUT[case]) for case in HOLDOUT},'pack_sha256':{ref:digest(frozen_files(ref)) for ref in ('v0.1.0','working')}},indent=2)+'\n')
    elif args.mode=='holdout':
        holdout_path=args.output/'holdout-session.json'
        if holdout_path.exists(): p.error('holdout already executed for this comparison directory')
        holdout_path.write_text(json.dumps({'benchmark_session_id':session_id,'model':args.model,'effort':args.effort,'created_at':utc(),'evaluator_sha256':config['evaluator_sha256'],'case_sha256':config['holdout_case_sha256'],'pack_sha256':{'working':config['pack_sha256']['working']}},indent=2)+'\n')
    tokens=0
    for n,case in enumerate(cases):
        for pair in range(3 if args.mode=='compare' else 1):
            refs=(['v0.1.0','working'] if (n+pair)%2==0 else ['working','v0.1.0']) if args.mode=='compare' else (['working'] if args.mode=='holdout' else ['v0.1.0'])
            for ref in refs:
                for attempt in range(3):
                    if args.max_total_tokens is not None and tokens >= args.max_total_tokens:
                        blocked={'status':'blocked','blocked_reason':'budget_exceeded','observed_tokens':tokens}; (args.output/'blocked.json').write_text(json.dumps(blocked,indent=2)+'\n'); print(json.dumps(blocked)); raise SystemExit(2)
                    row=run_case(case,ref,args.output,args.model,args.effort,args.timeout,'comparison' if args.mode=='compare' else args.mode,pair,session_id,attempt)
                    if row['input_tokens'] is not None and row['output_tokens'] is not None: tokens += row['input_tokens'] + row['output_tokens']
                    elif args.max_total_tokens is not None:
                        print(json.dumps({'status':'blocked','blocked_reason':'budget_unobservable'})); raise SystemExit(2)
                    if row['status']=='completed': break
                else:
                    blocked={'status':'blocked','blocked_reason':'external_dependency','message':'No valid run after two replacement attempts.'}; (args.output/'blocked.json').write_text(json.dumps(blocked,indent=2)+'\n'); print(json.dumps(blocked)); raise SystemExit(2)
    if args.mode=='holdout':
        rows=[json.loads(l) for l in (args.output/'metrics.jsonl').read_text().splitlines()]; adjudications=validate_adjudications(rows,args.output/'adjudications.jsonl'); report=evaluate_holdout(rows,json.loads((args.output/'holdout-session.json').read_text()),config,adjudications)
        print(json.dumps(report)); raise SystemExit(0 if report['decision']=='pass' else 1)


if __name__=='__main__': main()
