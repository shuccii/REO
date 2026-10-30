"""Offline benchmark contract tests; no paid CLI calls."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BENCH=Path(__file__).resolve().parents[1]/'evals/bench'
sys.path.insert(0,str(BENCH))
import run as runner
import grade as grader

class BenchRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'inputs/paper_mat').mkdir(parents=True)
        (self.root/'inputs/paper_mat/manuscript.md').write_text('original input')
        self.plugin=self.root/'plugin';self.plugin.mkdir();(self.plugin/'SKILL.md').write_text('source v1')
        self.addCleanup(patch.stopall)
        patch.object(runner,'BENCH',self.root).start()
        patch.dict(runner.PLUGINS,{'reo':str(self.plugin)}).start()
        self.calls=[]
    def fake(self,cmd,**kw):
        if '--version' in cmd:return subprocess.CompletedProcess(cmd,0,stdout='Claude 9.test\n')
        self.calls.append((cmd,kw['input']))
        kw['stdout'].write(json.dumps({'type':'system','subtype':'init','model':'fixed','plugins':[{'name':'reo','path':'local'}]})+'\n')
        kw['stdout'].write(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','name':'Skill','input':{'skill':'reo:review'}}]}})+'\n')
        kw['stdout'].write(json.dumps({'type':'result','subtype':'success','result':'review','usage':{'input_tokens':12,'output_tokens':5},'total_cost_usd':.02})+'\n')
        return subprocess.CompletedProcess(cmd,0)
    def test_requires_explicit_model(self):
        with patch.dict('os.environ',{},clear=True),self.assertRaises(ValueError):runner.run('paper_mat','reo',1)
    def test_cache_identity_and_observed_usage(self):
        with patch.object(runner.subprocess,'run',side_effect=self.fake):
            runner.run('paper_mat','reo',1,model='fixed')
            out=self.root/'runs/paper_mat/reo-1';meta=json.loads((out/'meta.json').read_text())
            self.assertTrue(meta['completed']);self.assertEqual(meta['input_tokens'],12)
            self.assertIsNone(meta['reasoning_tokens']);self.assertEqual(meta['skills'],['reo:review'])
            self.assertIn('--model',self.calls[0][0]);self.assertTrue((out/'inputs/manuscript.md').exists())
            runner.run('paper_mat','reo',1,model='fixed');self.assertEqual(len(self.calls),1)
            (self.plugin/'SKILL.md').write_text('source v2')
            runner.run('paper_mat','reo',1,model='fixed');self.assertEqual(len(self.calls),2)
            self.assertEqual(len(list((self.root/'runs/paper_mat/history').glob('*/meta.json'))),1)
    def test_private_files_are_not_fingerprinted_and_outputs_are_protected(self):
        (self.plugin / '.env').write_text('not source')
        source = runner.plugin_source(self.plugin)
        self.assertNotIn('.env', source['files'])
        with patch.object(runner.subprocess, 'run', side_effect=self.fake):
            runner.run('paper_mat', 'reo', 1, model='fixed')
            out = self.root / 'runs/paper_mat/reo-1'
            (out / 'final.md').write_text('changed output')
            runner.run('paper_mat', 'reo', 1, model='fixed')
        self.assertEqual(len(self.calls), 2)

    def test_cached_rubric_must_match_original(self):
        (self.root / 'RUBRIC.md').write_text('original rubric')
        with patch.object(runner.subprocess, 'run', side_effect=self.fake):
            runner.run('paper_mat', 'reo', 1, model='fixed')
            (self.root / 'runs/paper_mat/reo-1/rubric.md').write_text('changed rubric')
            runner.run('paper_mat', 'reo', 1, model='fixed')
        self.assertEqual(len(self.calls), 2)

    def test_timeout_is_recorded_and_not_reused(self):
        def timeout(cmd,**kw):
            if '--version' in cmd:return subprocess.CompletedProcess(cmd,0,stdout='v1')
            raise subprocess.TimeoutExpired(cmd,1)
        with patch.object(runner.subprocess,'run',side_effect=timeout):
            runner.run('paper_mat','reo',1,model='fixed',timeout=1)
        meta=json.loads((self.root/'runs/paper_mat/reo-1/meta.json').read_text())
        self.assertFalse(meta['completed']);self.assertTrue(meta['timed_out'])
    def test_incomplete_exit_zero_is_not_cached(self):
        def incomplete(cmd, **kw):
            if '--version' in cmd: return subprocess.CompletedProcess(cmd, 0, stdout='v1')
            self.calls.append(cmd)
            kw['stdout'].write(json.dumps({'type': 'assistant', 'message': {'content': []}}) + '\n')
            return subprocess.CompletedProcess(cmd, 0)
        with patch.object(runner.subprocess, 'run', side_effect=incomplete):
            runner.run('paper_mat', 'reo', 1, model='fixed')
            runner.run('paper_mat', 'reo', 1, model='fixed')
        self.assertEqual(len(self.calls), 2)
        meta = json.loads((self.root/'runs/paper_mat/reo-1/meta.json').read_text())
        self.assertFalse(meta['completed'])

    def test_grader_reads_retained_inputs(self):
        out=self.root/'runs/paper_mat/reo-1';(out/'inputs').mkdir(parents=True)
        (out/'inputs/manuscript.md').write_text('retained input')
        self.assertIn('retained input',grader.inputs_text(out))
    def test_report_paired_quality_and_missing_usage(self):
        import report
        rows=[{'task':'t','arm':a,'rep':1,'completed':True,'requested_model':'fixed','model':'fixed','inputs':{},'config':{},'rubric_sha256':'r','seconds':s,'cost_usd':.1,'input_tokens':None,'grade':{'_provenance':{'model':'judge','cli_version':'v1','grader_source_sha256':'source'},'scores':{'D1':{'score':q}},'decoys':{},'incorrect_claims':[]}} for a,s,q in [('base',3,0),('reo',4,2)]]
        result=report.aggregate(rows)
        self.assertIsNone(result['arms']['base']['input_tokens']['mean'])
        self.assertEqual(result['paired']['reo_vs_base']['quality_score_delta_mean'],2)

if __name__=='__main__':unittest.main()

class GraderContractTests(unittest.TestCase):
    def test_grade_keeps_prompt_and_observed_model_provenance(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'paper_mat/reo-1';(out/'inputs').mkdir(parents=True)
            (out/'inputs/manuscript.md').write_text('snapshot input')
            (out/'final.md').write_text('review output')
            rubric='## paper_mat\n- P1 flaw\n- X1 (decoy) correct practice\n'
            (out/'rubric.md').write_text(rubric)
            from runtime import digest
            (out/'meta.json').write_text(json.dumps({'completed':True,'identity':'run-id','outputs':runner.output_hashes(out),'inputs':digest(out/'inputs'),'rubric_sha256':hashlib.sha256(rubric.encode()).hexdigest()}))
            calls=[]
            def fake(cmd,**kw):
                if '--version' in cmd:return subprocess.CompletedProcess(cmd,0,stdout='cli-v1')
                calls.append(cmd)
                data={'scores':{'P1':{'score':2,'evidence':'quote'}},'decoys':{'X1':{'falsely_flagged':0,'evidence':'none'}},'incorrect_claims':[],'extra_valid_findings':0}
                return subprocess.CompletedProcess(cmd,0,stdout=json.dumps({'result':json.dumps(data),'usage':{'input_tokens':12}}),stderr='')
            with patch.object(grader.subprocess,'run',side_effect=fake):
                _,data=grader.grade(out,model='grader-fixed')
                grader.grade(out,model='grader-fixed')
                self.assertEqual(len(calls),1)
                mutated=json.loads((out/'grade.json').read_text());mutated['scores']['P1']['score']=0
                (out/'grade.json').write_text(json.dumps(mutated))
                grader.grade(out,model='grader-fixed')
            self.assertEqual(len(calls),2)
            self.assertEqual(data['_provenance']['model'],'grader-fixed')
            self.assertIn('snapshot input',(out/'grade-prompt.txt').read_text())

class ReportProvenanceTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        from runtime import digest
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.out=self.root/'paper_mat/reo-1'
        (self.out/'inputs').mkdir(parents=True)
        (self.out/'inputs/manuscript.md').write_text('original')
        (self.out/'final.md').write_text('review')
        (self.out/'rubric.md').write_text('## paper_mat\n- P1 flaw\n- X1 (decoy) correct\n')
        (self.out/'grade-prompt.txt').write_text('grade prompt')
        sha=lambda text:hashlib.sha256(text.encode()).hexdigest()
        self.meta={'task':'paper_mat','arm':'reo','rep':1,'completed':True,'identity':'id','outputs':runner.output_hashes(self.out),'inputs':digest(self.out/'inputs'),'rubric_sha256':sha((self.out/'rubric.md').read_text())}
        (self.out/'meta.json').write_text(json.dumps(self.meta))
        g={'scores':{'P1':{'score':2}},'decoys':{'X1':{'falsely_flagged':0}},'incorrect_claims':[],
           '_provenance':{'run_identity':'id','model':'old-judge','cli_version':'v1','inputs':self.meta['inputs'],'rubric_sha256':self.meta['rubric_sha256'],'output_sha256':sha('review'),'prompt_sha256':sha('grade prompt')}}
        (self.out/'grade.json').write_text(json.dumps(g))
        (self.out/'grade-meta.json').write_text(json.dumps({'grade_sha256':hashlib.sha256((self.out/'grade.json').read_bytes()).hexdigest()}))
    def test_report_rejects_changed_inputs_outputs_rubric_and_prompt(self):
        import report
        self.assertIn('grade',report.load_rows(self.root)[0])
        for name in ('inputs/manuscript.md','final.md','rubric.md','grade-prompt.txt'):
            with self.subTest(name=name):
                path=self.out/name;original=path.read_text();path.write_text(original+'tampered')
                self.assertNotIn('grade',report.load_rows(self.root)[0])
                path.write_text(original)
    def test_report_rejects_mutated_grade_payload(self):
        import report
        payload=json.loads((self.out/'grade.json').read_text())
        payload['scores']['P1']['score']=0
        (self.out/'grade.json').write_text(json.dumps(payload))
        self.assertNotIn('grade',report.load_rows(self.root)[0])

    def test_failed_regrade_does_not_leave_old_grade_active(self):
        def fail(cmd,**kw):
            if '--version' in cmd:return subprocess.CompletedProcess(cmd,0,stdout='v1')
            return subprocess.CompletedProcess(cmd,1,stdout='',stderr='judge failed')
        with patch.object(grader.subprocess,'run',side_effect=fail):
            _,result=grader.grade(self.out,model='new-judge')
        self.assertIn('error',result)
        self.assertFalse((self.out/'grade.json').exists())
        self.assertTrue(list(self.out.glob('grade-*.json')))

class PairCompatibilityTests(unittest.TestCase):
    def test_pair_rejects_changed_model_inputs_settings_cli_or_rubric(self):
        import report
        base={'task':'t','arm':'base','rep':1,'completed':True,'requested_model':'model-A','model':'actual-A','inputs':{'input':'hash-A'},'config':{'cli_version':'v1','settings':{}},'rubric_sha256':'rubric-A','grade':{'scores':{'D1':{'score':0}},'decoys':{},'incorrect_claims':[]}}
        for key,value in [('requested_model','model-B'),('model','actual-B'),('inputs',{'input':'hash-B'}),('config',{'cli_version':'v2','settings':{}}),('rubric_sha256','rubric-B')]:
            with self.subTest(key=key):
                other={**base,'arm':'reo',key:value}
                pair=report.aggregate([base,other])['paired']['reo_vs_base']
                self.assertEqual(pair['graded_pairs'],0)
                self.assertEqual(pair['excluded_incompatible_pairs'],1)

class SourceLayoutTests(unittest.TestCase):
    def test_command_agents_and_manifest_declared_source_invalidate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'.claude-plugin').mkdir()
            (root/'.claude-plugin/plugin.json').write_text(json.dumps({'name':'test','commands':'./custom_commands'}))
            for folder in ('commands','agents','custom_commands'):
                (root/folder).mkdir();(root/folder/'review.md').write_text('v1')
            for folder in ('commands','agents','custom_commands'):
                before=runner.plugin_source(root)
                (root/folder/'review.md').write_text('v2')
                self.assertNotEqual(before,runner.plugin_source(root))

class GraderCohortTests(unittest.TestCase):
    def test_pairs_require_same_grader_model_cli_and_template_source(self):
        import copy
        import report
        base={'task':'t','arm':'base','rep':1,'completed':True,'requested_model':'runner','model':'runner','inputs':{},'config':{},'rubric_sha256':'r',
              'grade':{'scores':{'D1':{'score':0}},'decoys':{},'incorrect_claims':[],
                       '_provenance':{'model':'judge-A','cli_version':'cli-A','grader_source_sha256':'template-A'}}}
        for key,value in [('model','judge-B'),('cli_version','cli-B'),('grader_source_sha256','template-B')]:
            with self.subTest(key=key):
                other=copy.deepcopy(base);other['arm']='reo';other['grade']['_provenance'][key]=value
                pair=report.aggregate([base,other])['paired']['reo_vs_base']
                self.assertEqual(pair['graded_pairs'],0)
                self.assertEqual(pair['excluded_incompatible_pairs'],1)
