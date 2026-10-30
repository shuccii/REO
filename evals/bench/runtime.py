"""Reproducible run identities and observable usage (standard library only)."""
import hashlib
import json
from pathlib import Path


def digest(folder):
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(folder).rglob('*')) if p.is_file()}


def identity(folder,source,model,settings,prompt):
    payload={'inputs':digest(folder),'source':source,'model':model,'settings':settings,'prompt':prompt}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def reusable(meta,run_id):
    return meta.get('identity')==run_id and meta.get('exit')==0 and meta.get('completed') is True


def usage(events):
    result=next((e for e in reversed(events) if e.get('type')=='result'),{})
    u=result.get('usage') or {}
    keys = {'input_tokens': 'inputTokens', 'output_tokens': 'outputTokens',
            'cache_read_input_tokens': 'cacheReadInputTokens',
            'cache_creation_input_tokens': 'cacheCreationInputTokens', 'reasoning_tokens': 'reasoningTokens'}
    observed = {k: u.get(k) for k in keys}
    if observed['reasoning_tokens'] is None:
        observed['reasoning_tokens'] = (u.get('output_tokens_details') or {}).get('reasoning_tokens')
    models = list((result.get('modelUsage') or {}).values())
    for key, alias in keys.items():
        # Sum only a complete per-model observation, never interpret absence as zero.
        values = [m.get(alias) for m in models]
        if observed[key] is None and values and all(isinstance(v, (int, float)) for v in values):
            observed[key] = sum(values)
    return {**observed, 'cost_usd': result.get('total_cost_usd')}
