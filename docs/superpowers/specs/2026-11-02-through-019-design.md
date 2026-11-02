# Re.O 0.17–0.19 design

User authorization: proceed through 0.19 while limiting usage (2026-11-02).

## Intent and approach

Connect existing planning to bounded local execution, offline comparisons and
verified restart. Reuse the current Python standard-library CLI and dependency
ledger. Avoid an autonomous agent framework or provider-specific billing adapter:
those alternatives add cost and cannot establish a hard monetary cap for an
opaque provider process. No live model benchmarks, automatic installation, push,
publication or user plugin activation in this implementation.

## 0.17 execution contract

A JSON plan declares workspace-local inputs, context, ordered DAG stages, commands
(argv, no shell), actors, outputs, timeout, experiments and resource estimates.
The runner executes only declared stages. Optional experiments require explicit
opt-in and a positive experiment cap. Each process returns one JSON receipt with
status and observed usage. Unknown usage under a corresponding budget prevents
further execution. Reserve required future work including review before launch;
exceeding estimates stops subsequent work. Wall time is enforced by terminating
the process group. Tokens/USD are admission and post-stage checks, not a hard
live provider cap. Commands are trusted, user-authorized programs, not sandboxed.

Review receipts bind distinct declared actor IDs to upstream artifact hashes and
a passed decision. Actor identity/independence is supplied by the host, never
claimed authenticated by this tool. Integration also requires a declared final
consistency stage. Safe deterministic-only plans need no independent review.

## 0.18 measurement

Produce an offline, serial-by-default experiment matrix with explicit model,
inputs/settings identity, repetition, arm and factor values. Compare paired rows
only when declared nuisance conditions match and the intended factor differs.
Include failed attempts in resource totals, preserve missing metrics as null,
reject malformed/nonfinite/duplicate observations. Reports are descriptive;
three repetitions do not establish noninferiority. No model launch from this tool.

## 0.19 checkpoint/restart

Atomically journal every launch before execution and every result after execution.
On restart verify plan/input/context/code identity and retained output hashes;
reuse only successful deterministic evidence. Invalidate affected descendants and
always rerun review and global consistency. An interrupted launch has unknown
usage and blocks budgeted restart until a new explicitly reconciled plan is made.
Persist cumulative usage including failed/repeated work. Checkpoints are local
evidence, not tamper-proof signatures or scientific approval.

## Acceptance

Adversarial tests cover budget reservation, failed/unknown usage, timeout children,
review binding, path protection, interrupted execution and changed dependencies.
Full existing suite remains green. Document new CLI, adapter receipt and honest
limits. Update both plugin manifests and marketplace to 0.19.0.
