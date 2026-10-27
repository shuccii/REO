import copy, json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; FIX=Path(__file__).parent/'fixtures'; sys.path.insert(0,str(ROOT/'scripts'))
from validate_research_contract import validate_research_contract

def load(): return json.loads((FIX/'research-contract.valid.json').read_text())
def materialize(root,data):
    refs=[data['evaluation']['raw_predictions_artifact'],data['data_quality']['missingness_artifact'],data['data_quality']['physical_constraints_artifact'],data['data_quality']['category_normalization_artifact']]
    refs += [data['reproduction'][key] for key in ('split_artifact','environment_artifact','command_artifact')]
    refs += [ref for gate in data['validation_gates'] for ref in gate['evidence_refs']]
    for ref in set(refs):
        path=root/ref; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('{}')

class ResearchContractTests(unittest.TestCase):
    def test_valid_contract_and_cli(self):
        data=load(); self.assertEqual(validate_research_contract(data),[])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); contract=root/'research.json'; contract.write_text(json.dumps(data)); materialize(root,data)
            p=subprocess.run([sys.executable,str(ROOT/'scripts/validate_research_contract.py'),'--json',str(contract)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
    def test_group_leakage(self):
        data=load(); data['splits'][2]['group_id']='g1'; self.assertTrue(any('group' in e for e in validate_research_contract(data)))
    def test_preprocessing_fit_leakage(self):
        data=load(); data['transforms'][0]['fit_sample_ids'].append('s4'); self.assertTrue(any('non-train' in e for e in validate_research_contract(data)))
    def test_resampling_must_stay_in_train(self):
        data=load(); data['transforms'][1]['output_partition']='test'; self.assertTrue(any('resampling output' in e for e in validate_research_contract(data)))
    def test_synthetic_parent_must_be_train(self):
        data=load(); data['transforms'][1]['synthetic_samples'][0]['parent_sample_ids']=['s1','s4']; self.assertTrue(any('synthetic parents' in e for e in validate_research_contract(data)))
    def test_test_set_cannot_select_design(self):
        data=load(); data['selection_steps'][0]['selected_using']='test'; self.assertTrue(any('cannot select' in e for e in validate_research_contract(data)))
    def test_data_derived_target_must_fit_on_train_only(self):
        data=load(); data['target'].update(kind='cluster_label',data_derived=True,fits=[{'split_id':'outer-1','fit_sample_ids':['s1','s4']}])
        self.assertTrue(any('target construction includes non-train' in e for e in validate_research_contract(data)))
    def test_target_column_cannot_be_an_input_feature(self):
        data=load(); data['feature_columns'].append('strength_mpa')
        self.assertTrue(any('cannot be model inputs' in e for e in validate_research_contract(data)))
    def test_repeats_uncertainty_raw_predictions_and_baseline(self):
        data=load(); data['evaluation'].update(repeats=1,seeds=[1],baseline_ids=[],raw_predictions_artifact='',uncertainty_reported=False)
        errors=validate_research_contract(data); self.assertGreaterEqual(len(errors),5)
    def test_nominal_class_distance_rejected(self):
        data=load(); data['activities'].append('optimization'); data['optimization']={'objective_semantics_artifact':'objective.md','feature_alignment_artifact':'features.json','feasibility_constraints_artifact':'constraints.json','applicability_domain_artifact':'ood.json','uses_ordinal_distance_on_nominal_labels':True}
        self.assertTrue(any('nominal label' in e for e in validate_research_contract(data)))
    def test_prospective_claim_requires_novelty_and_validation(self):
        data=load(); data['activities'].append('prospective_claim'); data['claim_scope']='prospective'; data['novelty']={'training_overlap_checked':True,'prior_art_checked':True,'status':'unvalidated_prospective_candidate','evidence_artifact':'prior-art.md'}
        self.assertTrue(any('prospective validation' in e for e in validate_research_contract(data)))
    def test_not_applicable_requires_reason(self):
        data=load(); data['validation_gates'][0].update(status='not_applicable',reason='n/a',evidence_refs=[])
        self.assertTrue(any('substantive reason' in e for e in validate_research_contract(data)))
    def test_activity_requires_named_validity_gates(self):
        data=load(); data['validation_gates']=[gate for gate in data['validation_gates'] if gate['gate_id']!='split_integrity']
        self.assertTrue(any("'split_integrity'" in e for e in validate_research_contract(data)))
    def test_failed_gate_invalidates_downstream_products(self):
        data=load(); next(g for g in data['validation_gates'] if g['gate_id']=='split_integrity')['status']='failed'
        errors=validate_research_contract(data); self.assertTrue(any('metrics: must be invalidated' in e for e in errors))
        for product in data['products']: product['status']='invalidated'
        self.assertEqual(validate_research_contract(data),[])
    def test_failed_required_gate_invalidates_all_non_audit_products(self):
        data=load(); next(g for g in data['validation_gates'] if g['gate_id']=='split_integrity')['status']='failed'
        data['products'][0]['status']='invalidated'; data['products'][1]['depends_on']=['interpretation_validity','model_dependence']; data['products'][2]['depends_on']=['reproducibility']
        errors=validate_research_contract(data); self.assertTrue(any('explanation: must be invalidated' in e for e in errors)); self.assertTrue(any('conclusion: must be invalidated' in e for e in errors))
    def test_product_dependency_cycle_is_rejected(self):
        data=load(); data['products'][0]['depends_on'].append('conclusion')
        self.assertTrue(any('dependency cycle' in e for e in validate_research_contract(data)))
    def test_data_quality_checks_are_mandatory(self):
        data=load(); data['data_quality']['physical_constraints_checked']=False
        self.assertTrue(any('physical_constraints_checked' in e for e in validate_research_contract(data)))
    def test_consequential_imputation_requires_seed_and_sensitivity(self):
        data=load(); data['transforms'].append({'transform_id':'impute','split_id':'outer-1','kind':'imputation','fit_sample_ids':['s1','s2'],'output_partition':'train','synthetic_samples':[],'imputation_fraction':0.34,'stochastic':True,'random_seed':None,'consequential':True})
        errors=validate_research_contract(data); self.assertTrue(any('requires a seed' in e for e in errors)); self.assertTrue(any('requires passed sensitivity' in e for e in errors))
    def test_cli_rejects_missing_evidence_artifact(self):
        data=load()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); contract=root/'research.json'; contract.write_text(json.dumps(data))
            p=subprocess.run([sys.executable,str(ROOT/'scripts/validate_research_contract.py'),'--json',str(contract)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0); self.assertIn('missing or unsafe artifact',p.stdout)
    def test_cli_rejects_symlink_evidence(self):
        data=load()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); contract=root/'research.json'; contract.write_text(json.dumps(data)); materialize(root,data)
            target=root/'outside.json'; target.write_text('{}'); (root/'splits.json').unlink(); (root/'splits.json').symlink_to(target)
            p=subprocess.run([sys.executable,str(ROOT/'scripts/validate_research_contract.py'),'--json',str(contract)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0); self.assertIn('missing or unsafe artifact',p.stdout)

if __name__=='__main__': unittest.main()
