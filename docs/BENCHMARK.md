# Reproducible benchmark harness

The harness runs research review/audit fixtures through fresh Claude Code processes. It records observed evidence; it does not imply an improvement in quality. Running or grading invokes a paid model and requires the operator's authorization. The offline tests never invoke a real model.

## Configuration and arms

Use a fixed model identifier with `--model MODEL` or `BENCH_MODEL`; there is no default model. Pin the CLI version in your environment and retain that installation when comparing runs. The harness records `claude --version`, requested and observed model, actual command, project setting source, allowed tools, explicit settings, timeout, prompt and SHA-256 fingerprints of inputs and actual plugin files. Plugin fingerprints cover intended source roots (`.claude-plugin`, `.codex-plugin`, `skills`, `tools`, `scripts`, `assets`, `requirements`, `commands`, `agents`, `hooks`, `docs`, `references`, `outputStyles`) and root skill/dependency declarations and manifest-declared source paths contained within the plugin; private environment/key files, symlinks and caches are excluded. The runner, runtime, grader, reporter and rubric are also hashed for every arm, including base. Uncommitted instruction/source edits are included.

- `base`: no benchmark plugin.
- `format-only`: bundled presentation guidance control, with no research checking instructions. The model may choose whether to activate its skill; observed activations are recorded.
- `current`: plugin source at `BENCH_CURRENT_PLUGIN`, which must point to a separate pinned baseline checkout.
- `reo`: this checkout's candidate source.

Legacy `mi`, `reo-cmd` and `mi-cmd` arms remain available; MI arms require `COMPARE_PLUGIN`. For an unbiased comparison keep task, model, settings, CLI, concurrency and repetitions matched. Project-level Claude settings inside input fixtures affect execution and are input-hashed. Host authentication/provider configuration can also affect execution and is intentionally not read or copied. Record provider/runtime constraints separately without secrets. Aliases that resolve to changing models weaken reproducibility even though the requested identifier is recorded.

```sh
export BENCH_CURRENT_PLUGIN=/path/to/pinned/baseline
python evals/bench/run.py paper_mat,paper_bio,audit_hard,multi_hard 3 2 base,format-only,current,reo --model FIXED_MODEL_ID
python evals/bench/grade.py --model FIXED_GRADER_MODEL_ID --workers 2
python evals/bench/report.py --output /path/to/report.json
```

The original positional task/repetition/worker/arm arguments remain supported. Programmatic callers may pass a JSON-serializable `settings` dictionary to `run(...)`; it is passed via `--settings` and included in the identity. Grading also accepts `BENCH_MODEL` when `--model` is absent.

## Retained evidence and reuse

`runs/TASK/ARM-REP/` contains original `inputs/`, the model's mutable `work/`, `prompt.txt`, `rubric.md`, raw `stream.jsonl`, stderr, final output and metadata. Source file hashes and input hashes identify the actual content used. Existing attempts are moved into unique `TASK/history/` directories when replaced; they are never silently deleted. Normal aggregation includes only the active attempt per task/arm/repetition, leaving history for audit.

A run can be reused only when its full identity matches, exit status is zero, a successful terminal result was observed, final output exists and retained input, final output, generated summary and raw stream hashes still match. Failed, timed-out and incomplete attempts remain recorded and are never reused. Interrupted Python processes may leave an incomplete directory; the next invocation archives it. CLI launch/version failures before an attempt starts raise an error. Do not launch concurrent harness invocations targeting the same task/arm/repetition directory.

Usage comes from the terminal result's authoritative `usage`, with complete per-model `modelUsage` fallback when provided. Input, output, cache read, cache creation and reasoning tokens remain null when absent; they are not estimated from text. Nested output reasoning details are supported. Cost is the reported USD total, elapsed time is wall time, and tool/skill activation counts come from actual stream events. Loaded plugins do not establish skill activation. Stream traces expose model-generated tool arguments; review them before sharing artifacts.

## Grading and reports

The grader sees the retained original inputs (including CSV data), run-specific rubric, final text and, for `multi_hard`, its generated summary. It receives no arm label in its prompt and has no tools. Its model identifier and CLI version are explicit. It retains the exact grade prompt, raw responses/errors and grader usage/cost when supplied. It validates complete defect and decoy IDs and allowed score ranges before saving `grade.json`. A separate `grade-meta.json` records the generated grade payload hash; cache reuse and reporting reject mutated parsed scores. A grade is reused only when model, CLI, prompt, original inputs, rubric and graded output hashes match. Legacy runs without input/rubric provenance cannot be graded reliably and must be rerun. Prior grade JSON is archived and removed from the active path before a replacement attempt, so a failed regrade cannot silently contribute the previous score. The rubric remains fixed; grader-model bias and stochasticity remain limitations.

The JSON report contains per-arm completed/graded counts, means, medians and totals with observation counts for usage, cost, latency, tool calls, rubric score, defect recall, decoy false positives and incorrect claims. Unknown values remain null. Incomplete attempts contribute observed resource costs but no quality score. Quality is admitted only after matching run identity and verifying retained inputs, rubric, grader prompt, raw stream and generated outputs against run/grade provenance; changed evidence is excluded. Pairwise quality deltas match task and repetition across completed graded arms with matching requested/observed model, inputs, settings/CLI configuration, rubric and grader model/CLI/source fingerprint. The grader source fingerprint identifies its prompt template while allowing each graded output to differ. Incompatible pairs are excluded and counted; they are descriptive, not a significance test or shared-seed experiment. Raw scores differ in possible maximum across tasks; inspect per-task evidence and normalized defect recall before interpreting a pooled score. Historical artifacts lack these new guarantees and should not be presented as newly reproduced results.

## Offline verification

```sh
/Users/t-shuichi/Developer/REO/.venv/bin/python -m unittest discover -s tests -p 'test_bench*.py'
```

Fixture tests replace subprocess execution, covering required model configuration, source edits invalidating cache, retained attempts and original inputs, timeout provenance, result usage and reasoning details, fixed-model grader cache and aggregate missing-value/paired behavior. They establish harness behavior, not model performance; no new quality or cost result is claimed without an authorized real run.
