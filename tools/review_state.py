#!/usr/bin/env python3
"""Content-hashed dependency ledger for incremental review, not semantic approval."""
import hashlib
import json
from pathlib import Path


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def build(graph,workspace,context):
    root=Path(workspace).resolve();nodes={}
    if not isinstance(context,dict):raise ValueError('context must be an object')
    canonical(context)
    if not isinstance(graph,dict):raise ValueError('graph must be an object')
    if not isinstance(graph.get('nodes'),list):raise ValueError('nodes must be a list')
    for item in graph['nodes']:
        if not isinstance(item,dict):raise ValueError('each node must be an object')
        key=item.get('id');name=item.get('path')
        if not isinstance(key,str) or not key or key in nodes:raise ValueError('node IDs must be unique nonempty strings')
        if not isinstance(name,str) or not name:raise ValueError('node path required')
        path=(root/name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(root):raise ValueError('paths must remain inside workspace')
        deps=item.get('depends_on',[])
        if not isinstance(deps,list) or not all(isinstance(x,str) for x in deps):raise ValueError('depends_on must be a list of IDs')
        if path.exists() and not path.is_file():raise ValueError('node path must be a file')
        nodes[key]={'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
                    'depends_on':sorted(set(deps)),'always_review':bool(item.get('always_review',False))}
    visiting=set();visited=set()
    def visit(key):
        if key not in nodes:raise ValueError('unknown dependency: '+key)
        if key in visiting:raise ValueError('dependency cycle: '+key)
        if key in visited:return
        visiting.add(key)
        for dep in nodes[key]['depends_on']:visit(dep)
        visiting.remove(key);visited.add(key)
    for key in nodes:visit(key)
    return {'schema_version':1,'context':context,'context_hash':canonical(context),'nodes':nodes}


def validate(state):
    if not isinstance(state,dict):raise ValueError('state must be an object')
    if state.get('schema_version')!=1 or not isinstance(state.get('nodes'),dict):raise ValueError('invalid previous state')
    if state.get('context_hash')!=canonical(state.get('context')):raise ValueError('previous context hash mismatch')
    for key,n in state['nodes'].items():
        if not isinstance(n,dict) or not isinstance(n.get('depends_on'),list) or 'sha256' not in n:raise ValueError('invalid previous node: '+key)
        if any(d not in state['nodes'] for d in n['depends_on']):raise ValueError('unknown previous dependency')


def compare(previous,current):
    validate(current)
    if previous is not None:validate(previous)
    old=previous['nodes'] if previous else {};new=current['nodes']
    changed={k for k,n in new.items() if old.get(k)!=n}
    removed=set(old)-set(new);missing={k for k,n in new.items() if n['sha256'] is None}
    context_changed=previous is None or previous['context_hash']!=current['context_hash']
    invalid=set(new) if context_changed else changed|missing|removed
    # Follow old edges too: removing a dependency cannot make downstream evidence fresh.
    edges={k:set(new.get(k,{}).get('depends_on',[]))|set(old.get(k,{}).get('depends_on',[])) for k in set(new)|set(old)}
    while True:
        more={k for k,deps in edges.items() if deps&invalid}
        if more<=invalid:break
        invalid|=more
    always={k for k,n in new.items() if n['always_review']}
    return {'changed':sorted(changed),'removed':sorted(removed),'missing':sorted(missing),
            'context_changed':context_changed,'invalidated':sorted(invalid&set(new)),
            'always_recheck':sorted(always),'reusable_evidence':sorted(set(new)-invalid-always),
            'global_claim_consistency_required':True,'semantic_review_completed':False,
            'limitation':'Reuse is a candidate for unchanged deterministic evidence only; inspect evidence provenance and recheck abstract/conclusion. This ledger never certifies claims.'}
