#!/usr/bin/env python3
"""Validate strict research evidence and reject common leakage/design failures."""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

from schema_subset import audit_schema, validate

ROOT=Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(Path(path).read_text())

def evidence_references(data):
    references=[data['evaluation']['raw_predictions_artifact'],data['data_quality']['missingness_artifact'],data['data_quality']['physical_constraints_artifact'],data['data_quality']['category_normalization_artifact']]
    references += [data['reproduction'][key] for key in ('split_artifact','environment_artifact','command_artifact')]
    references += [ref for gate in data['validation_gates'] for ref in gate['evidence_refs']]
    if data.get('optimization'): references += [data['optimization'][key] for key in ('objective_semantics_artifact','feature_alignment_artifact','feasibility_constraints_artifact','applicability_domain_artifact')]
    if data.get('novelty'): references.append(data['novelty']['evidence_artifact'])
    return set(filter(None,references))

def validate_research_contract(data, manifest=None, base_dir=None):
    schema=read(ROOT/'assets/research-contract.schema.json'); audit_schema(schema)
    errors=validate(data,schema)
    if errors: return errors
    if len(data['activities'])!=len(set(data['activities'])): errors.append('$.activities: duplicate activity')
    if manifest:
        if manifest.get('assurance_profile')!='research_strict': errors.append('$manifest.assurance_profile: contract requires research_strict')
        if data['run_id']!=manifest.get('run_id'): errors.append('$.run_id: differs from manifest')
    by_split=defaultdict(lambda: defaultdict(dict))
    for row in data['splits']:
        split=row['split_id']; sample=row['sample_id']; part=row['partition']; group=row['group_id']
        if sample in by_split[split]['samples']: errors.append(f'$.splits.{split}: sample {sample!r} assigned more than once')
        by_split[split]['samples'][sample]=part
        old=by_split[split]['groups'].get(group)
        if old and old!=part: errors.append(f'$.splits.{split}: group {group!r} crosses {old}/{part}')
        by_split[split]['groups'][group]=part
    for item in data['transforms']:
        split=item['split_id']; samples=by_split.get(split,{}).get('samples',{})
        if not samples: errors.append(f'$.transforms.{item["transform_id"]}: unknown split_id {split!r}'); continue
        leaked=[sample for sample in item['fit_sample_ids'] if samples.get(sample)!='train']
        unknown=[sample for sample in item['fit_sample_ids'] if sample not in samples]
        if leaked: errors.append(f'$.transforms.{item["transform_id"]}: fit includes non-train samples {sorted(leaked)}')
        if unknown: errors.append(f'$.transforms.{item["transform_id"]}: unknown fit samples {sorted(unknown)}')
        if item['kind']=='resampling':
            if item['output_partition']!='train': errors.append(f'$.transforms.{item["transform_id"]}: resampling output must remain in train')
            for synthetic in item['synthetic_samples']:
                bad=[parent for parent in synthetic['parent_sample_ids'] if samples.get(parent)!='train']
                if bad: errors.append(f'$.transforms.{item["transform_id"]}: synthetic parents are not all train samples')
        elif item['synthetic_samples']: errors.append(f'$.transforms.{item["transform_id"]}: synthetic samples allowed only for resampling')
    target=data['target']
    overlap=set(data['feature_columns']) & set(target['source_columns'])
    if overlap: errors.append(f'$.feature_columns: target/source columns cannot be model inputs {sorted(overlap)}')
    if target['data_derived']:
        if not target['fits']: errors.append('$.target.fits: data-derived target requires training-sample evidence')
        for fit in target['fits']:
            samples=by_split.get(fit['split_id'],{}).get('samples',{})
            if not samples: errors.append(f'$.target.fits: unknown split {fit["split_id"]!r}')
            leaked=[sample for sample in fit['fit_sample_ids'] if samples.get(sample)!='train']
            if leaked: errors.append(f'$.target.fits.{fit["split_id"]}: target construction includes non-train samples {sorted(leaked)}')
    elif target['fits']: errors.append('$.target.fits: non-derived target must not declare fits')
    for step in data['selection_steps']:
        if step['selected_using']=='test': errors.append(f'$.selection_steps.{step["name"]}: test data cannot select design')
    for item in data['transforms']:
        if item['kind']=='imputation':
            for key in ('imputation_fraction','stochastic','random_seed','consequential'):
                if key not in item: errors.append(f'$.transforms.{item["transform_id"]}.{key}: required for imputation')
            if item.get('stochastic') and item.get('random_seed') is None: errors.append(f'$.transforms.{item["transform_id"]}.random_seed: stochastic imputation requires a seed')
            if (item.get('consequential') or item.get('imputation_fraction',0)>=0.1) and data['data_quality']['sensitivity_analysis']!='passed':
                errors.append(f'$.transforms.{item["transform_id"]}: consequential imputation requires passed sensitivity analysis')
    evaluation=data['evaluation']
    predictive=bool({'predictive_modeling','interpretation','optimization','prospective_claim'} & set(data['activities']))
    if predictive:
        if evaluation['repeats']<2: errors.append('$.evaluation.repeats: predictive research requires repeated evaluation')
        if len(set(evaluation['seeds']))<2: errors.append('$.evaluation.seeds: predictive research requires at least two distinct seeds')
        if not evaluation['baseline_ids']: errors.append('$.evaluation.baseline_ids: predictive research requires a baseline')
        if not evaluation['raw_predictions_artifact']: errors.append('$.evaluation.raw_predictions_artifact: required for metric recomputation')
        if not evaluation['uncertainty_reported']: errors.append('$.evaluation.uncertainty_reported: required for predictive research')
        if data['data_quality']['sensitivity_analysis']=='not_run': errors.append('$.data_quality.sensitivity_analysis: unresolved sensitivity analysis cannot support predictive completion')
        for key in ('missingness_checked','physical_constraints_checked','category_normalization_checked'):
            if not data['data_quality'][key]: errors.append(f'$.data_quality.{key}: required for predictive research')
    if evaluation['test_access_purpose']=='selection': errors.append('$.evaluation.test_access_purpose: test data cannot be used for selection')
    if evaluation['test_access_count']>1: errors.append('$.evaluation.test_access_count: untouched test may be evaluated at most once')
    if evaluation['test_access_count']==0 and evaluation['test_access_purpose']!='not_accessed': errors.append('$.evaluation.test_access_purpose: inconsistent with access count')
    if evaluation['test_access_count']==1 and evaluation['test_access_purpose']!='final_evaluation': errors.append('$.evaluation.test_access_purpose: one access must be final evaluation')
    if data['claim_scope']=='causal' and 'prospective_claim' not in data['activities']:
        errors.append('$.claim_scope: causal claim requires prospective/interventional validation activity')
    if 'optimization' in data['activities']:
        opt=data.get('optimization')
        if not opt: errors.append('$.optimization: required for optimization activity')
        else:
            required=('objective_semantics_artifact','feature_alignment_artifact','feasibility_constraints_artifact','applicability_domain_artifact')
            for key in required:
                if not opt.get(key): errors.append(f'$.optimization.{key}: required')
            if opt['uses_ordinal_distance_on_nominal_labels']: errors.append('$.optimization: nominal label numbers cannot define ordinal distance')
    if 'prospective_claim' in data['activities']:
        novelty=data.get('novelty')
        if not novelty or not novelty.get('training_overlap_checked') or not novelty.get('prior_art_checked') or not novelty.get('evidence_artifact'):
            errors.append('$.novelty: prospective claim requires training-overlap and prior-art evidence')
        elif data['claim_scope']=='prospective' and novelty['status']!='prospectively_validated':
            errors.append('$.novelty.status: prospective result requires prospective validation')
    gates=data['validation_gates']; ids=[gate['gate_id'] for gate in gates]
    if len(ids)!=len(set(ids)): errors.append('$.validation_gates: duplicate gate_id')
    required_gates={'data_quality','reproducibility'}
    activities=set(data['activities'])
    if 'predictive_modeling' in activities: required_gates |= {'split_integrity','transform_fit_scope','target_validity','statistical_uncertainty','baseline'}
    if 'interpretation' in activities: required_gates |= {'interpretation_validity','model_dependence'}
    if 'optimization' in activities: required_gates |= {'optimization_objective','feature_alignment','feasibility','applicability_domain'}
    if 'prospective_claim' in activities: required_gates |= {'novelty','experimental_validation'}
    if 'reporting' in activities: required_gates.add('report_consistency')
    for missing in sorted(required_gates-set(ids)): errors.append(f'$.validation_gates: missing required gate {missing!r}')
    for gate in gates:
        if gate['status']=='passed' and not gate['evidence_refs']: errors.append(f'$.validation_gates.{gate["gate_id"]}: passed gate requires evidence')
        if gate['status']=='not_applicable' and len(gate['reason'].strip())<20: errors.append(f'$.validation_gates.{gate["gate_id"]}: not_applicable requires a substantive reason')
    gate_status={gate['gate_id']:gate['status'] for gate in gates}
    products=data['products']; product_status={product['artifact_id']:product['status'] for product in products}
    if len(product_status)!=len(products): errors.append('$.products: duplicate artifact_id')
    known=set(gate_status)|set(product_status)
    required_dependencies={
        'audit':set(),
        'metric':{'data_quality','split_integrity','transform_fit_scope','target_validity','statistical_uncertainty','baseline'},
        'model_ranking':{'split_integrity','transform_fit_scope','target_validity','statistical_uncertainty','baseline'},
        'interpretation':{'interpretation_validity','model_dependence'},
        'optimization':{'optimization_objective','feature_alignment','feasibility','applicability_domain'},
        'figure':set(),
        'claim':{'reproducibility'},
    }
    changed=True; invalid=set(key for key,value in gate_status.items() if value not in ('passed','not_applicable'))
    if invalid:
        invalid |= {product['artifact_id'] for product in products if product['kind']!='audit'}
    product_deps={product['artifact_id']:{dep for dep in product['depends_on'] if dep in product_status} for product in products}
    visiting=set(); visited=set()
    def visit(node):
        if node in visiting: return True
        if node in visited: return False
        visiting.add(node); cyclic=any(visit(dep) for dep in product_deps.get(node,set())); visiting.remove(node); visited.add(node); return cyclic
    if any(visit(node) for node in product_deps): errors.append('$.products: dependency cycle')
    while changed:
        changed=False
        for product in products:
            if product['artifact_id'] not in invalid and any(dep in invalid for dep in product['depends_on']): invalid.add(product['artifact_id']); changed=True
    for product in products:
        unknown=set(product['depends_on'])-known
        if unknown: errors.append(f'$.products.{product["artifact_id"]}: unknown dependencies {sorted(unknown)}')
        missing=required_dependencies[product['kind']]-set(product['depends_on'])
        if missing: errors.append(f'$.products.{product["artifact_id"]}: missing mandatory dependencies {sorted(missing)}')
        if product['artifact_id'] in invalid and product['status']!='invalidated': errors.append(f'$.products.{product["artifact_id"]}: must be invalidated by upstream failure')
        if product['artifact_id'] not in invalid and product['status']=='invalidated': errors.append(f'$.products.{product["artifact_id"]}: invalidated without failed dependency')
    if base_dir is not None:
        root=Path(base_dir).resolve()
        for reference in evidence_references(data):
            rel=Path(reference); candidate=root/rel
            cursor=root; has_symlink=False
            for part in rel.parts:
                cursor=cursor/part
                if cursor.is_symlink(): has_symlink=True
            try: safe=not rel.is_absolute() and '..' not in rel.parts and not has_symlink and candidate.resolve().is_relative_to(root) and candidate.exists()
            except (OSError,RuntimeError): safe=False
            if not safe: errors.append(f'$evidence: missing or unsafe artifact {reference!r}')
    return errors

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.add_argument('--manifest'); parser.add_argument('contracts',nargs='+'); args=parser.parse_args()
    manifest=read(args.manifest) if args.manifest else None; results=[]
    try:
        for contract in args.contracts:
            errors=validate_research_contract(read(contract),manifest,Path(contract).resolve().parent)
            results.append({'path':contract,'valid':not errors,'errors':errors})
    except Exception as exc:
        print(json.dumps({'internal_error':str(exc)}) if args.json else f'Validation error: {exc}',file=sys.stderr); raise SystemExit(2)
    output={'valid':all(item['valid'] for item in results),'results':results}
    print(json.dumps(output,indent=2) if args.json else '\n'.join(('VALID' if item['valid'] else 'INVALID')+': '+item['path']+'\n'+'\n'.join('  - '+e for e in item['errors']) for item in results))
    raise SystemExit(0 if output['valid'] else 1)

if __name__=='__main__': main()
