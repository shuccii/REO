import copy, json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmarks'))
from cases import score
from harness import compare, digest, evaluate_holdout, evaluator_digest, evidence_references, validate_adjudications, summarize_events, score_observed_behavior, score_review_completion, score_strict_research_completion, strict_result_contract_matches, frozen_files


def row(case,version,pair,session='session-1',seconds=10.0):
    return {'benchmark_session_id':session,'run_id':f'{case}-{version}-{pair}','case_id':case,'version':version,'phase':'comparison','pair':pair,'status':'completed','active_wall_clock':seconds,'requested_model':'model','reasoning_effort':'high','pack_sha256':f'pack-{version}','case_sha256':f'case-{case}','evaluator_sha256':'evaluator-1','grade':{'critical_pass':True,'noncritical_score':1}}


def config(cases):
    return {'benchmark_session_id':'session-1','model':'model','effort':'high','cases':cases,'evaluator_sha256':'evaluator-1','pack_sha256':{'v0.1.0':'pack-v0.1.0','working':'pack-working'},'case_sha256':{case:f'case-{case}' for case in cases},'holdout_case_sha256':{'holdout_format':'case-holdout_format','holdout_research':'case-holdout_research'}}


class HarnessTests(unittest.TestCase):
    def test_strict_benchmark_requires_contract_result_and_observed_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            grade={'critical':{'detect_S1':True},'critical_pass':True}
            checked=score_strict_research_completion(Path(directory),grade,{'observed_agent_ids':[]})
            self.assertFalse(checked['critical_pass']); self.assertFalse(checked['critical']['strict_manifest']); self.assertFalse(checked['critical']['strict_observed_reviewer'])
    def test_strict_benchmark_binds_invalidated_products(self):
        contract=json.loads((ROOT/'tests/fixtures/research-contract.valid.json').read_text())
        next(gate for gate in contract['validation_gates'] if gate['gate_id']=='split_integrity')['status']='failed'
        for product in contract['products']: product['status']='invalidated'
        result={'research_validation':[{'gate_id':gate['gate_id'],'status':gate['status']} for gate in contract['validation_gates']],'evidence':list(evidence_references(contract)),'invalidated_artifacts':[]}
        self.assertFalse(strict_result_contract_matches(contract,result)); result['invalidated_artifacts']=[product['artifact_id'] for product in contract['products']]; self.assertTrue(strict_result_contract_matches(contract,result))
    def test_frozen_pack_ignores_os_metadata(self):
        self.assertFalse(any(path.endswith('.DS_Store') for path in frozen_files('working')))

    def test_real_cli_collaboration_events_are_counted_and_disallowed_for_format(self):
        events=[{'type':'item.started','item':{'id':'1','type':'collab_tool_call','tool':'wait','receiver_thread_ids':[]}}, {'type':'item.completed','item':{'id':'1','type':'collab_tool_call','tool':'wait','receiver_thread_ids':[]}}, {'type':'item.completed','item':{'id':'2','type':'collab_agent_tool_call','tool':'spawn_agent','status':'failed'}}]
        telemetry=summarize_events(events)
        self.assertEqual(telemetry['observed_collaboration_events'],2)
        self.assertEqual(telemetry['observed_spawn_calls'],1)
        self.assertEqual(telemetry['observed_subagent_events'],1)
        self.assertEqual(telemetry['observed_unbound_waits'],1)
        self.assertIsNone(telemetry['subagent_count'])
        grade=score_observed_behavior('format',{'critical':{'values':True},'critical_pass':True},telemetry)
        self.assertFalse(grade['critical_pass'])

    def test_unbound_wait_fails_independent_modules(self):
        telemetry=summarize_events([{'type':'item.started','item':{'id':'wait-1','type':'collab_tool_call','tool':'wait','receiver_thread_ids':[]}}])
        grade=score_observed_behavior('independent_modules',{'critical':{'artifacts':True},'critical_pass':True},telemetry)
        self.assertFalse(grade['critical_pass'])

    def test_lifecycle_metadata_can_bind_a_started_wait(self):
        events=[{'type':'item.started','item':{'id':'wait-1','type':'collab_tool_call','tool':'wait'}},{'type':'item.completed','item':{'id':'wait-1','type':'collab_tool_call','tool':'wait','receiver_thread_ids':['worker-1']}}]
        telemetry=summarize_events(events)
        self.assertEqual(telemetry['observed_collaboration_events'],1); self.assertEqual(telemetry['observed_unbound_waits'],0)
        self.assertEqual(telemetry['observed_agent_ids'],['worker-1'])

    def test_review_completion_requires_contracts_and_observed_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); grade=lambda: {'critical':{'artifacts':True},'critical_pass':True}
            self.assertFalse(score_review_completion(root,grade(),{'observed_agent_ids':[]})['critical_pass'])
            tasks=[]
            for name in ('names','stats'):
                tasks.append({'task_id':name,'parent_task_id':None,'goal':name,'depends_on':[],'write_scope':[{'path':name+'.py','kind':'file'}],'operation_class':'reversible_write','verification_mode':'semantic_review_required','risk_tags':['implementation_change'],'required_checks':['review']})
                folder=root/name; folder.mkdir(); (folder/'out.json').write_text('{}')
                result=json.loads((ROOT/'tests/fixtures/result.completed.valid.json').read_text()); result.update(task_id=name,worker_id='worker-'+name)
                result['verification']={'required_checks':['review'],'checks':[{'check_id':'review','type':'semantic_review','result':'passed','observed_by':'reviewer','observer_id':'reviewer-1','evidence_refs':['out.json']}],'validity_review':{'required':True,'status':'passed','reviewer_id':'reviewer-1'}}
                (folder/'result.json').write_text(json.dumps(result))
            manifest={'schema_version':'0.3.0','run_id':'run-1','assurance_profile':'standard','research_contract':None,'budget':{'max_wall_clock_seconds':300,'max_retries':1},'tasks':tasks}; (root/'tasks.json').write_text(json.dumps(manifest))
            self.assertFalse(score_review_completion(root,grade(),{'observed_agent_ids':[]})['critical_pass'])
            self.assertTrue(score_review_completion(root,grade(),{'observed_agent_ids':['reviewer-1']})['critical_pass'])
            (root/'tasks.json').unlink()
            for task in tasks:
                split=copy.deepcopy(manifest); split['tasks']=[task]; (root/task['task_id']/'tasks.json').write_text(json.dumps(split))
            self.assertFalse(score_review_completion(root,grade(),{'observed_agent_ids':['reviewer-1']})['critical_pass'])

    def test_compare_pass_and_session_isolation(self):
        rows=[]
        for pair in range(3): rows += [row('format','v0.1.0',pair,seconds=10),row('format','working',pair,seconds=8)]
        rows.append(row('format','working',0,session='other',seconds=100))
        result=compare(rows,cases=['format'],config=config(['format']))
        self.assertEqual(result['decision'],'pass'); self.assertEqual(result['paired_ratio_median'],.8)

    def test_duplicate_and_frozen_mismatch_are_not_eligible(self):
        rows=[]
        for pair in range(3): rows += [row('format','v0.1.0',pair),row('format','working',pair)]
        rows.append(copy.deepcopy(rows[1])); rows[2]['case_sha256']='wrong'
        result=compare(rows,cases=['format'],config=config(['format']))
        self.assertEqual(result['decision'],'insufficient_measurement'); self.assertTrue(result['reasons'])
        rows=rows[:-1]; rows[0]['evaluator_sha256']='changed'
        self.assertEqual(compare(rows,cases=['format'],config=config(['format']))['decision'],'insufficient_measurement')

    def test_semantic_adjudication_is_bound_to_run(self):
        rows=[row('bugfix','v0.1.0',0),row('bugfix','working',0)]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'adjudications.jsonl'
            decisions=[]
            for item in rows: decisions.append({'benchmark_session_id':'session-1','run_id':item['run_id'],'case_id':'bugfix','version':item['version'],'passed':True,'critical_failures':[],'reviewer_id':'reviewer-2','reviewed_at':'2026-09-02T00:00:00Z'})
            path.write_text('\n'.join(map(json.dumps,decisions))+'\n')
            self.assertEqual(len(validate_adjudications(rows,path)),2)
            decisions[0]['case_id']='format'; path.write_text(json.dumps(decisions[0])+'\n')
            with self.assertRaises(ValueError): validate_adjudications(rows,path)
            decisions[0]['case_id']='bugfix'; decisions[0]['passed']=True; decisions[0]['critical_failures']=['contradiction']; path.write_text(json.dumps(decisions[0])+'\n')
            with self.assertRaises(ValueError): validate_adjudications(rows,path)

    def test_failed_semantic_review_is_quality_failure(self):
        rows=[]; decisions={}
        for pair in range(3):
            for version in ('v0.1.0','working'):
                item=row('bugfix',version,pair,seconds=10 if version=='v0.1.0' else 8); rows.append(item)
                decisions[item['run_id']]={'passed':version=='v0.1.0'}
        result=compare(rows,cases=['bugfix'],config=config(['bugfix']),adjudications=decisions)
        self.assertEqual(result['decision'],'fail'); self.assertTrue(result['quality_failure'])

    def test_host_scorer_does_not_execute_generated_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); marker=root/'EXECUTED'
            (root/'average.py').write_text(f'from pathlib import Path\nPath({str(marker)!r}).write_text("bad")\ndef average(values): return 1\n')
            (root/'test_average.py').write_text('def test_placeholder(): pass\n')
            self.assertTrue(score('bugfix',root)['critical_pass']); self.assertFalse(marker.exists())

    def test_noncritical_rubric_is_nonconstant(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'input.json').write_text('{"a": 1}\n'); (root/'formatted.json').write_text('{\n  "a": 1\n}')
            first=score('format',root); self.assertEqual(first['noncritical'],{'terminal_newline':False})
            (root/'formatted.json').write_text('{\n  "a": 1\n}\n'); self.assertGreater(score('format',root)['noncritical_score'],first['noncritical_score'])

    def test_parallel_candidate_contract_is_graded(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'names.py').write_text('def slug(value): return value\n'); (root/'stats.py').write_text('def median(value): return value\n'); (root/'test_modules.py').write_text('def test_slug_and_median(): pass\n')
            run=root/'runs'; run.mkdir(); manifest={'schema_version':'0.3.0','run_id':'test-run','assurance_profile':'standard','research_contract':None,'budget':{'max_wall_clock_seconds':300,'max_retries':1},'tasks':[{'task_id':'names','parent_task_id':None,'goal':'names','depends_on':[],'write_scope':[{'path':'names.py','kind':'file'}],'operation_class':'reversible_write','verification_mode':'semantic_review_required','risk_tags':['implementation_change'],'required_checks':['review']},{'task_id':'stats','parent_task_id':None,'goal':'stats','depends_on':[],'write_scope':[{'path':'stats.py','kind':'file'}],'operation_class':'reversible_write','verification_mode':'semantic_review_required','risk_tags':['implementation_change'],'required_checks':['review']}]}; (run/'tasks.json').write_text(json.dumps(manifest))
            self.assertTrue(score('independent_modules',root)['critical']['parallel_candidates_recorded'])
            integration=copy.deepcopy(manifest['tasks'][0]); integration.update(task_id='integration',goal='integration',depends_on=['names','stats'],write_scope=[{'path':'names.py','kind':'file'},{'path':'stats.py','kind':'file'}]); manifest['tasks'].insert(0,integration); (run/'tasks.json').write_text(json.dumps(manifest))
            self.assertTrue(score('independent_modules',root)['critical']['parallel_candidates_recorded'])
            manifest['tasks'].pop(0)
            manifest['tasks'][1]['depends_on']=['names']; (run/'tasks.json').write_text(json.dumps(manifest))
            self.assertFalse(score('independent_modules',root)['critical']['parallel_candidates_recorded'])
            manifest['tasks'][1]['depends_on']=[]; original=copy.deepcopy(manifest['tasks']); manifest['tasks']=[{'task_id':'both',**{k:v for k,v in manifest['tasks'][0].items() if k!='task_id'},'write_scope':[{'path':'names.py','kind':'file'},{'path':'stats.py','kind':'file'}]}]; (run/'tasks.json').write_text(json.dumps(manifest))
            self.assertFalse(score('independent_modules',root)['critical']['parallel_candidates_recorded'])
            name,stats=original; bridge=copy.deepcopy(name); bridge.update(task_id='bridge',goal='bridge',depends_on=['names'],write_scope=[{'path':'bridge.txt','kind':'file'}]); stats['depends_on']=['bridge']; manifest['tasks']=[name,bridge,stats]; (run/'tasks.json').write_text(json.dumps(manifest))
            self.assertFalse(score('independent_modules',root)['critical']['parallel_candidates_recorded'])
            stats['depends_on']=[]; stats['write_scope'].append({'path':'shared','kind':'tree'}); name['write_scope'].append({'path':'shared/file.txt','kind':'file'}); (run/'tasks.json').write_text(json.dumps(manifest))
            self.assertFalse(score('independent_modules',root)['critical']['parallel_candidates_recorded'])

    def test_invalid_timeout_and_unobservable_budget_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            nested=str(Path(directory)/'missing'/'nested'); base=[sys.executable,str(ROOT/'benchmarks/harness.py'),'pilot','--output',nested]
            bad=subprocess.run(base+['--timeout','nan'],capture_output=True,text=True); self.assertNotEqual(bad.returncode,0)
            zero=subprocess.run(base+['--max-total-tokens','0'],capture_output=True,text=True); self.assertEqual(zero.returncode,2)
            blocked=subprocess.run(base+['--max-llm-calls','1'],capture_output=True,text=True); self.assertNotEqual(blocked.returncode,0); self.assertTrue((Path(nested)/'preflight.json').exists())

    def test_holdout_gate_rejects_missing_primary(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); root.joinpath('benchmark-session.json').write_text(json.dumps(config(['format']))); root.joinpath('metrics.jsonl').write_text('')
            process=subprocess.run([sys.executable,str(ROOT/'benchmarks/harness.py'),'holdout','--output',directory],capture_output=True,text=True)
            self.assertNotEqual(process.returncode,0)

    def test_holdout_report_requires_quality_and_review(self):
        primary=config(['format']); primary['pack_sha256']['working']='pack-working'
        holdout={'benchmark_session_id':'holdout-1','case_sha256':{'holdout_format':'case-holdout_format','holdout_research':'case-holdout_research'}}
        rows=[]
        for case in ('holdout_format','holdout_research'):
            item=row(case,'working',0,session='holdout-1',seconds=8); item['phase']='holdout'; rows.append(item)
        self.assertEqual(evaluate_holdout(rows,holdout,primary)['decision'],'insufficient_measurement')
        decisions={rows[1]['run_id']:{'passed':True}}
        self.assertEqual(evaluate_holdout(rows,holdout,primary,decisions)['decision'],'pass')
        rows[1]['requested_model']='other'
        self.assertEqual(evaluate_holdout(rows,holdout,primary,decisions)['decision'],'insufficient_measurement')

    def test_report_exit_reflects_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); settings=config(['format']); settings['evaluator_sha256']=evaluator_digest(); root.joinpath('benchmark-session.json').write_text(json.dumps(settings)); root.joinpath('metrics.jsonl').write_text('')
            process=subprocess.run([sys.executable,str(ROOT/'benchmarks/harness.py'),'report','--output',directory],capture_output=True,text=True)
            self.assertEqual(process.returncode,1); self.assertIn('insufficient_measurement',process.stdout)

    def test_scoped_report_does_not_unlock_holdout(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); settings=config(['format']); settings['evaluator_sha256']=evaluator_digest(); root.joinpath('benchmark-session.json').write_text(json.dumps(settings)); root.joinpath('metrics.jsonl').write_text('')
            process=subprocess.run([sys.executable,str(ROOT/'benchmarks/harness.py'),'holdout','--output',directory],capture_output=True,text=True)
            self.assertNotEqual(process.returncode,0); self.assertIn('full primary comparison',process.stderr)


if __name__=='__main__': unittest.main()
