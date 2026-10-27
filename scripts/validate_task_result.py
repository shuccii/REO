#!/usr/bin/env python3
"""Validate v0.3 results; older results are readable only as explicit archives."""
import argparse, json, sys
from datetime import datetime
from pathlib import Path
from schema_subset import audit_schema, validate

ROOT=Path(__file__).resolve().parents[1]
def read(path):
    def reject(value): raise ValueError(f'non-finite number {value!r} is not valid')
    try: return json.loads(Path(path).read_text(),parse_constant=reject)
    except (OSError,json.JSONDecodeError,ValueError) as exc: raise ValueError(str(exc)) from exc

def valid_legacy(data):
    required={'status':str,'summary':str,'artifacts':list,'evidence':list,'risks':list,'next_actions':list,'verification':dict}
    if not all(key in data and isinstance(data[key],typ) for key,typ in required.items()): return False
    if data['status'] not in {'completed','needs_revision','blocked','awaiting_approval'}: return False
    if not all(isinstance(item,str) for key in ('artifacts','evidence','risks','next_actions') for item in data[key]): return False
    return all(isinstance(data['verification'].get(key),str) and data['verification'][key].strip() for key in ('execution','validity'))

def check_one(path,schema,manifest,legacy):
    try: data=read(path)
    except ValueError as exc: return {'path':str(path),'valid':False,'archive_readable':False,'completion_eligible':False,'errors':[str(exc)]}
    if not isinstance(data,dict): return {'path':str(path),'valid':False,'archive_readable':False,'completion_eligible':False,'errors':['$: expected object']}
    if data.get('schema_version')=='0.2.0' and legacy:
        required=('run_id','task_id','status','summary','artifacts','evidence','risks','next_actions','verification')
        readable=all(key in data for key in required)
        return {'path':str(path),'valid':readable,'archive_readable':readable,'completion_eligible':False,'legacy_version':'0.2.0','errors':[] if readable else ['$: incomplete v0.2 archive result']}
    if 'schema_version' not in data:
        if legacy and valid_legacy(data): return {'path':str(path),'valid':True,'archive_readable':True,'completion_eligible':False,'legacy_version':'0.1','errors':[]}
        if legacy: return {'path':str(path),'valid':False,'archive_readable':False,'completion_eligible':False,'legacy_version':'0.1','errors':['$: does not satisfy the v0.1 archive shape']}
        return {'path':str(path),'valid':False,'archive_readable':False,'completion_eligible':False,'errors':['$: schema_version missing; --legacy-read-only is archive-only']}
    errors=validate(data,schema)
    if errors: return {'path':str(path),'valid':False,'archive_readable':False,'completion_eligible':False,'errors':errors}
    task=next((t for t in manifest['tasks'] if t['task_id']==data['task_id']),None) if manifest else None
    if manifest and task is None: errors.append('$.task_id: not found in manifest')
    if manifest and data['run_id']!=manifest['run_id']: errors.append('$.run_id: differs from manifest')
    if task and data['parent_task_id']!=task['parent_task_id']: errors.append('$.parent_task_id: differs from manifest')
    if datetime.fromisoformat(data['ended_at'][:-1]+'+00:00') < datetime.fromisoformat(data['started_at'][:-1]+'+00:00'): errors.append('$.ended_at: precedes started_at')
    if data['status']=='blocked' and 'blocked_reason' not in data: errors.append('$.blocked_reason: required for blocked')
    if data['status']!='blocked' and 'blocked_reason' in data: errors.append('$.blocked_reason: allowed only for blocked')
    verification=data['verification']; checks=verification['checks']; ids=[c['check_id'] for c in checks]
    if len(ids)!=len(set(ids)): errors.append('$.verification.checks: duplicate check_id')
    if len(verification['required_checks'])!=len(set(verification['required_checks'])): errors.append('$.verification.required_checks: duplicate check_id')
    evidence=set(data['evidence'])
    strict=bool(manifest and manifest.get('assurance_profile')=='research_strict')
    for check in checks:
        missing=set(check['evidence_refs'])-evidence
        if missing: errors.append(f'$.verification.checks.{check["check_id"]}: unknown evidence refs {sorted(missing)}')
        if check['type']=='command' and check['result']=='passed' and (not check.get('command') or check.get('exit_code')!=0): errors.append(f'$.verification.checks.{check["check_id"]}: passed command requires command and exit_code 0')
        if check['type']=='semantic_review' and check['observed_by']!='reviewer': errors.append(f'$.verification.checks.{check["check_id"]}: semantic review must be observed by reviewer')
    if strict and data['status'] in ('completed','needs_revision'):
        required_fields=('research_validation','claim_evidence_map','invalidated_artifacts','reproduction_bundle','review_scope','review_findings')
        for field in required_fields:
            if field not in data: errors.append(f'$.{field}: required by research_strict')
        bundle=data.get('reproduction_bundle')
        if not bundle or bundle not in data.get('artifacts',[]): errors.append('$.reproduction_bundle: strict research requires a declared bundle artifact')
        else:
            result_root=Path(path).resolve().parent; rel=Path(bundle); candidate=result_root/rel; cursor=result_root; has_symlink=False
            for part in rel.parts:
                cursor=cursor/part
                if cursor.is_symlink(): has_symlink=True
            try: safe=not rel.is_absolute() and '..' not in rel.parts and not has_symlink and candidate.resolve().is_relative_to(result_root) and candidate.exists()
            except (OSError,RuntimeError): safe=False
            if not safe: errors.append('$.reproduction_bundle: missing or unsafe artifact')
        gates=data.get('research_validation',[])
        gate_ids=[gate.get('gate_id') for gate in gates]
        if len(gate_ids)!=len(set(gate_ids)): errors.append('$.research_validation: duplicate gate_id')
        for gate in gates:
            missing=set(gate.get('evidence_refs',[]))-evidence
            if missing: errors.append(f'$.research_validation.{gate.get("gate_id")}: unknown evidence refs {sorted(missing)}')
            if gate.get('status')=='passed' and not gate.get('evidence_refs'): errors.append(f'$.research_validation.{gate.get("gate_id")}: passed gate requires evidence')
            if gate.get('status')=='not_applicable' and len(gate.get('reason','').strip())<20: errors.append(f'$.research_validation.{gate.get("gate_id")}: not_applicable requires a substantive reason')
        for claim in data.get('claim_evidence_map',[]):
            if claim.get('status')=='supported' and not claim.get('evidence_refs'): errors.append(f'$.claim_evidence_map.{claim.get("claim_id")}: supported claim requires evidence')
            missing=set(claim.get('evidence_refs',[]))-evidence
            if missing: errors.append(f'$.claim_evidence_map.{claim.get("claim_id")}: unknown evidence refs {sorted(missing)}')
        review=verification['validity_review']; reviewer=review.get('reviewer_id'); worker=data.get('worker_id')
        if not worker: errors.append('$.worker_id: strict reviewed result requires an observed worker identity')
        if not review['required'] or review['status']!='passed' or not reviewer: errors.append('$.verification.validity_review: strict result requires a passed independent review')
        if worker and reviewer==worker: errors.append('$.verification.validity_review: reviewer equals worker')
        semantic=[check for check in checks if check['type']=='semantic_review' and check['result']=='passed' and check['observed_by']=='reviewer']
        if not semantic or any(check.get('observer_id')!=reviewer for check in semantic): errors.append('$.verification.checks: strict result requires a matching reviewer-observed semantic check')
        result_root=Path(path).resolve().parent
        for artifact in data['artifacts']:
            rel=Path(artifact); candidate=result_root/rel; cursor=result_root; has_symlink=False
            for part in rel.parts:
                cursor=cursor/part
                if cursor.is_symlink(): has_symlink=True
            try: safe=not rel.is_absolute() and '..' not in rel.parts and not has_symlink and candidate.resolve().is_relative_to(result_root) and candidate.exists()
            except (OSError,RuntimeError): safe=False
            if not safe: errors.append(f'$.artifacts: missing or unsafe strict artifact {artifact!r}')
    required=task['required_checks'] if task else verification['required_checks']
    if task and verification['required_checks']!=required: errors.append('$.verification.required_checks: differs from manifest')
    by_id={c['check_id']:c for c in checks}
    if task:
        policy=read(ROOT/'assets/verification-policy.json')['modes'][task['verification_mode']]
        for check_id in required:
            if check_id in by_id:
                check=by_id[check_id]
                if check['type'] not in policy['allowed_check_types'] or check['observed_by'] not in policy['allowed_observers']:
                    errors.append(f'$.verification.checks.{check_id}: check type/observer violates verification policy')
        approval=data['approval']; is_approval=task['operation_class']=='approval_required'
        if approval['required']!=is_approval: errors.append('$.approval.required: differs from operation_class')
        if not is_approval and approval != {'required':False,'status':'not_required','approved_by':None,'operation_succeeded':False}: errors.append('$.approval: non-approval task must use the not_required state')
        if not is_approval and data['status']=='awaiting_approval': errors.append('$.status: awaiting_approval requires approval_required operation_class')
        if is_approval:
            if approval['status'] not in {'pending','approved'}: errors.append('$.approval.status: approval task must be pending or approved')
            if approval['status']=='pending' and (approval['approved_by'] is not None or approval['operation_succeeded']): errors.append('$.approval: pending state cannot have approval or operation success')
            if approval['status']=='approved' and approval['approved_by']!='user': errors.append('$.approval: approved state requires approved_by user')
            if approval['operation_succeeded'] and approval['status']!='approved': errors.append('$.approval: operation success requires approved state')
            if data['status']=='awaiting_approval' and approval!={'required':True,'status':'pending','approved_by':None,'operation_succeeded':False}: errors.append('$.approval: awaiting_approval requires the pending state')
            operation=by_id.get('operation_success')
            special=read(ROOT/'assets/verification-policy.json')['approval_operation_success']
            if not operation or operation['type'] not in special['allowed_check_types'] or operation['observed_by'] not in special['allowed_observers']:
                errors.append('$.verification.checks.operation_success: violates approval success policy')
            elif approval['operation_succeeded'] != (operation['result']=='passed'):
                errors.append('$.approval.operation_succeeded: must agree with the operation_success check result')
    if data['status']=='completed':
        if not data['evidence']: errors.append('$.evidence: completed requires evidence')
        for check_id in required:
            if check_id not in by_id: errors.append(f'$.verification.checks: missing required check {check_id!r}')
            elif by_id[check_id]['result']!='passed': errors.append(f'$.verification.checks.{check_id}: required check did not pass')
        if task is None: errors.append('$: completed result requires --manifest for integration eligibility')
        if strict:
            if not data.get('research_validation'): errors.append('$.research_validation: completed strict research requires gates')
            elif any(gate['status']!='passed' for gate in data['research_validation']): errors.append('$.research_validation: completed strict research requires every declared gate to pass')
            if not data.get('claim_evidence_map'): errors.append('$.claim_evidence_map: completed strict research requires claim evidence')
            if any(claim['status']=='invalidated' for claim in data.get('claim_evidence_map',[])): errors.append('$.claim_evidence_map: completed result contains invalidated claims')
            if not data.get('reproduction_bundle'): errors.append('$.reproduction_bundle: completed strict research requires a bundle')
            elif data['reproduction_bundle'] not in data['artifacts']: errors.append('$.reproduction_bundle: must name a declared artifact')
            expected={'design','data','execution','numerical_results','interpretation','claims','reproducibility'}
            if set(data.get('review_scope',[]))!=expected: errors.append('$.review_scope: completed strict research requires full independent review scope')
        if task and task['verification_mode']=='semantic_review_required':
            review=verification['validity_review']
            if not data.get('worker_id'): errors.append('$.worker_id: required to establish independent semantic review')
            if not review['required'] or review['status']!='passed' or not review['reviewer_id']: errors.append('$.verification.validity_review: independent passed review required')
            if data.get('worker_id') and review['reviewer_id']==data['worker_id']: errors.append('$.verification.validity_review: reviewer equals worker')
            semantic=[by_id[check_id] for check_id in required if check_id in by_id and by_id[check_id]['type']=='semantic_review']
            if not semantic: errors.append('$.verification.required_checks: semantic mode requires a reviewer-observed semantic_review check')
            elif any(check.get('observer_id')!=review['reviewer_id'] for check in semantic): errors.append('$.verification.checks: semantic observer_id must match reviewer_id')
        elif verification['validity_review']['required'] and verification['validity_review']['status']!='passed': errors.append('$.verification.validity_review: required review did not pass')
        if task and task['operation_class']=='approval_required':
            if data['approval']!={'required':True,'status':'approved','approved_by':'user','operation_succeeded':True}: errors.append('$.approval: completed approval operation requires user approval and observed operation success')
        result_dir=Path(path).resolve().parent
        for artifact in data['artifacts']:
            rel=Path(artifact)
            candidate=result_dir/rel
            has_symlink=False; cursor=result_dir
            for part in rel.parts:
                cursor=cursor/part
                if cursor.is_symlink(): has_symlink=True
            try: contained=candidate.resolve().is_relative_to(result_dir)
            except (OSError,RuntimeError): contained=False
            if rel.is_absolute() or '..' in rel.parts or has_symlink or not contained or not candidate.exists(): errors.append(f'$.artifacts: missing or unsafe artifact {artifact!r}')
    return {'path':str(path),'valid':not errors,'archive_readable':not errors,'completion_eligible':not errors and data['status']=='completed' and task is not None,'errors':errors}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--json',action='store_true'); p.add_argument('--legacy-read-only',action='store_true',help='read v0.1/v0.2 history without integration eligibility'); p.add_argument('--manifest'); p.add_argument('results',nargs='+'); args=p.parse_args()
    try:
        schema=read(ROOT/'assets/task-result.schema.json'); audit_schema(schema); manifest=read(args.manifest) if args.manifest else None
        if manifest:
            from manifest_helper import validate_manifest
            errs=validate_manifest(manifest)
            if errs: raise ValueError('invalid manifest: '+'; '.join(errs))
        results=[check_one(path,schema,manifest,args.legacy_read_only) for path in args.results]
        reviewed_status_present=False
        for path in args.results:
            try: reviewed_status_present |= read(path).get('status') in ('completed','needs_revision')
            except (ValueError,AttributeError): pass
        if manifest and manifest.get('assurance_profile')=='research_strict' and reviewed_status_present:
            from validate_research_contract import evidence_references, validate_research_contract
            contract_errors=[]
            try:
                manifest_root=Path(args.manifest).resolve().parent; contract_path=manifest_root/manifest['research_contract']
                if contract_path.is_symlink() or not contract_path.resolve().is_relative_to(manifest_root): raise ValueError('unsafe research contract path')
                contract=read(contract_path)
                contract_errors=validate_research_contract(contract,manifest,contract_path.parent)
            except Exception as exc:
                contract_errors=[f'$research_contract: {exc}']
            if contract_errors:
                for result in results:
                    result['errors'] += contract_errors
                    result['valid']=False; result['completion_eligible']=False
            else:
                expected={gate['gate_id']:gate['status'] for gate in contract['validation_gates']}
                for result,path in zip(results,args.results):
                    data=read(path)
                    if data.get('status') not in ('completed','needs_revision'): continue
                    actual={gate['gate_id']:gate['status'] for gate in data.get('research_validation',[])}
                    if actual!=expected:
                        result['errors'].append('$.research_validation: must match research contract gates and statuses')
                        result['valid']=False; result['completion_eligible']=False
                    required_evidence=evidence_references(contract)
                    missing=required_evidence-set(data.get('evidence',[]))
                    if missing:
                        result['errors'].append(f'$.evidence: missing research-contract evidence {sorted(missing)}')
                        result['valid']=False; result['completion_eligible']=False
                    invalidated={product['artifact_id'] for product in contract['products'] if product['status']=='invalidated'}
                    if set(data.get('invalidated_artifacts',[]))!=invalidated:
                        result['errors'].append('$.invalidated_artifacts: must match invalidated contract products')
                        result['valid']=False; result['completion_eligible']=False
    except Exception as exc:
        print(json.dumps({'internal_error':str(exc)}) if args.json else f'Validation error: {exc}',file=sys.stderr); raise SystemExit(2)
    output={'valid':all(r['valid'] for r in results),'results':results}
    if args.json: print(json.dumps(output,indent=2))
    else:
        for r in results:
            print(('VALID' if r['valid'] else 'INVALID')+f': {r["path"]}')
            for error in r['errors']: print('  - '+error)
    raise SystemExit(0 if output['valid'] else 1)
if __name__=='__main__': main()
