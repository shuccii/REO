---
name: research-review-workflow
description: Audit scientific research, constructively review theses or papers, evaluate research plans, and rehearse interim or thesis defenses with source-grounded validity checks and adaptive follow-up questions. 日本語での依頼例は、研究の点検・監査、論文や修論の査読、主張と根拠の確認、研究計画の評価、中間発表・修論発表の模擬質疑。
---

# Research Review Workflow

研究の主張と根拠を点検し、修正案と確認条件を示します。研究成果の妥当性と、実行・書式の成功は別に判断します。

## User profile

If no profile exists, infer the field, methods and phase from the material, state that inference and do not block the task.

## Start and route

`<plugin root>` is two levels above this file. Run bundled Python tools by absolute path while keeping the user's workspace as cwd. Never cd into the plugin to resolve data paths.

1. Read the profile using `python3 <plugin root>/tools/reo_profile.py`. The current request overrides it. Missing profiles never block work; suggest setup at most once in the conversation.
2. Choose task: `peer_review`, `audit`, `supervision`, or `defense`. Choose **Standard** by default, **Quick** for an explicitly targeted/brief check, **Deep** for exhaustive or high-consequence review. A time limit alone does not authorize reducing required scope.
3. Run `python3 <plugin root>/tools/review_plan.py --mode standard --task peer_review --field 材料` with the actual mode/task/field; add `--long` for >8,000 words or >5 chapters, `--previous` when earlier reviews exist. Read only the returned references under this skill directory. Use `tools/reo.py plan` for a combined reading/review plan and `tools/reo.py state` for requested dependency-aware continuation. Supply observed `--available-reviewer` identities and any `--budget-json`; plans with a pending review gate do not prevent safe evidence acquisition but cannot authorize integration. Its required scientific review gates take precedence over mode convenience.
4. For search, read `references/evidence-acquisition.md` before searching. For registered lab policies/presentation/authorship use `../lab-policy-workflow/SKILL.md`. Read `references/review-report-contract.md` only for formal JSON reports. Use `../research-ml-workflow/SKILL.md` for executing experiments, statistical inference or integrating scientific results; its strict gates remain mandatory. For the full thesis schedule/slides/rehearsal preparation use `../thesis-defense-workflow/SKILL.md`. Standard/Deep stage criteria are in `references/phase-expectations.md`.

## Invariants in every mode

- State target/version, actual reading coverage, unassessed evidence and whether independent review occurred. A skeleton or excerpt is not full reading.
- Reconstruct the central claim and trace findings to exact evidence. Distinguish missing support, a demonstrated error and a plausible alternative explanation.
- Compute before a numerical finding; use `tools/` or Python and retain command and value. If unavailable, say **未計算**. Do not invent execution or raw data. Comparisons use `../research-ml-workflow/references/statistical-comparison.md` when applicable.
- Every finding includes severity, mechanism, correction and acceptance condition. Preserve supported strengths. Prioritize effects on the conclusion.
- All modes check the target's implications for abstract/conclusion and dependent claims. Central-claim risk or a cross-chapter contradiction expands the scope; report unresolved work if budget prevents that expansion.
- Never self-certify scientific validity from unit tests or schema checks. Consequential conclusions require independent semantic review; if unavailable, label the lead-only result preliminary and retain the pending review.
- For defense, ask one question at a time, wait through silence/self-correction, and give feedback after the rehearsal unless the user asks for advice.
- Save reviews only when requested; use `.reo/reviews/` and preserve prior finding IDs. No publication/submission without the user's authorization. Advice never substitutes for faculty approval.
