import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from review_state import build,compare

class ReviewStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        for f in ('data.csv','methods.md','claim.md','abstract.md'): (self.root/f).write_text(f)
        self.graph={'nodes':[{'id':'data','path':'data.csv'}, {'id':'methods','path':'methods.md','depends_on':['data']},
                             {'id':'claim:C1','path':'claim.md','depends_on':['methods']},
                             {'id':'abstract','path':'abstract.md','depends_on':['claim:C1'],'always_review':True}]}
        self.ctx={'plugin':'0.15','model':'fixed','tools':'hash','profile':'hash'}
    def test_changed_data_invalidates_transitive_claims(self):
        old=build(self.graph,self.root,self.ctx);(self.root/'data.csv').write_text('changed')
        r=compare(old,build(self.graph,self.root,self.ctx))
        self.assertEqual(r['changed'],['data'])
        self.assertEqual(set(r['invalidated']),{'data','methods','claim:C1','abstract'})
        self.assertFalse(r['semantic_review_completed'])
    def test_unchanged_reuses_but_global_check_required(self):
        state=build(self.graph,self.root,self.ctx);r=compare(state,state)
        self.assertIn('claim:C1',r['reusable_evidence']);self.assertEqual(r['always_recheck'],['abstract'])
        self.assertTrue(r['global_claim_consistency_required'])
    def test_context_and_graph_change_invalidate(self):
        old=build(self.graph,self.root,self.ctx)
        self.assertEqual(len(compare(old,build(self.graph,self.root,dict(self.ctx,model='other')))['invalidated']),4)
        self.graph['nodes'][2]['depends_on']=['data']
        self.assertIn('claim:C1',compare(old,build(self.graph,self.root,self.ctx))['invalidated'])
    def test_deletion_invalidates_and_is_not_reusable(self):
        old=build(self.graph,self.root,self.ctx);(self.root/'data.csv').unlink()
        r=compare(old,build(self.graph,self.root,self.ctx))
        self.assertIn('data',r['missing']);self.assertNotIn('data',r['reusable_evidence'])
    def test_rejects_cycles_unknown_dependencies_traversal_and_duplicates(self):
        for graph in ({'nodes':[{'id':'a','path':'claim.md','depends_on':['a']}]},
                      {'nodes':[{'id':'a','path':'claim.md','depends_on':['x']}]},
                      {'nodes':[{'id':'a','path':'../outside'}]},
                      {'nodes':[{'id':'a','path':'claim.md'},{'id':'a','path':'claim.md'}]}):
            with self.subTest(graph=graph),self.assertRaises(ValueError):build(graph,self.root,{})
    def test_removed_dependency_invalidates_downstream(self):
        old=build(self.graph,self.root,self.ctx)
        self.graph['nodes']=self.graph['nodes'][1:];self.graph['nodes'][0]['depends_on']=[]
        r=compare(old,build(self.graph,self.root,self.ctx));self.assertIn('data',r['removed'])
        self.assertIn('claim:C1',r['invalidated'])
