#!/usr/bin/env python3
"""Check report evidence bookkeeping, never scientific truth or faculty identity.

Locators are inert strings: this validator never opens evidence files, contacts
URLs, follows links, or verifies the contents of an asserted source.
"""
import argparse
import json
import sys
from pathlib import Path

from schema_subset import audit_schema, validate

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = (
    'question_significance', 'novelty_literature', 'logic_claims',
    'design_identifiability', 'data_measurement', 'statistics_uncertainty',
    'domain_validity', 'reproducibility', 'communication_defense',
    'ethics_governance',
)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_research_review(data):
    schema = read(ROOT / 'assets/research-review.schema.json')
    audit_schema(schema)
    errors = validate(data, schema)
    if errors:
        return errors

    def index(rows, key, label):
        result = {}
        for row in rows:
            value = row[key]
            if value in result:
                errors.append(f'$.{label}: duplicate {key} {value!r}')
            result[value] = row
        return result

    sources = index(data['sources'], 'source_id', 'sources')
    claims = index(data['claims'], 'claim_id', 'claims')
    findings = index(data['findings'], 'finding_id', 'findings')
    coverage = index(data['coverage'], 'dimension', 'coverage')
    # IDs are globally unique so a reference cannot silently resolve to a
    # different entity type after an editing mistake.
    all_ids = list(sources) + list(claims) + list(findings)
    if len(all_ids) != len(set(all_ids)):
        errors.append('$: source, claim and finding IDs must be globally unique')
    for missing in sorted(set(DIMENSIONS) - set(coverage)):
        errors.append(f'$.coverage: missing dimension {missing!r}')

    def references(refs, known, path, evidence=False):
        if len(refs) != len(set(refs)):
            errors.append(f'{path}: duplicate references')
        for reference in refs:
            if reference not in known:
                errors.append(f'{path}: unknown reference {reference!r}')
            elif evidence and known[reference]['status'] == 'unavailable':
                errors.append(f'{path}: unavailable source cannot be evidence {reference!r}')
        # A source locator is required and nonblank by schema. Interpretation
        # of page/line/section specificity requires a human or research reviewer.

    for source in data['sources']:
        if source['status'] in ('partial', 'unavailable') and not source['limitations']:
            errors.append(f'$.sources.{source["source_id"]}: partial/unavailable source requires limitations')
    for claim in data['claims']:
        path = f'$.claims.{claim["claim_id"]}'
        references(claim['evidence_refs'], sources, path + '.evidence_refs', True)
        if claim['status'] in ('supported', 'limited', 'invalidated') and not claim['evidence_refs']:
            errors.append(path + ': assessed supported/limited/invalidated claim requires evidence')
        if claim['status'] == 'limited' and not claim['material_limitations']:
            errors.append(path + ': limited claim requires material limitations')
        partial = any(sources.get(ref, {}).get('status') == 'partial' for ref in claim['evidence_refs'])
        if claim['status'] == 'supported' and partial and not any(sources.get(ref, {}).get('status') == 'read' for ref in claim['evidence_refs']):
            errors.append(path + ': partial-only evidence requires limited claim status')
    for item in data['coverage']:
        path = f'$.coverage.{item["dimension"]}'
        references(item['evidence_refs'], sources, path + '.evidence_refs', True)
        if item['status'] == 'assessed' and not item['evidence_refs']:
            errors.append(path + ': assessed dimension requires evidence')
        if item['status'] == 'not_applicable' and len(item['reason'].strip()) < 20:
            errors.append(path + ': not_applicable requires a substantive scope-specific reason')
    for finding in data['findings']:
        path = f'$.findings.{finding["finding_id"]}'
        references(finding['affected_claims'], claims, path + '.affected_claims')
        references(finding['evidence_refs'], sources, path + '.evidence_refs', True)
        references(finding['resolution_evidence_refs'], sources, path + '.resolution_evidence_refs', True)
        if finding['state'] == 'confirmed' and not finding['evidence_refs']:
            errors.append(path + ': confirmed finding requires evidence')
        if finding['resolution'] == 'resolved' and not finding['resolution_evidence_refs']:
            errors.append(path + ': resolved finding requires resolution evidence')
        if finding['resolution'] == 'resolved':
            original_refs = set(finding['evidence_refs'])
            original_locators = {sources[ref]['locator'] for ref in original_refs if ref in sources}
            fresh = [sources[ref] for ref in finding['resolution_evidence_refs']
                     if ref in sources and ref not in original_refs
                     and sources[ref]['locator'] not in original_locators
                     and sources[ref]['status'] == 'read']
            if not fresh:
                errors.append(path + ': resolution requires a distinct read source ID and new locator/version')
        if finding['resolution'] == 'open' and finding['resolution_evidence_refs']:
            errors.append(path + ': open finding cannot assert resolution evidence')
    for number, question in enumerate(data['questions']):
        references([question['claim_id']], claims, f'$.questions[{number}].claim_id')
    for number, issue in enumerate(data['unresolved']):
        references(issue['affected_claims'], claims, f'$.unresolved[{number}].affected_claims')
    for number, action in enumerate(data['next_actions']):
        references(action['related_findings'], findings, f'$.next_actions[{number}].related_findings')
    approval = data['faculty_approval']
    references(approval['evidence_refs'], sources, '$.faculty_approval.evidence_refs', True)
    if approval['status'] == 'confirmed' and not approval['evidence_refs']:
        errors.append('$.faculty_approval: confirmed approval requires evidence')
    if approval['status'] == 'confirmed' and not any(sources.get(ref, {}).get('status') == 'read' for ref in approval['evidence_refs']):
        errors.append('$.faculty_approval: confirmed approval requires at least one read source')
    if approval['status'] == 'not_assessed' and approval['evidence_refs']:
        errors.append('$.faculty_approval: not_assessed cannot assert approval evidence')

    if data['readiness'] == 'ready_within_scope':
        if any(f['severity'] in ('critical', 'major') and f['resolution'] == 'open' for f in data['findings']):
            errors.append('$.readiness: ready is blocked by open critical/major findings, including suspected findings')
        if any(item['status'] == 'not_assessed' for item in data['coverage']):
            errors.append('$.readiness: ready requires all dimensions assessed or justified not_applicable')
        if any(claim['status'] not in ('supported', 'limited') for claim in data['claims']):
            errors.append('$.readiness: ready requires every claim supported or materially limited')
        if any(issue['impact'] == 'material' for issue in data['unresolved']):
            errors.append('$.readiness: ready is blocked by material unresolved issues')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('reports', nargs='+')
    args = parser.parse_args()
    results = []
    try:
        for report in args.reports:
            try:
                data = read(report)
            except json.JSONDecodeError as exc:
                errors = [f'$: invalid JSON: {exc}']
            else:
                errors = validate_research_review(data)
            results.append({'path': report, 'contract_valid': not errors,
                            'scientific_validity': 'not_established', 'errors': errors})
    except (OSError, ValueError, TypeError, KeyError) as exc:
        output = {'contract_valid': False, 'scientific_validity': 'not_established', 'invocation_error': str(exc)}
        print(json.dumps(output) if args.json else f'Invocation error: {exc}', file=sys.stderr)
        return 2
    output = {'contract_valid': all(item['contract_valid'] for item in results),
              'scientific_validity': 'not_established', 'results': results}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for item in results:
            print(f'contract_valid={str(item["contract_valid"]).lower()} scientific_validity=not_established: {item["path"]}')
            for error in item['errors']:
                print('  - ' + error)
    return 0 if output['contract_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
