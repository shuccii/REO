"""Check the additional unsaturated review cases are runnable, not quality scores."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'evals/bench'))
import run as runner
import grade as grader

class EvaluationCaseTests(unittest.TestCase):
    def test_all_new_tasks_have_fixed_inputs_prompts_and_rubrics(self):
        rubrics=grader.rubric_items((ROOT/'evals/bench/RUBRIC.md').read_text())
        for task in ('clean_short','insufficient','partial_pairing','cross_chapter','defense'):
            with self.subTest(task=task):
                self.assertIn(task,runner.PROMPTS);self.assertTrue(rubrics[task])
                self.assertTrue((ROOT/'evals/bench/inputs'/task/'manuscript.md').is_file())
                self.assertTrue(any(not item.startswith('X') for item in rubrics[task]))
