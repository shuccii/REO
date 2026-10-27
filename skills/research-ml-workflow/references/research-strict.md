# Strict research validation

Use the schemas and commands in `../../orchestrate-work/references/v0.3-contract.md`.

## Evidence chain

Retain raw-data identity and provenance, sample/group split assignments, per-transform fit samples, synthetic-sample parentage, model-selection history, raw predictions, metric configuration, seeds/repeats, baselines, environment, code/config/data hashes, and execution commands. Evidence must belong to the same run.

## Validity gates

- Data: units, missingness, duplicates, category normalization, physical constraints, and sensitivity to consequential imputation.
- Evaluation: group/time-aware splits, fold-local fitting, repeated evaluation, uncertainty, documented metric averaging, and an untouched final test.
- Target: distinguish continuous outcomes from data-derived class or cluster labels; fit data-derived labels on training data and limit claims accordingly.
- Interpretation: interpret only a validated model, compare material disagreements across models, and separate predictive association from causation.
- Optimization: use scientifically meaningful objectives, align decision variables with trained features, constrain feasibility, and report uncertainty/applicability domain. Nominal class numbers have no ordinal distance.
- Novelty: check training-set overlap and prior art. Distinguish known candidates, retrospective rediscovery, unvalidated prospective candidates, and prospectively validated findings.
- Reporting: reconcile sample counts, features, objectives, metrics, tables, figures, and prose. Mark preliminary or unavailable validation explicitly.

`not_applicable` requires a substantive task-specific reason. Missing evidence is not a pass. Completion requires an independent reviewer to cover design, data, execution, numerical results, interpretation, claims, and reproducibility.
