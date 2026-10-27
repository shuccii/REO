"""Stateless manifest validation and dependency/write-scope queries."""
import json
from pathlib import Path, PurePosixPath

from schema_subset import audit_schema, validate

ROOT=Path(__file__).resolve().parents[1]
SEMANTIC_RISKS={'research_conclusion','external_fact','statistical_design','data_leakage','security_sensitive','job_claim','implementation_change'}
RESEARCH_RISKS={'research_conclusion','statistical_design','data_leakage'}

def load_manifest(path):
    return json.loads(Path(path).read_text())

def _schema_errors(manifest):
    schema=json.loads((ROOT/'assets/task-manifest.schema.json').read_text()); audit_schema(schema)
    return validate(manifest,schema)

def _clean_scope(scope):
    raw=scope['path']
    if '\\' in raw or any(char in raw for char in '*?[]{}') or raw.endswith('/'):
        raise ValueError('must be a normalized POSIX path without glob or trailing slash')
    path=PurePosixPath(raw)
    if path.is_absolute() or raw in ('','.','..') or '..' in path.parts or '.' in path.parts:
        raise ValueError('must be a normalized project-relative path')
    if str(path)!=raw: raise ValueError('must be normalized')
    return path

def _ancestors(tasks,task_id):
    by_id={task['task_id']:task for task in tasks}; seen=set(); stack=list(by_id[task_id]['depends_on'])
    while stack:
        current=stack.pop()
        if current in seen or current not in by_id: continue
        seen.add(current); stack += by_id[current]['depends_on']
    return seen

def detect_cycles(tasks):
    by_id={task['task_id']:task for task in tasks}; visiting=set(); done=set(); cycles=[]
    def visit(node,path):
        if node in visiting:
            cycles.append(path[path.index(node):]+[node]); return
        if node in done or node not in by_id: return
        visiting.add(node)
        for dep in by_id[node]['depends_on']: visit(dep,path+[dep])
        visiting.remove(node); done.add(node)
    for node in by_id: visit(node,[node])
    return cycles

def scopes_conflict(left,right):
    lp,rp=_clean_scope(left),_clean_scope(right)
    if lp==rp: return True
    if left['kind']=='tree' and len(lp.parts)<len(rp.parts) and rp.parts[:len(lp.parts)]==lp.parts: return True
    if right['kind']=='tree' and len(rp.parts)<len(lp.parts) and lp.parts[:len(rp.parts)]==rp.parts: return True
    return False

def detect_write_conflicts(tasks,candidates=None):
    selected=[task for task in tasks if candidates is None or task['task_id'] in candidates]; conflicts=[]
    for i,left in enumerate(selected):
        for right in selected[i+1:]:
            # Ordered writers are not simultaneous candidates.
            if left['task_id'] in _ancestors(tasks,right['task_id']) or right['task_id'] in _ancestors(tasks,left['task_id']): continue
            overlaps=[(a['path'],b['path']) for a in left['write_scope'] for b in right['write_scope'] if scopes_conflict(a,b)]
            if overlaps: conflicts.append({'left':left['task_id'],'right':right['task_id'],'paths':overlaps})
    return conflicts

def ready_tasks(manifest,completed_set,operation_succeeded_set=None):
    """Return dependency-ready tasks; approval nodes also need observed success."""
    completed=set(completed_set); succeeded=set(operation_succeeded_set or ()); by_id={task['task_id']:task for task in manifest['tasks']}
    def satisfied(dep): return dep in completed and (by_id[dep]['operation_class']!='approval_required' or dep in succeeded)
    return [task['task_id'] for task in manifest['tasks'] if task['task_id'] not in completed and all(satisfied(dep) for dep in task['depends_on'])]

def validate_manifest(manifest):
    errors=_schema_errors(manifest)
    if errors: return errors
    tasks=manifest['tasks']; ids=[task['task_id'] for task in tasks]; known=set(ids)
    contract=manifest['research_contract']
    if manifest['assurance_profile']=='research_strict':
        if not isinstance(contract,str) or not contract: errors.append('$.research_contract: research_strict requires a contract path')
        else:
            try: _clean_scope({'path':contract,'kind':'file'})
            except ValueError as exc: errors.append(f'$.research_contract: {exc}')
        if not any(set(task['risk_tags']) & RESEARCH_RISKS for task in tasks): errors.append('$.tasks: research_strict requires a research risk tag')
    else:
        if contract is not None: errors.append('$.research_contract: standard profile must use null')
        if any(set(task['risk_tags']) & RESEARCH_RISKS for task in tasks): errors.append('$.assurance_profile: research risk tags require research_strict')
    if len(ids)!=len(known): errors.append('$.tasks: duplicate task_id')
    for task in tasks:
        for dep in task['depends_on']:
            if dep not in known: errors.append(f'$.tasks.{task["task_id"]}: missing dependency {dep!r}')
        if task['parent_task_id'] is not None and task['parent_task_id'] not in known: errors.append(f'$.tasks.{task["task_id"]}: missing parent_task_id')
        if task['task_id'] in task['depends_on']: errors.append(f'$.tasks.{task["task_id"]}: self dependency')
        if set(task['risk_tags']) & SEMANTIC_RISKS and task['verification_mode']!='semantic_review_required': errors.append(f'$.tasks.{task["task_id"]}: risk_tags require semantic_review_required')
        if task['operation_class']=='read_only' and task['write_scope']: errors.append(f'$.tasks.{task["task_id"]}: read_only task has write scope')
        if task['operation_class']=='approval_required':
            if task['verification_mode']!='semantic_review_required': errors.append(f'$.tasks.{task["task_id"]}: approval_required requires semantic_review_required')
            if 'operation_success' not in task['required_checks']: errors.append(f'$.tasks.{task["task_id"]}: approval_required requires operation_success check')
        if len(task['required_checks'])!=len(set(task['required_checks'])): errors.append(f'$.tasks.{task["task_id"]}: duplicate required_checks')
        for scope in task['write_scope']:
            try: _clean_scope(scope)
            except ValueError as exc: errors.append(f'$.tasks.{task["task_id"]}.write_scope.{scope["path"]}: {exc}')
    for cycle in detect_cycles(tasks): errors.append('$.tasks: dependency cycle '+' -> '.join(cycle))
    return errors
