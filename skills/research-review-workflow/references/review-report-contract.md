# Review report contract (additive v0.4.0)

Use [the schema](../../../assets/research-review.schema.json) and [the validator](../../../scripts/validate_research_review.py). All command paths below are relative to the plugin root. Existing task/research contracts remain v0.3.0. A formal review report is a standalone advisory evidence ledger, not a replacement for strict experiment validation.

```bash
python3 -B scripts/validate_research_review.py --json review-report.json
```

The CLI returns 0 for contract-valid data, 1 for invalid report data/JSON, and 2 for invocation/file access errors. It always reports `scientific_validity: not_established`. Source locators are inert strings: the validator does not read evidence files, retrieve URLs, or establish authenticity/approval. Independent inspection remains necessary.

## Fields

- `schema_version: "0.4.0"`, stable `report_id`, `review_mode`: audit, peer_review, defense or supervision.
- `scope`: subject, included areas, excluded areas and limitations. Identify artifact versions and stage here.
- `sources`: source_id, title, locator (exact page/line/figure/message plus artifact version), access public/private, observed_at UTC RFC3339 ending in Z, status read/partial/unavailable, limitations. Multiple passages can have separate source IDs. Partial/unavailable records require limitations; unavailable records cannot support an evidence reference.
- `claims`: claim_id, text, original locator, status supported/limited/unsupported/invalidated/not_assessed, evidence_refs (source IDs), material_limitations. Limited claims require explicit substantive limits. Supported/limited/invalidated claims need evidence; partial-only sources cannot fully support a claim.
- `coverage`: exactly the ten dimension IDs in the assessment rubric, each with assessed/not_assessed/not_applicable, reason and evidence_refs. Assessed requires evidence; N/A requires a scope-specific explanation of at least 20 characters (a mechanical lower bound, not proof of relevance). Missing evidence is not N/A.
- `findings`: finding_id, severity critical/major/minor, state confirmed/suspected, resolution open/resolved, affected_claims, evidence_refs, mechanism, correction, acceptance_condition, resolution_evidence_refs. Confirmed defects require evidence; resolution requires at least one read source with a distinct source ID and a different locator/version from the original finding evidence (aliasing the original locator is rejected). Record rerun/experiment scope in correction and acceptance_condition.
- `questions`: claim_id, question, followup, evidence_needed (descriptions), answer_boundary. These describe needed evidence without implying it exists. All questions reference real report claims.
- `unresolved`: issue, affected_claims, evidence_needed, impact material/minor. Unavailable raw data, contradictory evidence and missing specialist review belong here.
- `next_actions`: action, related_findings, acceptance_condition. Priority/dependencies/time/cost can be included in action prose when known.
- `readiness`: ready_within_scope/revision_required/insufficient_evidence. Ready requires no open critical/major finding (including suspected ones), every dimension assessed or justified N/A, every claim supported/limited, and no material unresolved issue. A report can be fully written while readiness remains revision_required or insufficient_evidence.
- `faculty_approval`: status not_assessed/pending/confirmed and evidence_refs. Confirmed requires at least one read source of actual approval for the exact artifact/version/scope; this declaration is still not authenticated by the CLI. Approval and review readiness are independent.

Source/claim/finding IDs are globally unique. Unknown/duplicate references are rejected. Required fields cannot be replaced by extra properties. An intentionally synthetic example is in `tests/fixtures/research-review.valid.json`; it tests bookkeeping and must not be treated as a scientifically assessed report or copied wholesale into a real review.

## Integration and limits

For an actual experiment, append this report to the existing strict result's artifacts/evidence and use ordinary `review_findings`, `claim_evidence_map`, gate/invalidation and independent-review fields as required. Do not update existing schema versions to 0.4 or mark a failing strict task completed because the review JSON is valid.

The validator cannot verify that a source supports a sentence, a control is scientifically appropriate, an N/A reason is truthful, or an approval is genuine. Avoid claiming that passing these checks proves scientific validity. Review multiple claims and dependencies explicitly; when a demonstrated defect invalidates results, propagate that status through the strict result's downstream artifacts.
