---
name: root-cause-debugging
description: Diagnose execution errors, failing tests, stalled work or unexpected numerical results before changing code, data or configuration. Use for NaN/inf, unstable fits, suspicious accuracy, unit mismatches and notebook execution problems.
---

# Root Cause Debugging

## 概要(日本語)

エラーや数値の異常が起きたとき、当てずっぽうに直さず原因を特定するスキルです。

- まず再現し、正常な例と比べてから、仮説を1つだけ立てて最小の検証をします。
- NaN や不安定な計算を、データの除外や値の置き換えで隠しません。
- 修正が3回うまくいかなければ、前提と計画をいったん見直します。

Written for Codex. Its approach draws on the systematic-debugging skill of Superpowers. Use the available tools and the target project's constraints; no Superpowers installation is required.

## Reproduce before repairing

1. Read the full error and warnings. Record the command, input version, interpreter/environment, seed and notebook execution order needed to reproduce it. Reproduce in a disposable output area when possible; preserve the original data.
2. Inspect recent changes and compare a working example. Across a pipeline, execute a small boundary probe showing actual columns, values, missing/non-finite counts, units and ranges (read → transform → fit → evaluate → plot) to locate the first invalid stage. Combine the stage probes in one diagnostic invocation (one Python command or disposable script), printing shapes as well as columns, missingness, values and ranges. Inspect that output before choosing a repair; stop unsafe downstream stages with an explicit reason. Code inspection alone does not establish the values returned by a loader.
3. State one hypothesis and its evidence. Run the smallest probe that distinguishes it from an alternative; change one factor at a time. An unsuccessful probe is evidence to revise the hypothesis, not permission to accumulate speculative fixes.
4. Before the repair, retain a minimal reproducer that fails for the observed reason. Make one cause-directed repair, rerun the same check, then the relevant surrounding checks. Verify the original symptom, not just a successful exit code.

When reproduction is unavailable, record what is missing and gather evidence. Do not present a guessed change as a verified fix.

Use the intended available interpreter and supported tool flags. For portable file inspection/edits or a bounded local command, prefer Python standard-library operations (including `subprocess.run(..., timeout=...)` when appropriate) over guessing platform-specific `sed -i`, `cat -A` or `timeout` availability. A shell-flag failure is not evidence that numerical dependencies need reinstalling. Retain failed probes and the later successful check separately.

## Numerical and research failures

| Observation | First checks |
| --- | --- |
| NaN/inf or unstable matrices | Source row IDs, missingness, log/division domains, units, conditioning and precision |
| Unexpectedly good accuracy | Duplicates/groups across splits, preprocessing fit scope, target leakage and test-driven selection |
| Large seed-to-seed changes | Sample size, split balance, optimizer convergence and evaluation variance |
| Report differs from saved values | Artifact version, cell order, stale output, units and rounding |
| Missing module or runtime library | Intended interpreter, declared dependencies, lockfile and platform/runtime compatibility |

Do not silently drop invalid rows, replace NaN with zero, suppress warnings or choose a favorable seed to make a result look valid. If exclusions or a changed method are justified, record row IDs/counts, the rule, rationale and effect; resolve consequential choices under the applicable research contract before making scientific claims. A diagnostic fit remains provisional.

When a loader defect and genuine missing measurements coexist, repair and probe the loader first, retaining its new output and remaining invalid rows. Then handle the independently justified missing-data rule in a separate step. Do not bundle a header repair with a mask that conceals whether the repair worked. Keep a proven computational cause distinct from an unresolved measurement explanation or scientific acceptance; do not relabel all three as "cause unknown".

For scientific work, keep `research_strict`: a failed validity gate invalidates dependent outputs and claims. Debugging success does not restore scientific validity; rerun the affected checks and independent review. Do not weaken the research question or acceptance criteria to make a repair pass.

## Bound the repair loop

After three ineffective repair attempts, stop the current repair loop, preserve evidence and reconsider data definitions, model assumptions, task boundaries or architecture with the lead. A smaller manifest retry/compute budget takes precedence. Record attempted hypotheses and the decision needed before continuing. This is a worker handoff rule, not a declaration that the entire user's goal is blocked.

Inspect the current files/constants/diff rather than assuming every historical trial was reverted. Stopping repairs still permits a safe bounded invocation of the original acceptance test to establish its current result. If it cannot run safely or within the available resources, name that reason and leave the current test status unverified; a separately recomputed metric is not the test's exit status. Do not edit tests, tolerances, data or formulas to satisfy an incompatible reference value.

For a stalled agent or process, inspect its actual returned handle and state first. An observation timeout is not a terminal failure. Continue observing a live task rather than launching a duplicate. After confirmed termination or a missing handle, reduce/split the task or repair the prerequisite before retrying; repeated confirmed failures call for a minimal reproducer and a revised plan.

## Evidence to return

Include the failing reproducer/output, hypothesis, discriminating probe, repair diff, successful and failed checks, and remaining uncertainty. Record unexecuted checks as not run.

For a numerical handoff, first reopen each saved output with a readback command, then map the reported keys/rows and observed values to that actual command/output evidence. This includes diagnostic counts and null/blocked results, not just fitted metrics. Printing an in-memory object while writing it does not inspect the saved artifact. The table below is one compact format; equivalent concise prose with the same artifact, key, evidence locator, value and validity scope is sufficient. Reference retained logs rather than duplicating them.

Compute every quantity presented as a new result through an executed calculation, including auxiliary estimates, activation energies and unit conversions; save the formula inputs/constants, units and computed values with the requested output, then read them back. A formula or plausible mental estimate is not an executed result. Supplied/reference values may be quoted with their provenance and must remain distinct from newly computed values. If a requested calculation is unavailable, retain the requested partial artifact with null/uncomputed fields and the reason rather than supplying an invented value or claiming the deliverable exists. Use permitted provisional diagnostics when useful, without promoting them to scientific acceptance.

| Saved artifact | Key/row | Executed readback command and observed value | Validity scope |
| --- | --- | --- | --- |
| Path of the actual output | Reported key or source row | Command that reopens the file, plus its returned value | Diagnostic, provisional or independently validated |

For JSON, a small Python command using `json.loads(Path(output_path).read_text())` and printing the reported keys is sufficient. Retain the actual command/output in the run evidence; the readable evidence mapping is not a new field in the JSON result contract.

When part of an orchestrated run, use the existing v0.3 result schema and the [execution-control status mapping](../orchestrate-work/references/execution-control.md); do not add new result enum values or infer independent review from a worker's own checks.
