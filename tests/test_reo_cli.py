import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ReoCliTests(unittest.TestCase):
    def run_cli(self,*args,cwd=None):
        p=subprocess.run([sys.executable,str(ROOT/'tools/reo.py'),*args],cwd=cwd,capture_output=True,text=True)
        return p.returncode,json.loads(p.stdout)
    def test_doctor_reports_dependencies_without_installing(self):
        code,r=self.run_cli('doctor');self.assertIn('python',r);self.assertIn('dependencies',r)
        self.assertIn('plugin_version',r);self.assertIn(code,(0,1))
    def test_check_reports_facts_not_scientific_certification(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'draft.md').write_text('# Abstract\nMAE = 0.3\n\n# Results\nMAE = 0.4\n')
            (p/'data.csv').write_text('id,y,split\na,1,train\na,1,train\na,2,test\n')
            code,r=self.run_cli('check','draft.md','--data','data.csv','--unit','id','--split','split',cwd=d)
            self.assertEqual(code,1);self.assertEqual(r['data']['duplicate_rows'],1)
            self.assertEqual(r['data']['cross_split_units'],['a'])
            self.assertFalse(r['scientific_validity_assessed']);self.assertTrue(r['summary'])
    def test_no_inferred_csv_roles_and_invalid_columns(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'d.md').write_text('# test');(p/'d.csv').write_text('id,y\na,2\n')
            code,r=self.run_cli('check','d.md','--data','d.csv',cwd=d)
            self.assertIsNone(r['data']['cross_split_units']);self.assertIn('not supplied',' '.join(r['limitations']))
            code,r=self.run_cli('check','d.md','--data','d.csv','--unit','missing',cwd=d)
            self.assertEqual(code,2);self.assertIn('error',r)
    def test_project_profile_overrides_global_and_explicit_overrides_project(self):
        sys.path.insert(0,str(ROOT/'tools'));from reo_profile import resolve_path
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'.reo').mkdir();((p/'.reo/profile.md').resolve()).write_text('- 分野: 材料')
            self.assertEqual(resolve_path(workspace=p),(p/'.reo/profile.md').resolve())
            self.assertEqual(resolve_path('other.md',workspace=p),Path('other.md'))
    def test_state_round_trip_requires_explicit_save(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'draft.md').write_text('claim');(p/'graph.json').write_text(json.dumps({'nodes':[{'id':'claim','path':'draft.md'}]}))
            code,r=self.run_cli('state','graph.json','--save','state.json',cwd=d)
            self.assertEqual(code,0);self.assertTrue((p/'state.json').exists())
            code,r=self.run_cli('state','graph.json','--previous','state.json',cwd=d)
            self.assertEqual(r['delta']['reusable_evidence'],['claim'])
            self.assertFalse(r['delta']['semantic_review_completed'])

    def test_save_cannot_overwrite_document_or_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'d.md').write_text('# original');(p/'d.csv').write_text('id,y\na,1\n')
            for name in ('d.md','d.csv'):
                code,r=self.run_cli('check','d.md','--data','d.csv','--save',name,cwd=d)
                self.assertEqual(code,2);self.assertIn('overwrite',r['error'])
            self.assertEqual((p/'d.md').read_text(),'# original')
    def test_corrupt_docx_is_json_error(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'d.docx').write_text('not a zip')
            code,r=self.run_cli('check','d.docx',cwd=d)
            self.assertEqual(code,2);self.assertIn('error',r)

    def test_state_protects_context_and_selected_profile(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'.reo').mkdir();(p/'.reo/profile.md').write_text('- 分野: 材料')
            (p/'draft.md').write_text('claim');(p/'graph.json').write_text(json.dumps({'nodes':[{'id':'claim','path':'draft.md'}]}))
            (p/'context.json').write_text('{}')
            for target in ('context.json','.reo/profile.md'):
                code,r=self.run_cli('state','graph.json','--context','context.json','--save',target,cwd=d)
                self.assertEqual(code,2);self.assertIn('overwrite',r['error'])
    def test_malformed_graph_and_previous_return_json_error(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for graph in ([],{'nodes':[None]}):
                (p/'graph.json').write_text(json.dumps(graph))
                code,r=self.run_cli('state','graph.json',cwd=d)
                self.assertEqual(code,2);self.assertIn('error',r)

    def test_nonfinite_target_preserves_deterministic_report(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'d.md').write_text('# test');(p/'d.csv').write_text('id,y\na,0.1\nb,0.2\nc,0.3\nd,0.4\ne,nan\n')
            code,r=self.run_cli('check','d.md','--data','d.csv','--target','y',cwd=d)
            self.assertEqual(code,1);self.assertEqual(r['data']['nonfinite']['y'],1)
            self.assertEqual(r['data']['evaluation_recommendation']['status'],'not_run')
    def test_nonfinite_context_leaves_no_saved_state(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'graph.json').write_text('{"nodes":[]}');(p/'ctx.json').write_text('{"model":NaN}')
            code,r=self.run_cli('state','graph.json','--context','ctx.json','--save','new.json',cwd=d)
            self.assertEqual(code,2);self.assertFalse((p/'new.json').exists())

    def test_default_output_bounded_but_saved_evidence_complete(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'d.md').write_text('# Results\n'+' '.join(str(i) for i in range(100)))
            code,r=self.run_cli('check','d.md','--save','check.json',cwd=d)
            self.assertEqual(code,0);self.assertEqual(len(r['document']['number_ledger']),20)
            self.assertEqual(r['document']['number_ledger_total'],100)
            self.assertEqual(len(json.loads((p/'check.json').read_text())['document']['number_ledger']),100)

    def test_unterminated_csv_quote_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'d.md').write_text('# test');(p/'d.csv').write_text('id,y\na,"1\n')
            code,r=self.run_cli('check','d.md','--data','d.csv',cwd=d)
            self.assertEqual(code,2);self.assertIn('error',r)

    def test_plan_preserves_review_gate_even_in_quick(self):
        code,r=self.run_cli('plan','--mode','quick','--task','peer_review')
        self.assertEqual(code,2);self.assertEqual(r['review_route']['assurance'],'research_strict')
        self.assertFalse(r['review_route']['review_completed'])
        code,r=self.run_cli('plan','--mode','quick','--available-reviewer','reviewer-1')
        self.assertEqual(code,0);self.assertEqual(r['review_route']['actual_reviewers'],[])
        self.assertEqual(r['review_route']['assigned_reviewers'],['reviewer-1'])
    def test_route_mechanical_does_not_invoke_reviewers(self):
        code,r=self.run_cli('route','--task-kind','mechanical')
        self.assertEqual(code,0);self.assertEqual(r['route'],'single_agent')
