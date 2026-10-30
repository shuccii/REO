import importlib.util, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bench_runtime',ROOT/'evals/bench/runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)

class BenchRuntimeTests(unittest.TestCase):
    def test_identity_changes_with_code_model_settings_and_input(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'input.md').write_text('a')
            kw=dict(source='rev1', model='fixed-model', settings={'mode':'standard'}, prompt='review')
            base=runtime.identity(p,**kw)
            self.assertEqual(base,runtime.identity(p,**kw))
            for key,value in [('source','rev2'),('model','other'),('settings',{'mode':'quick'}),('prompt','changed')]:
                self.assertNotEqual(base,runtime.identity(p,**dict(kw,**{key:value})))
            (p/'input.md').write_text('b');self.assertNotEqual(base,runtime.identity(p,**kw))

    def test_usage_uses_authoritative_result_without_double_counting(self):
        events=[{'type':'assistant','message':{'usage':{'input_tokens':200}}},
                {'type':'result','usage':{'input_tokens':12,'output_tokens':3,'cache_read_input_tokens':4},'total_cost_usd':.1}]
        r=runtime.usage(events)
        self.assertEqual(r['input_tokens'],12);self.assertEqual(r['output_tokens'],3)
        self.assertEqual(r['cache_read_input_tokens'],4);self.assertIsNone(r['reasoning_tokens'])
        self.assertIsNone(runtime.usage([])['input_tokens'])

    def test_failed_or_different_runs_are_not_reused(self):
        self.assertFalse(runtime.reusable({'identity':'a','exit':1},'a'))
        self.assertFalse(runtime.reusable({'identity':'a','exit':0},'b'))
        self.assertTrue(runtime.reusable({'identity':'a','exit':0,'completed':True},'a'))
        self.assertFalse(runtime.reusable({'identity':'a','exit':0},'a'))

class UsageDetailTests(unittest.TestCase):
    def test_reasoning_details_and_per_model_fallback(self):
        r=runtime.usage([{'type':'result','usage':{'output_tokens_details':{'reasoning_tokens':7}},'modelUsage':{'m':{'inputTokens':12,'outputTokens':6,'cacheReadInputTokens':4,'cacheCreationInputTokens':2}}}])
        self.assertEqual(r['reasoning_tokens'],7)
        self.assertEqual(r['input_tokens'],12)
        self.assertEqual(r['cache_creation_input_tokens'],2)
