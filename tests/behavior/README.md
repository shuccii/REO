# Agent behavior checks

These four fixture tasks test the consuming agent's behavior on input-only scenarios. They test the agent, not phrases in a SKILL.md.

1. Freeze the original and candidate skill files/commit hashes. Start a fresh agent for each version with the same model, tools and input-only `cases.json`. Copy each fixture to a disposable directory. Keep `rubric.md` and expected outcomes out of the worker context.
2. Load only relevant skills from that version. Let the worker act within fixture-only write scopes and retain actual commands, outputs, artifacts and final replies. The blocked-routing case is decision-only: no installation or real delegation.
3. An independent reviewer reads the traces and artifacts, then scores `rubric.md`, recording evidence per item and unassessed items honestly. Preserve safety and scope findings even if a numerical score is high.
4. Compare matched cases, including extra steps, questions, failures and unnecessary delegation. A single pair of runs is a smoke test; repeat independent runs before claiming reduced failures, latency or cost. Do not claim improvement from structural checks or matching prose.

These exercises are plugin-behavior tests, not scientific experiments. A scientific use of their sample data still requires the normal research_strict gates before scientific claims. No provider API, external service or optional numeric/plotting dependency is needed.

## Regression cases

`regression-cases.json` adds hidden loader changes, a misleading environment diagnosis, exhausted repairs with a mismatched reference, report-only obstacle evidence and a tiny Notebook task. The new fixtures are anonymous standard-library adaptations; plotting coordinates are exported to JSON so no optional numerical/plotting package is needed. Follow each setup in a disposable output directory. Keep genuine missingness distinct from a broken loader. The premise fixture's intentionally failing test is an input to the agent, not an expected passing test in the plugin suite.

Use `regression-rubric.md` only in the independent scorer context. Score actual acceptance-command execution, separate probes, saved derived values, current-state verification and factual provenance even if a final answer looks plausible. A recomputed metric cannot earn credit for a test command that never ran. Report format and substantive correctness have separate scores; a raw execution gap remains a gap after a reviewer performs the omitted check. Mask version/STATUS/boilerplate for initial substance scoring while retaining the original trace and locator map; if scoring is unblinded, disclose it. Keep time/token/tool-failure observations separate, and do not infer capability or speed improvements from one pair of exercises.
