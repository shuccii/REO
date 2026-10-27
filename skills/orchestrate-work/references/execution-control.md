# Execution, review and recovery

Read this for delegated/reviewed runs, repair loops and final integration. It applies the v0.3 JSON contracts to Codex tools. It does not require any other plugin or agent names to be installed.

## Task handoff and status routing

Give a worker the task goal, acceptance criteria, input artifact versions, permitted writes/tools, necessary references, output path, budget and stop condition. Include prior findings and report paths on repairs. Supply enough context for a fresh worker, without copying the whole conversation or unrelated skills.

Use native v0.3 JSON fields. The legacy `STATUS` labels below are an interpretation guide, not additional JSON keys or enum values. A worker's completion report is not an integration decision.

| Worker observation / legacy label | Native Codex result and lead action |
| --- | --- |
| Work and checks finished (`DONE`) | `completed` only once all required checks and any independent review actually pass. Until then retain the pending evidence and a non-complete state; an implemented artifact awaiting required review is `needs_revision`. Inspect artifacts and send to review before integration. |
| Artifact exists with concerns (`DONE_WITH_CONCERNS`) | Record concerns in `risks` and follow-up in `next_actions`. Use `needs_revision` for unresolved correctness, scope or acceptance problems. Only non-blocking, explicitly scoped limitations may accompany `completed` after all required checks/review pass. |
| Missing information (`NEEDS_CONTEXT`) | `blocked` with `blocked_reason: external_dependency`; name the missing input/decision in `next_actions`. Supply it and update the task before retrying. |
| Cannot proceed (`BLOCKED`) | `blocked` with the actual schema-supported reason: `external_dependency`, `resource_unavailable`, `budget_exceeded` or `budget_unobservable`. Preserve the concrete cause in `summary`/`evidence` and change the prerequisite, task size or plan. |
| User approval needed for an external operation | A separate `approval_required` task uses `awaiting_approval` with pending approval. A blocked worker is not automatically an approval-operation task. Approval alone never means the operation succeeded. |
| Unrecoverable execution failure | `failed` with observed failure evidence and a recovery proposal; do not label this completed. |

Validate against the [contract](v0.3-contract.md). A `needs_revision` result is not integration eligible. Strict-research results in `completed` or `needs_revision` still require the research-contract fields and independent review mandated by that contract; if those are unavailable, report a valid `blocked` result with the actual reason instead of inventing review evidence.

Never retry an unchanged blocked task. Record which input, prerequisite, instruction, scope or plan changed and why. Do not silently substitute a different scientific method or relax acceptance criteria. Apply actual user/workspace authorization to environment changes; this workflow does not require a new approval for every reversible local dependency operation.

## Compact handoffs and risk-based review

Keep v0.3 schemas, required fields, enums and validation gates unchanged. The task card records `risk_class=low` or `risk_class=normal` and report/result paths in the existing manifest task `goal` string. The worker records the classification/rationale and report path in `summary`/`evidence`; concerns remain in `risks` and actions in `next_actions`. Do not add `risk`, `report` or other top-level fields, or introduce new `risk_tags` values.

A low card has no numerical results, no scientific claims, no applicable laboratory policy, and at most two artifact files. Otherwise classify normal; uncertainty means normal. This scheduling classification never downgrades `risk_tags`, verification mode, required checks, approval boundaries or `research_strict`. An implementation change still needs independent semantic review even if small.

Workers save full reports/results to the supplied paths; the return message contains native status, a three-line summary (result, checks, concerns) and paths. The lead validates the full structured result using the validator, inspects status/check outcomes, concerns and artifact/evidence indexes, and passes report paths to reviewers. It need not read the full narrative on a clean handoff. For non-completed states, concerns, invalid/missing evidence, failed review or a stop, read the relevant report sections before routing. Since an implementation awaiting review is `needs_revision`, inspect its pending-review concern; do not mislabel it `completed` to get a shorter route. Before integration the lead still opens final artifacts and checks every acceptance criterion; file handoff only reduces repeated narrative reading.

For independent low cards ready in the same wave, combine at most three in one reviewer invocation. Provide each card's criteria, inputs, diff, report path and check requirements. Produce a separate result and evidence mapping for each card, with the actual reviewer identity. A failing card never passes because another card passes; release only each card whose own dependencies/checks pass. Normal or uncertain cards receive individual review. A batched review retains all mandatory checks and the two-stage order for each card.

For a clean review, stage 1 and stage 2 each use one line in the supporting report: "Conforms: no missing, extra or mistaken work (criterion/evidence refs)" and "Mandatory checks passed / not applicable (checked scope and evidence refs)". Expand findings, failures or unassessed areas when present. Required JSON fields and individual semantic-review evidence remain complete; one-line prose does not waive a check or invent a passing result.

Batch independent reads/checks using the available tool orchestration; preserve individual outputs/exit codes and inspect each. Keep dependent steps, mutations and adaptive follow-ups sequential. Use focused source ranges and brief decisive log excerpts, retaining full evidence files for review.

## Observe real Codex handles

Use the agent/process identity returned by the available tool. Codex delegation is asynchronous; do not copy any background-run parameter from other tools. Preserve each returned identity exactly in result/reviewer fields.

Keep independent useful work moving, then wait on the known handle. A wait timeout or temporarily missing observation is not proof that work stopped. Inspect authoritative state and re-poll the same handle before deciding to restart. Do not duplicate live work. After confirmed termination, fix prerequisites or split/reduce the task before retrying. Repeated confirmed failures require root-cause investigation rather than an endless restart loop. Report resource unavailability according to the entrypoint's independent-review rule.

## Review in two stages

Review artifacts and their actual diff, not the implementer's self-assessment. Give reviewers the acceptance criteria, original inputs, artifact versions, scope, prior findings and evidence index. Do not pre-label likely defects as harmless.

Inventory the relevant worktree changes independently of the report's file list (`git status`, tracked diff and relevant untracked outputs). Follow changed data-loading/preprocessing dependencies when judging a plotting or metric claim. For "unchanged" claims, compare the prior/current artifacts or recompute within the allowed scope. Inspect the full source before asserting total row counts or exact line locators; a preview and a remembered trial history are insufficient.

1. **Requirements and scope:** map each criterion to an inspected file/line, cell, figure or command result. Identify missing work, unauthorized additions and solutions to a different problem. Treat a report's justifications as claims to verify. Requirements failure blocks acceptance even if tests pass.
2. **Quality and mandatory integrity checks:** assess relevant correctness, security/privacy, leakage, reproducibility, rules and error handling. If stage 1 fails, defer optional polish but still inspect mandatory integrity risks. Keep required `research_strict` review coverage and gates; a shorter preliminary review is not full-scope scientific approval.

Save the two-stage findings in a review artifact and reference it from the existing `semantic_review` check. Do not extend schemas with new top-level fields. Use a criterion/evidence table and record strengths and unassessed areas.

Severity follows evidenced impact: critical for fabricated evidence, leakage or defects changing central conclusions; major for failed acceptance, incorrect scope or unreliable output; minor for optional cosmetic improvements. Unauthorized data thinning is substantive even if described as readability. Distinguish demonstrated impact from plausible risk rather than calling every scope defect fabrication or a changed scientific conclusion. Required integrity checks and scientific readiness criteria cannot be downgraded to deferred minor work.

## Repairs and repeat review

Return substantive findings to the implementer with evidence, correction and acceptance conditions. Default to at most two repair/re-review rounds after the first review, capped by the manifest's smaller retry budget. Critical integrity failures or a prerequisite requiring a user decision stop the current loop immediately; preserve the evidence and report the needed decision. Record minor optional findings in the run summary rather than silently dropping them or reopening the repair loop.

On repeat review, check each previous finding as resolved/unresolved with fresh evidence, then inspect regressions caused by the repair. Avoid expanding into unrelated optional work. Newly discovered serious defects, unmet acceptance criteria and mandatory integrity checks still block acceptance; do not hide them because they were absent from the first review. Report these separately with their evidence.

The lead may implement a repair when appropriate, but that makes the lead an implementer for the changed scope: obtain independent review of the new diff before integration. Never turn a coordinator's own fix into self-approved review.

When the repair budget is exhausted, report the remaining defects and the decision needed to revise the plan. Do not manufacture a passing review or silently increase the budget.

## Evidence before completion

Immediately before a completion claim:

1. Re-read the goal and each acceptance criterion. Open the final artifacts and current diff; check all required deliverables, not only the recently edited part.
2. Run the checks needed for the current claim. Read their exit code, failure count, warnings and relevant output; retain command, version and evidence location. Verify a repair with the original reproducer. For generated files, parse/render as applicable; for numerical reports, read the saved outputs.
3. Inspect independent review and validate the run/results. A worker's report or a reviewer's assertion alone is insufficient. Preserve distinct worker/reviewer identities and do not mark required checks passed on another agent's behalf without its observed evidence.
4. State only what this evidence proves. Separate implemented, executed, structurally checked, semantically reviewed, scientifically valid, locally installed and externally published. Name failed, not-run and unavailable checks explicitly.

Keep worker-reported errors, inspected facts, computed results, hypotheses and proposed actions distinct. Do not invent a cell index, traceback line, project constraint, outlier, permission or completed approval/repair to fill a report. Verify locators against current bytes; support an outlier claim with an actual diagnostic or keep it a hypothesis. Proposed handoff text uses future/conditional language until the operation is observed. A verification command that failed or never ran cannot be summarized as passed.

For expensive immutable prior results, inspect current artifact hashes/provenance, scope and the recorded execution evidence rather than repeating an entire experiment solely for recency. Re-execute affected checks if inputs, code, environment or provenance changed. An old test result or cached success without this verification does not establish the current claim.

The final run summary includes criterion/evidence matches, actual checks, review/repair history, deferred minor findings, unresolved limitations and next actions. Keep the readable report proportional: a small mechanical task or decision can use a brief result, criterion/check evidence and remaining action. Reference the retained command log instead of duplicating long outputs or filling empty review sections; two-stage review is an order of checks, not a demand for verbose headings. Required structured result/research-contract fields still apply when their workflow applies. Mechanical direct-path tasks remain direct: this reference does not create manifests or delegation for a small file transformation.
