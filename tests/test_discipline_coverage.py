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
        self.assertIn('~/.config/lab-advisor/profile.md', text)
        self.assertIn('Never write the profile inside the plugin folder', text)

    def test_institution_template_requires_confirmed_or_unconfirmed(self):
        text = (ROOT / 'skills/thesis-defense-workflow/references/institution-template.md').read_text()
        self.assertIn('confirmed (source:', text)
        self.assertIn('unconfirmed', text)


if __name__ == '__main__':
    unittest.main()
