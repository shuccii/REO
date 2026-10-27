import copy, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; SCRIPTS=ROOT/'scripts'; FIX=Path(__file__).parent/'fixtures'
sys.path.insert(0,str(SCRIPTS))
from manifest_helper import detect_write_conflicts, ready_tasks, validate_manifest
from schema_subset import audit_schema

def load(name): return json.loads((FIX/name).read_text())
def run_result(data,manifest=True,legacy=False):
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'result.json'; p.write_text(json.dumps(data))
        (Path(d)/'out.json').write_text('{}')
        cmd=[sys.executable,str(SCRIPTS/'validate_task_result.py'),'--json']
        if legacy: cmd.append('--legacy-read-only')
        if manifest: cmd += ['--manifest',str(FIX/'manifest.valid.json')]
        cmd.append(str(p)); return subprocess.run(cmd,capture_output=True,text=True)

class ContractTests(unittest.TestCase):
    def setUp(self): self.valid=load('result.completed.valid.json')
    def test_valid_examples_and_batch(self):
        p=subprocess.run([sys.executable,str(SCRIPTS/'validate_task_result.py'),'--json','--manifest',str(FIX/'manifest.valid.json'),str(FIX/'result.completed.valid.json'),str(FIX/'result.needs-revision.valid.json')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr+p.stdout); self.assertEqual(len(json.loads(p.stdout)['results']),2)
    def test_reject_non_string_artifact(self): self.assertNotEqual(run_result({**self.valid,'artifacts':[1]}).returncode,0)
    def test_reject_empty_evidence_completed(self): self.assertNotEqual(run_result({**self.valid,'evidence':[]}).returncode,0)
    def test_reject_missing_required_check(self):
        d=copy.deepcopy(self.valid); d['verification']['checks']=[]; self.assertNotEqual(run_result(d).returncode,0)
    def test_reject_failed_required_check(self):
        d=copy.deepcopy(self.valid); d['verification']['checks'][0]['result']='failed'; self.assertNotEqual(run_result(d).returncode,0)
    def test_reject_status_version_id_and_time(self):
        for key,value in [('status','wrong'),('schema_version','0.1.0'),('task_id','bad id'),('ended_at','2025-09-02T00:00:01Z')]:
            with self.subTest(key=key): self.assertNotEqual(run_result({**self.valid,key:value}).returncode,0)
    def test_self_review_rejected(self):
        d=copy.deepcopy(self.valid); d['task_id']='review'; d['worker_id']='same'; d['verification']['required_checks']=['review']; d['verification']['checks'][0].update(check_id='review',type='semantic_review'); d['verification']['validity_review']={'required':True,'status':'passed','reviewer_id':'same'}
        self.assertNotEqual(run_result(d).returncode,0)
    def test_semantic_review_requires_worker_identity(self):
        d=copy.deepcopy(self.valid); d['task_id']='review'; d['parent_task_id']='format'; d.pop('worker_id'); d['verification']['required_checks']=['review']; d['verification']['checks'][0].update(check_id='review',type='semantic_review',observed_by='reviewer'); d['verification']['validity_review']={'required':True,'status':'passed','reviewer_id':'reviewer'}
        p=run_result(d); self.assertNotEqual(p.returncode,0); self.assertIn('worker_id',p.stdout)
    def test_semantic_review_requires_observed_check(self):
        d=copy.deepcopy(self.valid); d['task_id']='review'; d['parent_task_id']='format'; d['verification']['required_checks']=['review']; d['verification']['checks'][0].update(check_id='review',type='schema',observed_by='harness'); d['verification']['validity_review']={'required':True,'status':'passed','reviewer_id':'reviewer'}
        p=run_result(d); self.assertNotEqual(p.returncode,0); self.assertIn('semantic mode requires',p.stdout)
    def test_symlink_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            outside=Path(d).parent/'rdo-outside'; outside.write_text('x'); result=Path(d)/'result.json'; (Path(d)/'out.json').symlink_to(outside); result.write_text(json.dumps(self.valid))
            try:
                p=subprocess.run([sys.executable,str(SCRIPTS/'validate_task_result.py'),'--manifest',str(FIX/'manifest.valid.json'),str(result)],capture_output=True,text=True)
                self.assertNotEqual(p.returncode,0); self.assertIn('unsafe artifact',p.stdout)
            finally: outside.unlink(missing_ok=True)
    def test_nonfinite_json_is_validation_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'result.json'; path.write_text('{"value": NaN}')
            p=subprocess.run([sys.executable,str(SCRIPTS/'validate_task_result.py'),'--json',str(path)],capture_output=True,text=True)
            self.assertEqual(p.returncode,1); self.assertIn('non-finite',p.stdout)
    def test_approval_state_table_rejects_not_required(self):
        d=copy.deepcopy(self.valid); d['task_id']='format'; d['status']='blocked'; d['blocked_reason']='external_dependency'; d['approval']={'required':True,'status':'not_required','approved_by':'user','operation_succeeded':False}
        manifest=copy.deepcopy(load('manifest.valid.json')); manifest['tasks'][0].update(operation_class='approval_required',verification_mode='semantic_review_required',required_checks=['operation_success'])
        with tempfile.TemporaryDirectory() as directory:
            rp=Path(directory)/'result.json'; mp=Path(directory)/'manifest.json'; rp.write_text(json.dumps(d)); mp.write_text(json.dumps(manifest))
            p=subprocess.run([sys.executable,str(SCRIPTS/'validate_task_result.py'),'--json','--manifest',str(mp),str(rp)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0); self.assertIn('pending or approved',p.stdout)
    def test_approval_operation_boolean_matches_check(self):
        d=copy.deepcopy(self.valid); d['status']='blocked'; d['blocked_reason']='external_dependency'; d['approval']={'required':True,'status':'approved','approved_by':'user','operation_succeeded':True}; d['verification']['required_checks']=['operation_success']; d['verification']['checks'][0].update(check_id='operation_success',type='file_exists',result='failed',observed_by='harness')
        manifest=copy.deepcopy(load('manifest.valid.json')); manifest['tasks'][0].update(operation_class='approval_required',verification_mode='semantic_review_required',required_checks=['operation_success'])
        with tempfile.TemporaryDirectory() as directory:
            rp=Path(directory)/'result.json'; mp=Path(directory)/'manifest.json'; rp.write_text(json.dumps(d)); mp.write_text(json.dumps(manifest))
            p=subprocess.run([sys.executable,str(SCRIPTS/'validate_task_result.py'),'--json','--manifest',str(mp),str(rp)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0); self.assertIn('must agree',p.stdout)
    def test_legacy_is_explicit_and_archive_only(self):
        data=load('result.legacy.json'); self.assertNotEqual(run_result(data,manifest=False).returncode,0)
        p=run_result(data,manifest=False,legacy=True); self.assertEqual(p.returncode,0); self.assertFalse(json.loads(p.stdout)['results'][0]['completion_eligible'])
        self.assertNotEqual(run_result({},manifest=False,legacy=True).returncode,0)
        old=copy.deepcopy(self.valid); old['schema_version']='0.2.0'
        p=run_result(old,manifest=False,legacy=True); self.assertEqual(p.returncode,0); self.assertFalse(json.loads(p.stdout)['results'][0]['completion_eligible'])
    def test_completed_without_manifest_not_eligible(self): self.assertNotEqual(run_result(self.valid,manifest=False).returncode,0)
    def test_unknown_schema_keyword_fails_closed(self):
        with self.assertRaises(ValueError): audit_schema({'type':'string','maxLength':2})
    def test_strict_research_result_requires_traceable_validity(self):
        manifest={
            'schema_version':'0.3.0','run_id':'research-run','assurance_profile':'research_strict','research_contract':'research-contract.json',
            'budget':{'max_wall_clock_seconds':300,'max_retries':1},
            'tasks':[{'task_id':'analysis','parent_task_id':None,'goal':'Validate research','depends_on':[],'write_scope':[{'path':'out.json','kind':'file'}],'operation_class':'reversible_write','verification_mode':'semantic_review_required','risk_tags':['statistical_design','data_leakage'],'required_checks':['review']}]
        }
        result=copy.deepcopy(self.valid); result.update(run_id='research-run',task_id='analysis',worker_id='worker-1')
        result['verification']={'required_checks':['review'],'checks':[{'check_id':'review','type':'semantic_review','result':'passed','observed_by':'reviewer','observer_id':'reviewer-1','evidence_refs':['out.json']}],'validity_review':{'required':True,'status':'passed','reviewer_id':'reviewer-1'}}
        contract=json.loads((FIX/'research-contract.valid.json').read_text())
        contract_refs={contract['evaluation']['raw_predictions_artifact'],contract['data_quality']['missingness_artifact'],contract['data_quality']['physical_constraints_artifact'],contract['data_quality']['category_normalization_artifact'],contract['reproduction']['split_artifact'],contract['reproduction']['environment_artifact'],contract['reproduction']['command_artifact']} | {ref for gate in contract['validation_gates'] for ref in gate['evidence_refs']}
        result['evidence']=sorted({'out.json'}|contract_refs); result['artifacts']=['out.json','bundle.json']
        result.update(research_validation=[{'gate_id':gate['gate_id'],'status':gate['status'],'reason':gate['reason'],'evidence_refs':['out.json']} for gate in contract['validation_gates']],claim_evidence_map=[{'claim_id':'conclusion','claim':'Predictive performance was evaluated without leakage.','status':'supported','evidence_refs':['out.json']}],invalidated_artifacts=[],reproduction_bundle='bundle.json',review_scope=['design','data','execution','numerical_results','interpretation','claims','reproducibility'],review_findings=[])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'out.json').write_text('{}'); (root/'bundle.json').write_text('{}'); (root/'manifest.json').write_text(json.dumps(manifest)); (root/'research-contract.json').write_text(json.dumps(contract)); (root/'result.json').write_text(json.dumps(result))
            refs=[contract['evaluation']['raw_predictions_artifact'],contract['data_quality']['missingness_artifact'],contract['data_quality']['physical_constraints_artifact'],contract['data_quality']['category_normalization_artifact']]
            refs += [contract['reproduction'][key] for key in ('split_artifact','environment_artifact','command_artifact')]
            refs += [ref for gate in contract['validation_gates'] for ref in gate['evidence_refs']]
            for ref in set(refs): (root/ref).write_text('{}')
            cmd=[sys.executable,str(SCRIPTS/'validate_task_result.py'),'--json','--manifest',str(root/'manifest.json'),str(root/'result.json')]
            passed=subprocess.run(cmd,capture_output=True,text=True); self.assertEqual(passed.returncode,0,passed.stdout+passed.stderr)
            revision=copy.deepcopy(result); revision['status']='needs_revision'; (root/'result.json').write_text(json.dumps(revision))
            reviewed_revision=subprocess.run(cmd,capture_output=True,text=True); self.assertEqual(reviewed_revision.returncode,0,reviewed_revision.stdout+reviewed_revision.stderr)
            no_worker=copy.deepcopy(result); no_worker.pop('worker_id'); (root/'result.json').write_text(json.dumps(no_worker))
            failed=subprocess.run(cmd,capture_output=True,text=True); self.assertNotEqual(failed.returncode,0); self.assertIn('worker_id',failed.stdout)
            result['claim_evidence_map'][0]['status']='invalidated'; (root/'result.json').write_text(json.dumps(result))
            failed=subprocess.run(cmd,capture_output=True,text=True); self.assertNotEqual(failed.returncode,0); self.assertIn('invalidated claims',failed.stdout)
            blocked=copy.deepcopy(result); blocked.update(status='blocked',blocked_reason='resource_unavailable',artifacts=[],evidence=['out.json'])
            for field in ('research_validation','claim_evidence_map','invalidated_artifacts','reproduction_bundle','review_scope','review_findings'): blocked.pop(field)
            blocked.pop('worker_id',None); blocked['verification']['validity_review']={'required':False,'status':'not_run','reviewer_id':None}; (root/'result.json').write_text(json.dumps(blocked))
            partial=subprocess.run(cmd,capture_output=True,text=True); self.assertEqual(partial.returncode,0,partial.stdout+partial.stderr)
            (root/'research-contract.json').unlink()
            for ref in contract_refs: (root/ref).unlink(missing_ok=True)
            blocked_before_execution=subprocess.run(cmd,capture_output=True,text=True); self.assertEqual(blocked_before_execution.returncode,0,blocked_before_execution.stdout+blocked_before_execution.stderr)

class ManifestTests(unittest.TestCase):
    def setUp(self): self.valid=load('manifest.valid.json')
    def test_valid_ready_and_ordered_scope(self):
        self.assertEqual(validate_manifest(self.valid),[]); self.assertEqual(ready_tasks(self.valid,set()),['format']); self.assertEqual(ready_tasks(self.valid,{'format'}),['review'])
    def test_missing_dependency_and_cycle(self):
        d=copy.deepcopy(self.valid); d['tasks'][0]['depends_on']=['missing']; self.assertTrue(validate_manifest(d))
        d=copy.deepcopy(self.valid); d['tasks'][0]['depends_on']=['review']; self.assertTrue(any('cycle' in e for e in validate_manifest(d)))
    def test_bad_paths(self):
        for path in ('/tmp/x','../x','a/*','a//b','a/'):
            d=copy.deepcopy(self.valid); d['tasks'][0]['write_scope'][0]['path']=path
            with self.subTest(path=path): self.assertTrue(validate_manifest(d))
    def test_parallel_conflict_reported_but_manifest_valid(self):
        d=copy.deepcopy(self.valid); other=copy.deepcopy(d['tasks'][0]); other['task_id']='other'; other['write_scope']=[{'path':'out.json','kind':'file'}]; d['tasks']=[d['tasks'][0],other]
        self.assertEqual(validate_manifest(d),[]); self.assertTrue(detect_write_conflicts(d['tasks']))
    def test_risk_requires_semantic_review(self):
        d=copy.deepcopy(self.valid); d['tasks'][0]['risk_tags']=['external_fact']; self.assertTrue(validate_manifest(d))
    def test_approval_requires_review_and_success_check(self):
        d=copy.deepcopy(self.valid); d['tasks'][0]['operation_class']='approval_required'; self.assertTrue(validate_manifest(d))
    def test_approval_alone_does_not_release_dependent(self):
        d=copy.deepcopy(self.valid); d['tasks'][0].update(operation_class='approval_required',verification_mode='semantic_review_required',required_checks=['operation_success']); d['tasks'][1]['depends_on']=['format']
        self.assertEqual(validate_manifest(d),[]); self.assertEqual(ready_tasks(d,{'format'}),[]); self.assertEqual(ready_tasks(d,{'format'},{'format'}),['review'])
    def test_standard_profile_rejects_research_contract(self):
        d=copy.deepcopy(self.valid); d['research_contract']='runs/research.json'; self.assertTrue(validate_manifest(d))
    def test_research_strict_requires_contract_and_research_risk(self):
        d=copy.deepcopy(self.valid); d['assurance_profile']='research_strict'; self.assertTrue(validate_manifest(d))
        d['research_contract']='runs/research.json'; d['tasks'][1]['risk_tags']=['statistical_design']; self.assertEqual(validate_manifest(d),[])
    def test_research_risk_cannot_use_standard_profile(self):
        d=copy.deepcopy(self.valid); d['tasks'][1]['risk_tags']=['data_leakage']
        self.assertTrue(any('require research_strict' in error for error in validate_manifest(d)))

if __name__=='__main__': unittest.main()
