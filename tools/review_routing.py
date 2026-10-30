#!/usr/bin/env python3
"""Plan risk-based review without executing agents or claiming completed review."""

import argparse
import json
import math


TASK_KINDS = ('mechanical', 'implementation', 'research', 'statistical_design',
              'data_leakage', 'central_claim', 'external_fact', 'security_sensitive', 'unknown')
RISK_KINDS = ('research_conclusion', 'external_fact', 'statistical_design',
              'data_leakage', 'security_sensitive', 'job_claim',
              'implementation_change', 'central_claim', 'interpretation')
RESEARCH_KINDS = {'research', 'statistical_design', 'data_leakage', 'central_claim'}
RESEARCH_RISKS = {'research_conclusion', 'statistical_design', 'data_leakage',
                  'central_claim', 'interpretation'}


def _strings(value, name):
    if not isinstance(value, (list, tuple)) or any(
            not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(name + ' must be a list of nonempty strings')
    if len(set(value)) != len(value):
        raise ValueError(name + ' must not contain duplicate identities')
    return list(value)


def _budget_plan(budget):
    if budget is None:
        budget = {}
    if not isinstance(budget, dict):
        raise ValueError('budget must be an object')
    allowed = {'metric', 'limit', 'used', 'required', 'observable', 'retry_limit'}
    if set(budget) - allowed:
        raise ValueError('unknown budget fields: ' + ', '.join(sorted(set(budget) - allowed)))
    metric = budget.get('metric')
    if metric is not None and metric not in ('tokens', 'llm_calls'):
        raise ValueError('budget metric must be tokens or llm_calls; turns/tool counts are not proxies')
    if 'observable' in budget and not isinstance(budget['observable'], bool):
        raise ValueError('budget observable must be boolean')
    for key in ('limit', 'used', 'required'):
        value = budget.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or (isinstance(value,float) and not math.isfinite(value)) or value < 0):
            raise ValueError('budget ' + key + ' must be a finite nonnegative number')
        if metric == 'llm_calls' and value is not None and int(value) != value:
            raise ValueError('llm_calls budget values must be whole counts')
    retries = budget.get('retry_limit', 2)
    if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
        raise ValueError('retry_limit must be a nonnegative integer')
    # This planner never raises the default two-round repair/re-review cap.
    retries = min(2, retries)
    limit, used, required = (budget.get(k) for k in ('limit', 'used', 'required'))
    remaining = None
    if limit is None:
        status = 'not_constrained'
    elif metric is None or used is None or required is None or budget.get('observable') is False:
        status = 'unobservable'
    else:
        remaining = limit - used
        status = 'sufficient' if remaining >= required else 'insufficient'
    return {'status': status, 'metric': metric, 'limit': limit, 'used': used,
            'required': required, 'remaining': remaining,
            'observable': budget.get('observable', None), 'retry_limit': retries}


def route_review(*, task_kind='unknown', risks=None, mode='standard', assurance='standard',
                 requested_reviewers=None, available_reviewers=None, budget=None):
    """Return a deterministic JSON-compatible plan, never execution evidence.

    ``available_reviewers`` is an observed pool of independent reviewer identities,
    supplied by the caller. None means unknown; [] means known unavailable. The
    caller must exclude the implementer and identities that are not independent.
    ``requested_reviewers`` optionally names exact reviewers; [] cannot waive a
    mandatory reviewer. No reviewer is spawned and actual_reviewers stays empty.

    A hard budget needs metric, limit, used, required and observable usage. required
    is the caller's reservation estimate for the planned remaining work and review;
    an estimate is not a guarantee or a measured token count.
    """
    if task_kind not in TASK_KINDS:
        raise ValueError('invalid task_kind: ' + str(task_kind))
    if mode not in ('quick', 'standard', 'deep'):
        raise ValueError('invalid mode: ' + str(mode))
    if assurance not in ('standard', 'research_strict'):
        raise ValueError('invalid assurance: ' + str(assurance))
    if risks is None:
        risks = []
    if not isinstance(risks, (list, tuple)) or any(r not in RISK_KINDS for r in risks):
        raise ValueError('risks must be a list of supported risk names')
    risks = sorted(set(risks))
    requested = None if requested_reviewers is None else _strings(requested_reviewers, 'requested_reviewers')
    available = None if available_reviewers is None else _strings(available_reviewers, 'available_reviewers')
    budget_plan = _budget_plan(budget)

    strict = assurance == 'research_strict' or task_kind in RESEARCH_KINDS or bool(set(risks) & RESEARCH_RISKS)
    reasons = []
    if task_kind != 'mechanical':
        reasons.append('task_kind:' + task_kind)
    reasons.extend('risk:' + risk for risk in risks)
    if strict:
        reasons.append('assurance:research_strict')
    if requested:
        reasons.append('explicit_review_request')
    independent = bool(reasons)
    if not independent:
        reasons.append('mechanical_only')
    required_count = max(1, len(requested or [])) if independent else 0
    requested_display = (['independent_semantic_reviewer'] if independent else []) if requested is None else requested

    assigned = []
    if not independent:
        availability = 'not_required'
    elif available is None:
        availability = 'unknown'
    elif requested:
        assigned = [identity for identity in requested if identity in available]
        availability = 'available' if len(assigned) == required_count else 'unavailable'
    else:
        # Pool order is caller preference; preserve exact identities, no fabricated handles.
        assigned = available[:required_count]
        availability = 'available' if len(assigned) == required_count else 'unavailable'

    blocked = []
    if budget_plan['status'] == 'unobservable':
        blocked.append('budget_unobservable')
    elif budget_plan['status'] == 'insufficient':
        blocked.append('budget_exceeded')
    if independent and availability != 'available':
        blocked.append('resource_unavailable')
    actions = []
    if 'budget_unobservable' in blocked:
        actions.append('Obtain observed usage and a reservation estimate in the actual budget metric; do not substitute turns or tool counts.')
    if 'budget_exceeded' in blocked:
        actions.append('Reduce optional scope or revise the budget before proceeding; retain all mandatory integrity and review gates.')
    if 'resource_unavailable' in blocked:
        actions.append('Obtain an identifiable independent reviewer; attempt an unavailable spawn at most once and do not integrate pending review.')
    if independent:
        actions.append('Run requirements/scope review then mandatory integrity review; preserve each claim and artifact evidence mapping.')
    else:
        actions.append('Perform direct mechanical checks against the requested artifact before a completion claim.')

    return {
        'schema_version': '1.0', 'plan_only': True,
        'task_kind': task_kind, 'risks': risks, 'mode': mode,
        'assurance': 'research_strict' if strict else 'standard',
        'route': 'independent_semantic_review' if independent else 'single_agent',
        'status': 'blocked' if blocked else ('ready_for_review' if independent else 'ready_for_direct_checks'),
        'reasons': reasons, 'semantic_review_required': independent,
        'manifest_required': independent or strict, 'research_contract_required': strict,
        'required_reviewer_count': required_count,
        'requested_reviewers': requested_display, 'assigned_reviewers': assigned,
        'actual_reviewers': [], 'review_completed': False,
        'availability_status': availability, 'budget_status': budget_plan['status'],
        'budget': budget_plan, 'blocked_reason': blocked[0] if blocked else None,
        'blocked_reasons': blocked, 'next_actions': actions,
        'retry_limit': budget_plan['retry_limit'],
        'retry_guidance': 'Never retry unchanged blocked work. Stop on critical integrity failures; after at most the retry_limit repair/re-review rounds, retain unresolved findings and revise the plan. A smaller caller budget wins.',
        'limitations': [
            'Caller-supplied task, risks, reviewer independence and availability are not verified by this planner.',
            'Assigned identities are proposed assignments, not observed reviewer execution or passing review.',
            'Quick changes optional depth only; mandatory integrity checks, approvals and research gates remain.',
            'Budget reservations are estimates; runtime usage must be observed and enforced separately.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-kind', choices=TASK_KINDS, default='unknown')
    parser.add_argument('--risks', nargs='*', choices=RISK_KINDS, default=[])
    parser.add_argument('--mode', choices=('quick', 'standard', 'deep'), default='standard')
    parser.add_argument('--assurance', choices=('standard', 'research_strict'), default='standard')
    parser.add_argument('--requested-reviewers', nargs='*')
    parser.add_argument('--available-reviewers', nargs='*')
    parser.add_argument('--budget-json', help='JSON budget object; usage is never inferred from turns')
    args = vars(parser.parse_args(argv))
    raw_budget = args.pop('budget_json')
    try:
        args['budget'] = json.loads(raw_budget) if raw_budget is not None else None
        result = route_review(**args)
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 2 if result['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
