"""Real local subprocess tests. No model services or paid commands."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import execution


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'input.txt').write_text('input')
        self.checkpoint = self.root / '.reo/run.json'
        self.plan = {'context': {'model': 'fixed'}, 'inputs': ['input.txt'],
                     'limits': {'seconds': 10, 'llm_calls': 10}, 'stages': []}

    def stage(self, name='build', kind='mechanical', deps=(), actor='worker', cost=1):
        script = ("import json,pathlib; "
                  f"pathlib.Path('{name}.txt').write_text('result'); "
                  "print(json.dumps({'status':'passed','usage':"
                  f"{{'llm_calls':{cost},'tokens':2,'cost_usd':0.01}}}}))")
        return {'id': name, 'kind': kind, 'actor': actor, 'depends_on': list(deps),
                'command': [sys.executable, '-c', script], 'outputs': [name + '.txt'],
                'estimate': {'llm_calls': cost, 'tokens': 2, 'cost_usd': .01}, 'timeout': 2}

    def run_plan(self, resume=False):
        return execution.execute(self.plan, self.root, self.checkpoint, resume=resume)

    def test_executes_declared_stages_and_records_observed_usage(self):
        self.plan['stages'] = [self.stage()]
        result = self.run_plan()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['usage']['llm_calls'], 1)
        self.assertTrue(self.checkpoint.exists())
        self.assertEqual(result['attempts'][0]['status'], 'passed')

    def test_reserves_future_work_before_starting(self):
        self.plan['limits']['llm_calls'] = 1
        self.plan['stages'] = [self.stage(), self.stage('next', deps=['build'])]
        result = self.run_plan()
        self.assertEqual(result['reason'], 'budget_insufficient')
        self.assertFalse((self.root / 'build.txt').exists())

    def test_unknown_usage_blocks_next_stage(self):
        first = self.stage()
        first['command'] = [sys.executable, '-c', "import pathlib; pathlib.Path('build.txt').write_text('x'); print('{\"status\":\"passed\"}')"]
        self.plan['stages'] = [first, self.stage('next', deps=['build'])]
        result = self.run_plan()
        self.assertEqual(result['reason'], 'budget_unobservable')
        self.assertFalse((self.root / 'next.txt').exists())

    def test_exceeding_estimate_stops_next_stage(self):
        first = self.stage(cost=8)
        first['estimate']['llm_calls'] = 1
        self.plan['limits']['llm_calls'] = 3
        self.plan['stages'] = [first, self.stage('next', deps=['build'])]
        result = self.run_plan()
        self.assertEqual(result['reason'], 'budget_exceeded')
        self.assertFalse((self.root / 'next.txt').exists())

    def test_experiments_need_explicit_permission_and_cap(self):
        self.plan['stages'] = [self.stage(kind='experiment')]
        result = self.run_plan()
        self.assertEqual(result['reason'], 'experiments_not_authorized')
        self.assertFalse((self.root / 'build.txt').exists())

    def test_implementation_requires_review_and_consistency(self):
        self.plan['stages'] = [self.stage(kind='implementation')]
        result = self.run_plan()
        self.assertEqual(result['reason'], 'review_required')
        self.assertFalse((self.root / 'build.txt').exists())

    def reviewed_plan(self):
        build = self.stage(kind='implementation')
        review = self.stage('review', 'review', ['build'], 'reviewer')
        review['command'] = [sys.executable, '-c',
            "import json,sys,pathlib; request=json.load(sys.stdin); "
            "pathlib.Path('review.txt').write_text('review evidence'); "
            "print(json.dumps({'status':'passed','usage':{'llm_calls':1},"
            "'review':{'actor':'reviewer','decision':'passed','reviewed':request['dependency_outputs']}}))"]
        final = self.stage('final', 'consistency', ['review'])
        self.plan['stages'] = [build, review, final]

    def test_review_binds_current_artifacts_and_distinct_actor(self):
        self.reviewed_plan()
        self.assertEqual(self.run_plan()['status'], 'completed')
        self.plan['stages'][1]['actor'] = 'worker'
        with self.assertRaisesRegex(ValueError, 'independent'):
            self.run_plan()

    def test_review_without_hash_binding_cannot_pass(self):
        self.reviewed_plan()
        self.plan['stages'][1]['command'] = self.stage('review')['command']
        self.assertEqual(self.run_plan()['reason'], 'review_evidence_invalid')

    def test_timeout_stops_execution(self):
        stage = self.stage()
        stage['command'] = [sys.executable, '-c', 'import time; time.sleep(3)']
        stage['timeout'] = .05
        self.plan['stages'] = [stage]
        self.assertEqual(self.run_plan()['reason'], 'timeout')

    def test_failed_exit_is_never_success_even_with_passed_receipt(self):
        stage = self.stage()
        stage['command'][-1] += '; raise SystemExit(1)'
        self.plan['stages'] = [stage]
        self.assertEqual(self.run_plan()['reason'], 'stage_failed')

    def test_invalid_budgets_and_paths_rejected_before_launch(self):
        for limit in (float('nan'), float('inf'), -1, True):
            with self.subTest(limit=limit):
                self.plan['limits']['llm_calls'] = limit
                with self.assertRaises(ValueError): self.run_plan()
        self.plan['limits']['llm_calls'] = 10
        stage = self.stage()
        self.plan['stages'] = [stage]
        for output in ('input.txt', '../escape', '.reo/run.json'):
            stage['outputs'] = [output]
            with self.subTest(output=output), self.assertRaises(ValueError): self.run_plan()

    def test_duplicate_stages_cycles_and_unknown_dependencies_rejected(self):
        stage = self.stage()
        for stages in ([stage, stage], [dict(stage, depends_on=['unknown'])],
                       [dict(stage, depends_on=['build'])]):
            self.plan['stages'] = stages
            with self.assertRaises(ValueError): self.run_plan()

    def test_restart_reuses_only_unchanged_mechanical_evidence(self):
        self.plan['stages'] = [self.stage()]
        first = self.run_plan()
        second = self.run_plan(resume=True)
        self.assertEqual(second['status'], 'completed')
        self.assertEqual(second['reused'], ['build'])
        self.assertEqual(len(second['attempts']), 1)
        self.assertEqual(second['usage']['llm_calls'], first['usage']['llm_calls'])

    def test_changed_inputs_context_command_or_output_invalidate_restart(self):
        for change in ('input', 'context', 'command', 'output'):
            with self.subTest(change=change):
                self.setUp()
                self.plan['stages'] = [self.stage()]
                self.run_plan()
                if change == 'input': (self.root / 'input.txt').write_text('changed')
                elif change == 'context': self.plan['context']['model'] = 'other'
                elif change == 'command': self.plan['stages'][0]['command'][-1] += '; pass'
                else: (self.root / 'build.txt').write_text('tampered')
                result = self.run_plan(resume=True)
                self.assertEqual(result['reused'], [])
                self.assertEqual(len(result['attempts']), 2)
                self.assertEqual(result['usage']['llm_calls'], 2)

    def test_upstream_change_invalidates_descendants_even_if_output_bytes_match(self):
        self.plan['stages'] = [self.stage(), self.stage('next', deps=['build'])]
        self.run_plan()
        self.plan['stages'][0]['command'][-1] += '; pass'
        result = self.run_plan(resume=True)
        self.assertEqual(result['reused'], [])
        self.assertEqual(len(result['attempts']), 4)

    def test_unrelated_stage_can_still_be_reused(self):
        (self.root / 'other-input.txt').write_text('other')
        self.plan['inputs'].append('other-input.txt')
        a, b = self.stage(), self.stage('other')
        a['inputs'], b['inputs'] = ['input.txt'], ['other-input.txt']
        self.plan['stages'] = [a, b]
        self.run_plan()
        (self.root / 'input.txt').write_text('changed')
        result = self.run_plan(resume=True)
        self.assertEqual(result['reused'], ['other'])

    def test_review_and_global_consistency_rerun_on_restart(self):
        self.reviewed_plan()
        # A mechanical precursor is reusable; implementation and semantic gates are not.
        self.plan['stages'].insert(0, self.stage('prepare'))
        self.plan['stages'][1]['depends_on'] = ['prepare']
        first = self.run_plan()
        second = self.run_plan(resume=True)
        self.assertEqual(second['status'], 'completed')
        self.assertEqual(second['reused'], ['prepare'])
        self.assertEqual(len(second['attempts']), len(first['attempts']) + 3)

    def test_restart_cannot_reset_spent_budget(self):
        self.plan['limits']['llm_calls'] = 1
        self.plan['stages'] = [self.stage()]
        self.run_plan()
        (self.root / 'build.txt').unlink()
        result = self.run_plan(resume=True)
        self.assertEqual(result['reason'], 'budget_insufficient')
        self.assertEqual(len(result['attempts']), 1)

    def test_interrupted_launch_blocks_restart_without_guessing_usage(self):
        self.plan['stages'] = [self.stage()]
        self.run_plan()
        state = json.loads(self.checkpoint.read_text())
        state['attempts'][0].update(status='running', usage={})
        state.pop('checkpoint_hash', None)
        state['checkpoint_hash'] = execution.canonical(state)
        self.checkpoint.write_text(json.dumps(state))
        result = self.run_plan(resume=True)
        self.assertEqual(result['reason'], 'interrupted_usage_unknown')
        self.assertIsNone(result['usage']['llm_calls'])

    def test_corrupt_checkpoint_and_cross_workspace_restart_rejected(self):
        self.plan['stages'] = [self.stage()]
        self.run_plan()
        state = json.loads(self.checkpoint.read_text())
        state['attempts'][0]['usage']['llm_calls'] = 0
        self.checkpoint.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            self.run_plan(resume=True)

    def test_failed_attempt_usage_is_retained_on_retry(self):
        bad = self.stage()
        bad['command'][-1] += '; raise SystemExit(1)'
        self.plan['stages'] = [bad]
        self.run_plan()
        self.plan['stages'] = [self.stage()]
        result = self.run_plan(resume=True)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['usage']['llm_calls'], 2)

    def test_input_modification_cannot_pass(self):
        stage = self.stage()
        stage['command'][-1] += "; pathlib.Path('input.txt').write_text('modified')"
        self.plan['stages'] = [stage]
        self.assertEqual(self.run_plan()['reason'], 'artifact_invalid')

    def test_symlink_output_alias_is_rejected(self):
        (self.root / 'alias.txt').symlink_to(self.root / 'input.txt')
        stage = self.stage()
        stage['outputs'] = ['alias.txt']
        self.plan['stages'] = [stage]
        with self.assertRaises(ValueError): self.run_plan()

    def test_invalid_receipt_usage_does_not_become_free(self):
        stage = self.stage()
        stage['command'][-1] = stage['command'][-1].replace("'llm_calls':1", "'llm_calls':-1")
        self.plan['stages'] = [stage]
        result = self.run_plan()
        self.assertEqual(result['reason'], 'invalid_receipt')
        self.assertIsNone(result['usage']['llm_calls'])

    def test_mutation_of_already_completed_unrelated_evidence_cannot_pass(self):
        first, second = self.stage(), self.stage('other')
        second['command'][-1] += "; pathlib.Path('build.txt').write_text('mutated')"
        self.plan['stages'] = [first, second]
        self.assertEqual(self.run_plan()['reason'], 'artifact_invalid')

    def test_future_reuse_candidate_is_revalidated_after_another_stage_runs(self):
        first, second = self.stage(), self.stage('other')
        self.plan['stages'] = [first, second]
        self.run_plan()
        first['command'][-1] += "; pathlib.Path('other.txt').write_text('mutated')"
        result = self.run_plan(resume=True)
        self.assertEqual(result['status'], 'completed')
        self.assertNotIn('other', result['reused'])
        self.assertEqual((self.root / 'other.txt').read_text(), 'result')

    def test_budget_reservation_includes_review_and_consistency(self):
        self.reviewed_plan()
        self.plan['limits']['llm_calls'] = 2
        self.assertEqual(self.run_plan()['reason'], 'budget_insufficient')
        self.assertFalse((self.root / 'build.txt').exists())

    def test_a_review_without_final_consistency_cannot_integrate(self):
        self.reviewed_plan()
        self.plan['stages'].pop()
        self.assertEqual(self.run_plan()['reason'], 'consistency_required')

    def test_retries_are_explicit_and_capped(self):
        stage = self.stage()
        stage['command'][-1] += '; raise SystemExit(1)'
        self.plan['stages'] = [stage]
        self.run_plan()
        result = self.run_plan(resume=True)
        self.assertEqual(result['reason'], 'retry_limit_reached')
        self.assertEqual(len(result['attempts']), 1)
        self.plan['retry_limit'] = 1
        result = self.run_plan(resume=True)
        self.assertEqual(len(result['attempts']), 2)
        result = self.run_plan(resume=True)
        self.assertEqual(result['reason'], 'retry_limit_reached')

    def test_timeout_kills_child_process_group(self):
        child = "import pathlib,time; time.sleep(.4); pathlib.Path('child-marker').write_text('leaked')"
        stage = self.stage()
        stage['command'] = [sys.executable, '-c',
            f'import subprocess,time,sys; subprocess.Popen([sys.executable,"-c",{child!r}]); time.sleep(3)']
        stage['timeout'] = .1
        self.plan['stages'] = [stage]
        result = self.run_plan()
        self.assertEqual(result['reason'], 'timeout')
        import time
        time.sleep(.45)
        self.assertFalse((self.root / 'child-marker').exists())

    def test_concurrent_executor_cannot_share_budget_checkpoint(self):
        import fcntl
        self.plan['stages'] = [self.stage()]
        self.checkpoint.parent.mkdir(parents=True)
        with Path(str(self.checkpoint) + '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'in use'):
                self.run_plan()

    def test_cross_workspace_checkpoint_rejected(self):
        self.plan['stages'] = [self.stage()]
        self.run_plan()
        other = self.root / 'other-workspace'
        other.mkdir()
        (other / 'input.txt').write_text('input')
        checkpoint = other / 'run.json'
        checkpoint.write_bytes(self.checkpoint.read_bytes())
        with self.assertRaisesRegex(ValueError, 'workspace'):
            execution.execute(self.plan, other, checkpoint, resume=True)

    def test_hardlink_output_alias_is_rejected_before_input_can_be_damaged(self):
        import os
        os.link(self.root / 'input.txt', self.root / 'build.txt')
        self.plan['stages'] = [self.stage()]
        with self.assertRaises(ValueError): self.run_plan()
        self.assertEqual((self.root / 'input.txt').read_text(), 'input')

    def test_hardlink_aliases_between_stage_outputs_rejected(self):
        import os
        (self.root / 'build.txt').write_text('existing')
        os.link(self.root / 'build.txt', self.root / 'other.txt')
        self.plan['stages'] = [self.stage(), self.stage('other')]
        with self.assertRaises(ValueError): self.run_plan()

    def test_checkpoint_lock_hardlink_to_input_rejected(self):
        import os
        self.checkpoint.parent.mkdir(parents=True)
        os.link(self.root / 'input.txt', Path(str(self.checkpoint) + '.lock'))
        self.plan['stages'] = [self.stage()]
        with self.assertRaises(ValueError): self.run_plan()


if __name__ == '__main__':
    unittest.main()
