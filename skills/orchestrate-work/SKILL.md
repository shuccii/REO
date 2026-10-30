---
name: orchestrate-work
description: Coordinate complex research work with bounded parallel tasks, machine-readable evidence, independent review, and explicit approval boundaries. 日本語での依頼例は、複数の作業の分担、並列作業、独立したレビュー、検証済みの成果の統合。
---

# Orchestrate Work

## 概要(日本語)

複数の作業を分担し、結果を検証してから統合するためのスキルです。

- 作業を依存関係の順に分け、必要な場合だけ並列で進めます。
- 作業結果は機械可読な形式で受け取り、独立したレビューを通してから統合します。
- 公開・提出・送信・デプロイなどは、必ず承認が必要な操作として扱います。

Use this skill when a request has independent workstreams, a research-to-deliverable pipeline, or a meaningful review or approval boundary. Handle a simple question, one-file edit, or strictly sequential change directly.

## Plugin paths

`<plugin root>` is the directory two levels above this `SKILL.md`; it contains `tools/`, `scripts/` and `assets/`. In Claude Code it is also `${CLAUDE_PLUGIN_ROOT}`. Call bundled tools and scripts by that absolute path (for example `python3 <plugin root>/tools/reo_profile.py`) and keep the working directory in the user's workspace, so that data, report and output paths stay relative to the workspace. Do not `cd` into the plugin. Every `tools/...`, `scripts/...` or `assets/...` path in this skill and its references means `<plugin root>/...`.

## User profile

At the start, run `python3 <plugin root>/tools/reo_profile.py` (standard library only; see *Plugin paths*), or read `~/.config/reo/profile.md` directly. If the profile exists, use its field, methods, phase and institution to choose probes, criteria and templates, and state which ones you used. If it does not exist, infer the field, methods and phase from the material, use the matching probes, state the inference in one line, and suggest the `setup-profile` skill once; do not block the task. The current request overrides the profile.

## Choose the direct path first

For a small, mechanically verifiable operation with no dependencies, parallel work, semantic risk, or approval boundary, the lead performs and checks it directly. Do not create a manifest or result contract, read orchestration schemas, delegate a worker, or wait for a reviewer just to format a file or run an existing check. Report the checked artifact and finish. This path does not enter the structured integration workflow below.

Keep small-task and decision-only reports brief: observed result, the checks/evidence, and any unresolved action. Do not load full review procedures or repeat template sections solely to make the report look complete. Preserve required checks and distinguish supplied reports from personally verified facts.

Code changes and scientific or factual judgments are not mechanical operations merely because tests can run. Keep their semantic review gate, even when implementation is performed directly.

## Use only the relevant procedure

The lead reads [execution, review and recovery](references/execution-control.md) for delegated/reviewed runs. Workers receive the inline instructions below and the task's required result/check fields; they need not load the lead's whole orchestration procedure. Reviewers receive the two-stage procedure and required check fields in their handoff. Use [root-cause-debugging](../root-cause-debugging/SKILL.md) for detailed diagnosis when the inline procedure is insufficient. Load domain references when their checks apply; scientific validity and policy checks remain mandatory.

## Worker instructions to copy into each handoff

Copy these instructions directly into work/compute handoffs, alongside the task's scope, result path and schema-required fields. A link to a debugging skill alone is insufficient.

- For errors, NaN/inf, unexpected accuracy or failed tests: reproduce, compare a working case, state one hypothesis, run a discriminating probe, then make one cause-directed repair. Execute and retain actual outputs; code inspection is not observed data. Do not conceal failures by dropping rows, suppressing warnings or selecting a favorable seed.
- Across read → preprocess → fit/evaluate, print shapes, columns, missing/non-finite counts, values and ranges in one diagnostic invocation (one Python command or disposable script). Inspect its output before choosing a repair. Stop a downstream stage that cannot safely consume invalid inputs and print that reason. After a loader repair, probe again before separately handling genuine missingness. Preserve that causal observation boundary.
- After three ineffective repair attempts (including prior attempts on this card), stop repairs, inspect current code and assumptions, retain the attempted hypotheses and return a valid blocked handoff with the decision needed. A smaller retry budget wins; safe execution of the original test is still allowed.
- Batch independent reads/checks in one tool orchestration, for example `Promise.allSettled` over tool calls. Inspect every result and exit code. Keep dependent operations, edits, approvals and adaptive follow-ups sequential. Do not batch a diagnostic with a repair selected before seeing its result.
- Read only relevant source ranges; use `rg`, head/tail or equivalent. Retain full command evidence in files and quote about five decisive output lines with their log paths. Broaden inspection for scope, integrity or a failed check.
- Save the full structured result and supporting report/evidence at the supplied paths. Reply with the native status, a three-line result/check/concern summary and paths. Keep unresolved concerns in `risks`/`next_actions`; implementation awaiting required review is `needs_revision`, never self-approved `completed`.

## Review routing by risk

Before delegated/reviewed work, use `python3 <plugin root>/tools/review_routing.py --task-kind <kind>` with actual risks, observed reviewer availability and any hard budget. Read [review routing](references/review-routing.md) for the contract. Mechanical checks without consequential interpretation take the single-agent path; research/statistics/leakage/central claims and implementation changes retain independent semantic review and required strict contracts. Mode convenience never overrides these gates. The planner does not spawn agents, verify identities, enforce runtime spending or prove review completion. Missing resources leave integration pending; safe evidence acquisition may continue. Never infer actual reviewers from assigned identities.

## Route the work

The lead owns the plan, final answer, validation rules, and integration. Delegate only bounded tasks with distinct outcomes and write scopes. Use at most three concurrent workers by default, and parallelize only when tasks have no dependency or write-scope conflict and coordination is likely to save time.

Give each worker its objective, acceptance criteria, versioned inputs, permitted paths and tools, necessary references, required artifacts and checks, budget, stop condition, output location and the inline worker instructions above. For code changes, use isolated worktrees or branches. A branch name alone is not isolation.

Treat delegation as started only after the spawn operation returns a concrete worker identity. Preserve that returned identity verbatim in worker/reviewer result fields. Never wait without a known target, and never infer successful delegation or review from an attempted call. If spawning is unavailable or fails, attempt it only once. Continue safe implementation in the lead when useful, but record the distinct reviewer task as `blocked` with `blocked_reason: resource_unavailable`; do not attach that reason to a completed or needs-revision implementation result. Leave lead integration incomplete until an identifiable reviewer actually returns evidence.

Use a task manifest when a run has more than three tasks, delegated work, dependency ordering, parallel candidates, budgets, approval-required operations, or strict research. Read [the v0.3 contract](references/v0.3-contract.md) before creating or validating a manifest or result.

For scientific audits, thesis/paper assessment, research-plan critique, and defense rehearsal, route to [research-review-workflow](../research-review-workflow/SKILL.md). For preparing a master's thesis defense end to end (schedule, slides, question bank, rehearsals, day-of), route to [thesis-defense-workflow](../thesis-defense-workflow/SKILL.md), which uses research-review-workflow for the substantive audit. Pure document critique may finish with scoped, explicitly unassessed numerical validity; executing experiments or integrating scientific claims still uses `research_strict`. Plugin/skill engineering itself uses `standard` with implementation/external-fact semantic review, rather than pretending to generate a scientific experiment.

## Validate and integrate

Workers save structured results in the run directory. Validate a manifest before delegation, then validate each result against that same manifest. A completed result without a manifest is not integration-eligible.

Keep execution success separate from scientific, technical, or factual validity. Require independent semantic review for research conclusions, external facts, statistical design, data leakage, security-sensitive work, and implementation changes. A unit-test pass confirms the tested behavior; it does not establish that a code change preserves intent.

Give reviewers the run and task contracts, relevant diff, artifact and evidence indexes, prior findings, and references needed for semantic judgment. Review requirements/scope before quality, while retaining mandatory integrity checks and strict-research coverage. Let reviewers retrieve additional source material when required. Use the execution-control procedure for status-sensitive recovery and repeat review; do not retry unchanged blocked work or integrate a lead-authored repair without independent review.

Integrate only results that pass the required checks and review. Before claiming completion, inspect the final artifacts and current diff, map every acceptance criterion to evidence, and run or verify the checks for the current claim as specified in execution-control. Report actual artifacts and checks, deferred minor findings, unresolved limitations, unavailable metrics, and approval-required next actions.

Select `research_strict` automatically for scientific research, statistical inference, machine-learning model construction or evaluation, scientific conclusions, research optimization, and research reporting. Routine aggregation, log inspection, file transformation and ordinary scripting stay on `standard` unless the user explicitly requests research-grade assurance. Strict research always uses a manifest and research contract; it never takes the direct path.

## Approval and budget boundaries

For laboratory authorship or conference/presentation tasks, read [lab-policy-workflow](../lab-policy-workflow/SKILL.md) and resolve applicable user-local policies. Record required faculty review, rehearsal, and approval separately from user authorization and technical/scientific validation. Do not embed internal laboratory rules in distributable artifacts.

Classify operations as `read_only`, `reversible_write`, or `approval_required`. Treat submissions, messages, publication, deployment, spending, production-data changes, and material deletion as approval-required. A manifest is a preflight record; enforcement comes from the active Codex sandbox and approval controls.

Represent approval operations as tasks. User approval authorizes the operation but does not complete it; release dependent tasks only after the operation succeeds and its result is verified. Present independent ready approvals together when useful.

Do not substitute turn or tool counts for unavailable LLM-call counts. If a hard budget depends on an unobservable metric, stop with `blocked_reason: budget_unobservable`.
