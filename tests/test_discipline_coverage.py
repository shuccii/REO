"""Guards that discipline probes, the setup skill and the institution template stay wired up."""
import os
from pathlib import Path
import re
import unittest

ROOT = Path(os.environ.get('RDO_GUIDANCE_ROOT', Path(__file__).resolve().parents[1]))
PROBES = ROOT / 'skills/research-review-workflow/references/probes'
REQUIRED_PROBES = ['materials-ml.md', 'bio-experimental.md', 'chemistry-synthesis.md',
                   'physics-engineering.md', 'simulation-theory.md', 'field-observational.md']


class DisciplineCoverageTests(unittest.TestCase):
    def test_every_probe_exists_and_has_japanese_summary(self):
        for name in REQUIRED_PROBES:
            with self.subTest(probe=name):
                text = (PROBES / name).read_text()
                self.assertIn('概要(日本語)', text)

    def test_probe_index_links_resolve(self):
        text = (PROBES / 'README.md').read_text()
        for target in re.findall(r'\]\(([^)#]+\.md)\)', text):
            with self.subTest(link=target):
                self.assertTrue((PROBES / target).exists())

    def test_setup_profile_skill_keeps_profile_outside_plugin(self):
        text = (ROOT / 'skills/setup-profile/SKILL.md').read_text()
        self.assertTrue(text.startswith('---\nname: setup-profile\n'))
        self.assertIn('~/.config/reo/profile.md', text)
        self.assertIn('Never write the profile inside the plugin folder', text)

    def test_institution_template_requires_confirmed_or_unconfirmed(self):
        text = (ROOT / 'skills/thesis-defense-workflow/references/institution-template.md').read_text()
        self.assertIn('confirmed (source:', text)
        self.assertIn('unconfirmed', text)


    def test_research_skills_read_the_profile(self):
        for name in ('research-review-workflow', 'research-ml-workflow', 'thesis-defense-workflow',
                     'lab-policy-workflow', 'orchestrate-work'):
            with self.subTest(skill=name):
                text = (ROOT / f'skills/{name}/SKILL.md').read_text()
                self.assertIn('## User profile', text)
                self.assertIn('tools/reo_profile.py', text)
                self.assertIn('do not block the task', text)


class ProfileReaderTests(unittest.TestCase):
    def setUp(self):
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        import reo_profile as reader
        self.assertTrue(hasattr(reader, 'load'))
        self.reader = reader

    def write(self, directory, body):
        path = Path(directory) / 'profile.md'
        path.write_text(body, encoding='utf-8')
        return path

    def test_missing_profile_is_not_an_error(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            report = self.reader.load(Path(directory) / 'none.md')
        self.assertFalse(report['exists'])

    def test_template_fields_map_to_probes(self):
        import tempfile
        template = (ROOT / 'skills/setup-profile/references/profile-template.md').read_text(encoding='utf-8')
        filled = (template.replace('- 分野:', '- 分野: 化学')
                  .replace('- 主な手法:', '- 主な手法: 実験, 計算・シミュレーション, データ解析・機械学習')
                  .replace('- 今の段階:', '- 今の段階: 修論'))
        with tempfile.TemporaryDirectory() as directory:
            report = self.reader.load(self.write(directory, filled))
        self.assertTrue(report['exists'])
        self.assertEqual([Path(p).name for p in report['probes']], ['chemistry-synthesis.md', 'simulation-theory.md'])
        self.assertTrue(report['use_research_ml_workflow'])
        self.assertIn('institution', report['unset'])
        for path in report['probes']:
            self.assertTrue((ROOT / path).exists())

    def test_unset_values_are_none(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            report = self.reader.load(self.write(directory, '- 分野: 未設定\n- 主な手法: 観察・調査\n'))
        self.assertIsNone(report['profile']['field'])
        self.assertEqual([Path(p).name for p in report['probes']], ['field-observational.md'])


if __name__ == '__main__':
    unittest.main()
