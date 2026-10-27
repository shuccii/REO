import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / 'fixtures'
sys.path.insert(0, str(ROOT / 'scripts'))
from schema_subset import audit_schema
from validate_research_review import validate_research_review


def load():
    return json.loads((FIX / 'research-review.valid.json').read_text())


def finding():
    return {'finding_id': 'finding-1', 'severity': 'major', 'state': 'confirmed',
            'resolution': 'open', 'affected_claims': ['claim-1'],
            'evidence_refs': ['src-results'], 'mechanism': 'Confounding could explain the association.',
            'correction': 'Restrict the conclusion and assess confounding.',
            'acceptance_condition': 'Provide a sensitivity analysis with assumptions.',
            'resolution_evidence_refs': []}


class ResearchReviewTests(unittest.TestCase):
    def assert_invalid(self, data, fragment):
        errors = validate_research_review(data)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/validate_research_review.py'), '--json', *map(str, args)], capture_output=True, text=True)

    def test_observed_canonical_agent_identities(self):
        from schema_subset import validate
        import re
        schema = json.loads((ROOT / 'assets/task-result.schema.json').read_text())
        worker = schema['properties']['worker_id']
        for identity in ('agent-123', '/root', '/root/independent_review'):
            self.assertEqual(validate(identity, worker), [])
        for identity in ('/root/../other', '/root//other', '/root/', ''):
            self.assertTrue(validate(identity, worker))
            self.assertIsNone(re.search(worker['pattern'], identity))
        self.assertIsNone(re.search(worker['pattern'], 'prefix /root suffix'))
        review = schema['properties']['verification']['properties']['validity_review']['properties']['reviewer_id']
        self.assertEqual(validate(None, review), [])

    def test_schema_subset_supported(self):
        audit_schema(json.loads((ROOT / 'assets/research-review.schema.json').read_text()))

    def test_valid_limited_review_and_cli(self):
        self.assertEqual(validate_research_review(load()), [])
        result = self.cli(FIX / 'research-review.valid.json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertTrue(output['contract_valid'])
        self.assertEqual(output['scientific_validity'], 'not_established')

    def test_all_modes(self):
        for mode in ('audit', 'peer_review', 'defense', 'supervision'):
            data = load(); data['review_mode'] = mode
            self.assertEqual(validate_research_review(data), [])

    def test_revision_can_preserve_unassessed_and_unavailable(self):
        data = load(); data['readiness'] = 'insufficient_evidence'
        data['claims'][0].update(status='not_assessed', evidence_refs=[], material_limitations=[])
        data['sources'][1].update(status='unavailable', limitations=['Access unavailable.'])
        data['coverage'][1].update(status='not_assessed', reason='Missing prior-art sources.', evidence_refs=[])
        self.assertEqual(validate_research_review(data), [])

    def test_open_suspected_major_blocks_ready(self):
        data = load(); data['findings'] = [finding()]
        data['findings'][0].update(state='suspected', evidence_refs=[])
        self.assert_invalid(data, 'open critical/major')
        data['readiness'] = 'revision_required'
        self.assertEqual(validate_research_review(data), [])

    def test_confirmed_finding_requires_evidence(self):
        data = load(); data['readiness'] = 'revision_required'; data['findings'] = [finding()]
        data['findings'][0]['evidence_refs'] = []
        self.assert_invalid(data, 'confirmed finding requires evidence')

    def test_resolved_major_can_be_ready_only_with_evidence(self):
        data = load(); data['findings'] = [finding()]
        data['findings'][0]['resolution'] = 'resolved'
        self.assert_invalid(data, 'resolution evidence')
        data['findings'][0]['resolution_evidence_refs'] = ['src-results']
        self.assert_invalid(data, 'distinct read source')
        source = copy.deepcopy(data['sources'][0])
        source.update(source_id='src-correction', locator='synthetic-results-v2.md#sensitivity-check')
        data['sources'].append(source)
        data['findings'][0]['resolution_evidence_refs'] = ['src-correction']
        self.assertEqual(validate_research_review(data), [])

    def test_resolution_rejects_alias_and_partial_correction(self):
        data = load(); data['findings'] = [finding()]
        data['findings'][0].update(resolution='resolved', resolution_evidence_refs=['src-correction'])
        source = copy.deepcopy(data['sources'][0]); source['source_id'] = 'src-correction'
        data['sources'].append(source)
        self.assert_invalid(data, 'distinct read source')
        source.update(locator='synthetic-results-v2.md#sensitivity-check', status='partial', limitations=['Correction not fully inspected.'])
        self.assert_invalid(data, 'distinct read source')
        source.update(status='read', limitations=[])
        self.assertEqual(validate_research_review(data), [])

    def test_unknown_and_duplicate_source_refs(self):
        data = load(); data['claims'][0]['evidence_refs'] = ['src-results', 'src-results', 'missing']
        self.assert_invalid(data, 'duplicate references'); self.assert_invalid(data, 'unknown reference')

    def test_duplicate_source_claim_finding_dimension_ids(self):
        for key in ('sources', 'claims', 'coverage'):
            data = load(); data[key].append(copy.deepcopy(data[key][0]))
            self.assert_invalid(data, 'duplicate')
        data = load(); data['readiness'] = 'revision_required'; data['findings'] = [finding(), finding()]
        self.assert_invalid(data, 'duplicate finding_id')

    def test_cross_entity_id_collision(self):
        data = load(); data['sources'][0]['source_id'] = 'claim-1'
        self.assert_invalid(data, 'globally unique')

    def test_missing_dimension(self):
        data = load(); data['coverage'].pop()
        self.assert_invalid(data, 'too few items')
        data['coverage'].append(copy.deepcopy(data['coverage'][0]))
        self.assert_invalid(data, 'missing dimension')

    def test_unknown_claim_refs_and_action_refs(self):
        data = load(); data['questions'][0]['claim_id'] = 'missing-claim'
        self.assert_invalid(data, 'unknown reference')
        data = load(); data['next_actions'] = [{'action': 'Review evidence', 'related_findings': ['missing-finding'], 'acceptance_condition': 'Evidence confirmed'}]
        self.assert_invalid(data, 'unknown reference')
        data = load(); data['readiness'] = 'revision_required'; data['findings'] = [finding()]
        data['findings'][0]['affected_claims'] = ['src-results']
        self.assert_invalid(data, 'unknown reference')

    def test_unavailable_source_cannot_support_any_evidence(self):
        for section in ('claims', 'coverage', 'findings', 'faculty_approval'):
            data = load(); data['readiness'] = 'revision_required'
            data['sources'][0].update(status='unavailable', limitations=['Access denied.'])
            if section == 'findings': data['findings'] = [finding()]
            if section == 'faculty_approval': data[section].update(status='confirmed', evidence_refs=['src-results'])
            self.assert_invalid(data, 'unavailable source cannot be evidence')

    def test_blank_locator_and_blank_reason_rejected(self):
        data = load(); data['sources'][0]['locator'] = '   '
        self.assert_invalid(data, 'pattern mismatch')
        data = load(); data['coverage'][0]['reason'] = '\n \n'
        self.assert_invalid(data, 'pattern mismatch')

    def test_partial_source_and_limited_claim_need_limitations(self):
        data = load(); data['sources'][1]['limitations'] = []
        self.assert_invalid(data, 'partial/unavailable source requires limitations')
        data = load(); data['claims'][0]['material_limitations'] = []
        self.assert_invalid(data, 'limited claim requires material limitations')

    def test_partial_only_support_must_be_limited(self):
        data = load(); data['claims'][0].update(status='supported', evidence_refs=['src-protocol'])
        self.assert_invalid(data, 'partial-only evidence')

    def test_supported_invalidated_limited_claims_require_evidence(self):
        for status in ('supported', 'limited', 'invalidated'):
            data = load(); data['readiness'] = 'revision_required'; data['claims'][0].update(status=status, evidence_refs=[])
            self.assert_invalid(data, 'requires evidence')

    def test_false_ready_unassessed_or_unsupported(self):
        data = load(); data['coverage'][0]['status'] = 'not_assessed'
        self.assert_invalid(data, 'requires all dimensions assessed')
        for status in ('unsupported', 'invalidated', 'not_assessed'):
            data = load(); data['claims'][0]['status'] = status
            self.assert_invalid(data, 'requires every claim')

    def test_not_applicable_must_be_justified(self):
        data = load(); data['coverage'][0].update(status='not_applicable', reason='n/a', evidence_refs=[])
        self.assert_invalid(data, 'substantive scope-specific reason')
        data['coverage'][0]['reason'] = 'This dimension does not apply to the explicitly restricted synthetic comparison.'
        self.assertEqual(validate_research_review(data), [])

    def test_assessed_coverage_needs_evidence(self):
        data = load(); data['coverage'][0]['evidence_refs'] = []
        self.assert_invalid(data, 'assessed dimension requires evidence')

    def test_faculty_approval_is_not_inferred_from_contract(self):
        data = load(); data['faculty_approval']['status'] = 'confirmed'
        self.assert_invalid(data, 'confirmed approval requires evidence')
        data['faculty_approval']['evidence_refs'] = ['src-protocol']
        self.assert_invalid(data, 'requires at least one read source')
        data['faculty_approval']['evidence_refs'] = ['src-results']
        self.assertEqual(validate_research_review(data), [])
        data['faculty_approval']['status'] = 'not_assessed'
        self.assert_invalid(data, 'cannot assert approval evidence')

    def test_material_unresolved_blocks_ready(self):
        data = load(); data['unresolved'] = [{'issue': 'Confounding unresolved', 'affected_claims': ['claim-1'], 'evidence_needed': ['Control measurements'], 'impact': 'material'}]
        self.assert_invalid(data, 'material unresolved issues')
        data['readiness'] = 'insufficient_evidence'
        self.assertEqual(validate_research_review(data), [])

    def test_inert_locators_never_read(self):
        data = load(); data['sources'][0]['locator'] = '/etc/passwd; https://example.invalid/secret'
        original_read = Path.read_text
        paths = []
        def tracked_read(path, *args, **kwargs):
            paths.append(str(path)); return original_read(path, *args, **kwargs)
        with patch.object(Path, 'read_text', tracked_read):
            self.assertEqual(validate_research_review(data), [])
        self.assertEqual(paths, [str(ROOT / 'assets/research-review.schema.json')])

    def test_cli_invalid_data_exit_one(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'bad.json'; report.write_text('{}')
            result = self.cli(report)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)['contract_valid'])

    def test_cli_invocation_errors_exit_two(self):
        self.assertEqual(self.cli('/path-that-does-not-exist/review.json').returncode, 2)
        self.assertEqual(self.cli().returncode, 2)
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'bad.json'; report.write_text('{')
            result = self.cli(report)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['scientific_validity'], 'not_established')

    def test_schema_version_and_extra_properties(self):
        data = load(); data['schema_version'] = '0.3.0'
        self.assert_invalid(data, 'expected')
        data = load(); data['scientifically_correct'] = True
        self.assert_invalid(data, 'unexpected property')

    def test_multiline_explanations_allowed_and_observed_at_utc(self):
        data = load(); data['claims'][0]['text'] += '\nThe limit remains explicit.'
        self.assertEqual(validate_research_review(data), [])
        data['sources'][0]['observed_at'] = '2026-09-30T09:00:00+09:00'
        self.assert_invalid(data, 'UTC RFC 3339')


if __name__ == '__main__':
    unittest.main()
