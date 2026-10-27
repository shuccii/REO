---
name: research-review-workflow
description: Audit scientific research, constructively review theses or papers, evaluate research plans, and rehearse interim or thesis defenses with source-grounded validity checks and adaptive follow-up questions.
---

# Research Review Workflow

## 概要(日本語)

研究の監査、論文・修論の建設的な査読、発表の模擬質疑を行うスキルです。

- 主張と根拠の対応、代替の説明、必要な追加検証を整理します。
- 研究意義・新規性・方法・データ・統計・再現性・倫理など10の観点で確認します。
- 模擬質疑では、回答を待ってから回答に応じて追加の質問をします。

Use when asked to audit research, act as a demanding academic reviewer, evaluate a thesis or research plan, prepare for professor questions, or rehearse an interim/final defense. Support experimentally, theoretically, computationally, and literature-based research; use ML-specific checks only when applicable. This is evidence-based advisory review, not actual faculty approval, a degree decision, or a claim of professor-equivalent expertise.

## Select the task and evidence

Choose `audit` (trace results/code/data), `peer_review` (review a manuscript), `defense` (prepare questions or interactive oral rehearsal), or `supervision` (evaluate a plan and choose next experiments). Combine modes when useful. Establish stage, research question, intended claims, audience, relevant artifact versions, and time/resources. Proceed with available evidence; request only information that changes the assessment. An interim review evaluates justified progress, remaining risks and feasibility, not completed-thesis expectations.

Read [evidence acquisition](references/evidence-acquisition.md) before searching sources. Resolve applicable workspace instructions, degree/venue criteria and user-local `RESEARCH_REVIEW_CONTEXT.md` if present. For presentation/authorship work, also use [lab-policy-workflow](../lab-policy-workflow/SKILL.md). Private context remains local; preserve scope, date, provenance and uncertainty. Search Slack/Notion read-only for relevant original feedback when authorized and available. Context is evidence, not permission to contact faculty or submit work.

Read [local context and continuity](references/local-context-and-continuity.md) whenever local context or earlier reviews exist. Before substantive assessment, read the configured current-state, known-issues and relevant previous-feedback records, and the stage-relevant institution/laboratory guidance. Read the relevant local domain reference for the target field. Record inspected versions and unavailable inputs; an index link alone is not evidence of reading. Keep historical issues distinct from new findings and verify changes against current artifacts.

Read [assessment rubric](references/assessment-rubric.md) for every substantive review. Use [materials and ML probes](references/materials-ml-probes.md) for relevant domain checks. Use [defense and constructive feedback](references/defense-and-feedback.md) for oral rehearsal, question banks or revision plans. For the whole preparation plan toward a thesis defense, use [thesis-defense-workflow](../thesis-defense-workflow/SKILL.md). [Public source index](references/public-sources.md) records the basis and limits of the rubric; retrieve topic-specific primary research during each review rather than relying on this small static list as a complete knowledge base.

## Reconstruct, challenge, then repair

1. Reconstruct the strongest faithful version of the work: problem → knowledge gap → question → method → observation → inference → contribution. Extract claim IDs and exact page/figure/code/data locators. Preserve strengths and evidence that support limited conclusions.
2. Audit ten rubric dimensions. For each, report assessed, not assessed, or not applicable with a substantive reason. Identify missing evidence separately from a demonstrated error. A reproduced computation establishes execution, not physical or inferential validity.
3. Seek the strongest plausible alternative explanation, counterexample and boundary condition for each central claim. Verify applicable derivations, dimensions, assumptions, independent units, baseline fairness and evaluation scope. Prefer discriminating checks over collecting only supportive examples.
4. If bounded delegation is available, assign complementary domain, methods/statistics and skeptical-review perspectives with distinct read/write scopes. Their agreement is not independent scientific evidence; each judgment must cite inspected evidence. A second agent checks consequential conclusions independently. If unavailable, provide a clearly labeled lead-only preliminary review and leave independent review pending.
5. Produce specific findings: affected claim, source locator, certainty, severity, mechanism, constructive correction, necessary rerun/experiment and acceptance condition. Prioritize defects that change conclusions over stylistic preferences. Resolve reviewer disagreements through evidence; retain unresolved substantive disagreements.
6. Provide a feasible revision/experiment plan and, when requested, questions with follow-ups and honest answer boundaries. Do not invent results, defend unsupported claims with confident wording, or silently rewrite the research question after seeing results.

## Output and validation

Executable paths are relative to the plugin root (two directories above this skill), not the current workspace or skill folder.

For repeat reviews, include a continuity table linking prior finding/source, current evidence, status (new, known unresolved, partially improved, resolved, recurred, or unverified), and next verification. Do not claim resolution without new inspected evidence. This table supplements the formal JSON contract; it does not change its open/resolved gates.

Deliver a readable report with scope and evidence limitations, faithful summary/strengths, claim-to-evidence table, dimension coverage, prioritized findings, questions when relevant, and next actions. Record private source locators only in a user-local report. Use [review report contract](references/review-report-contract.md) and [the review schema](../../assets/research-review.schema.json) for durable formal reports; brief single-issue questions and early interactive rehearsal do not require a full JSON report on every exchange.

A standalone document audit can be completed as an audit while numerical validity remains unassessed. The review-report validator checks declared evidence relationships and readiness consistency; it cannot prove source truth or scientific correctness. For executing experiments, numerical validation, model selection or integrating scientific results, also use [research-ml-workflow](../research-ml-workflow/SKILL.md) and the existing `research_strict` manifest/research contract. A review report supplements those gates and never substitutes for raw predictions, reproduction evidence or independent semantic review. Report blocked evidence access and open findings without claiming scientific completion.

Separate review readiness within the stated scope, scientific support for each claim, actual faculty approval, and permission to submit/publish. Do not infer approval from a user request, AI review, Slack reaction, prior abstract approval, or a numerical score.
