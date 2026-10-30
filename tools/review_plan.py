#!/usr/bin/env python3
"""Deterministic reading/output plan; this is not a scientific assessment."""
import argparse
import json


def plan(mode='standard', task='peer_review', field='', long=False, previous=False):
    if mode not in ('quick', 'standard', 'deep') or task not in ('audit','peer_review','defense','supervision'):
        raise ValueError('invalid mode or task')
    refs=['references/modes.md']
    invariants=['compute_before_numeric_claim','exact_evidence_locators','missing_evidence_is_not_error',
                'no_fabricated_execution','report_unread_scope','escalate_central_claim_risks']
    output=['coverage','prioritized_findings','correction_and_acceptance','limitations','next_actions']
    if task=='defense':
        refs+=['references/defense-and-feedback.md'];invariants+=['wait_for_answer']
    else:
        refs+=['references/assessment-rubric.md']
        if mode!='quick':refs+=['references/phase-expectations.md','references/output-template.md']
    # Field probes are selected, not universally loaded.
    probes={'材料':'materials-ml.md','生物':'bio-experimental.md','医学':'bio-experimental.md',
            '化学':'chemistry-synthesis.md','物理':'physics-engineering.md','工学':'physics-engineering.md',
            '地球':'field-observational.md','環境':'field-observational.md','情報':'simulation-theory.md'}
    chosen=[]
    for keyword,file in probes.items():
        if keyword in field and file not in chosen:chosen.append(file)
    refs+=['references/probes/'+f for f in chosen[:2]]
    if long:refs+=['references/long-manuscripts.md']
    if previous:refs+=['references/local-context-and-continuity.md']
    if task!='defense' and mode!='quick':refs+=['references/substantive-review.md']
    return dict(mode=mode,task=task,references=refs,required_output=output,invariants=invariants,
                cross_claim_check=True,scope='targeted' if mode=='quick' else 'whole_requested_scope',
                escalation='Expand scope for central-claim risk, dependency change or cross-chapter contradiction; report budget limits.')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['quick','standard','deep'],default='standard')
    p.add_argument('--task',choices=['audit','peer_review','defense','supervision'],default='peer_review')
    p.add_argument('--field',default='');p.add_argument('--long',action='store_true');p.add_argument('--previous',action='store_true')
    a=p.parse_args(argv);print(json.dumps(plan(**vars(a)),ensure_ascii=False,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
