---
name: research-ml-workflow
description: Build, execute, validate, and communicate research or analysis with strict leakage controls, reproducibility evidence, independent review, and claim-level validity gates.
---

# Research ML Workflow

## 概要(日本語)

機械学習や解析の研究を、データリークなどを防ぎながら厳密に検証するスキルです。

- 学習データと評価データの分け方(グループ単位の分割を含む)を先に固定します。
- 前処理や特徴量の選択は、学習データの中だけで行います。
- 予測の根拠と不確かさを記録し、因果的な解釈と予測上の関連を分けて書きます。

Use this skill when the user asks for machine-learning research, experiment execution, result validation, interpretation, figures, or slides.

For laboratory authorship, conference plans, abstracts, posters, or research presentations, also read [lab-policy-workflow](../lab-policy-workflow/SKILL.md) and resolve any applicable user-local policy before planning the deliverable. Scientific validation does not replace faculty review, rehearsal, or presentation approval required by that policy.

Automatically use the `research_strict` assurance profile. Start from a v0.3 research contract: research question, target definition, sample and independence units, allowed sources, claim scope, split strategy, selection protocol, compute budget, and final deliverable. Read [the strict validation guide](references/research-strict.md) before planning or validating the run. Do not infer an unsupported causal claim from predictive performance.

For research audits, thesis/paper review, research-plan evaluation, or interim/final defense preparation, also use [research-review-workflow](../research-review-workflow/SKILL.md). It adds source acquisition, argument/novelty/domain review, constructive findings and adaptive questions. Review documents do not replace the strict numerical validation gates below.

## User profile

At the start, run `python3 tools/reo_profile.py` from the plugin root (standard library only), or read `~/.config/reo/profile.md` directly. If the profile exists, use its field, methods, phase and institution to choose probes, criteria and templates, and state which ones you used. If it does not exist, infer the field, methods and phase from the material, use the matching probes, state the inference in one line, and suggest the `setup-profile` skill once; do not block the task. The current request overrides the profile.

## Recommended task graph

1. **Data auditor**: profile sources, sample counts, units, missingness, duplicates, leakage risks, and permitted transformations.
2. **Modeller**: implement a reproducible baseline and candidate models with fixed configuration files and seeds.
3. **Experiment runner**: execute only the approved configurations; retain commands, environment, logs, raw metrics, and generated figures.
4. **Validation reviewer**: independently check splits, leakage, fit scope, metric definitions, uncertainty, and reproducibility. Execution completion is not evidence of numerical validity.
5. **Interpreter**: compare verified results with the research question, state alternative explanations and limitations, and identify the next discriminating experiment.
6. **Presentation writer**: create figures and slides only from reviewed metrics and interpretations. Mark preliminary results and missing validation explicitly.

Run data auditing independently from literature or domain-context research. Do not start model comparison before the target and evaluation scheme are defined. Parallelise models only when they share a frozen dataset version and evaluation protocol.

## Diagnose unexpected results

For execution errors, NaN/inf, suspicious accuracy, unstable fits or unit mismatches, use [root-cause-debugging](../root-cause-debugging/SKILL.md). Identify the first invalid pipeline stage before changing data or code; retain row IDs, invalid/excluded counts, hypotheses, probes and the original failing reproducer. A repaired computation does not restore invalidated claims until the affected research gates and independent review pass. Read saved output artifacts before reporting numeric values.

Use [execution, review and recovery](../orchestrate-work/references/execution-control.md) for two-stage review and blocked-worker routing. Strict-research review coverage, schema fields and validity gates remain mandatory, including when an earlier requirements check fails.

## Required validation

- Confirm the split unit prevents information leakage; do not use random pixel splits when independent samples or regions are required.
- Fit preprocessing within each training fold only.
- Retain raw predictions or sufficient arrays to recompute reported metrics.
- Report variation across folds, seeds, or independent repeats where the design allows it.
- Support every comparative claim (model A better than B, treatment changes the outcome) with a statistical comparison on independent units: read [statistical comparison](references/statistical-comparison.md) and let the tools choose the method: `tools/choose_evaluation.py` for the validation scheme and metrics, `tools/compare_models.py` for model comparisons, `tools/auto_test.py` for comparisons between conditions. Report the decision path. Report the difference with its CI, the test, n and the correction for multiple comparisons. Compare errors with measurement repeatability when replicate measurements exist.
- Separate predictive association from causal interpretation.
- Record any unavailable raw data or unexecuted calculation as a limitation, not a result.

Require stable sample IDs and group-aware split assignments. Record the exact samples used to fit every learned transform. Fit imputation, scaling, feature selection, dimensionality reduction, clustering, and resampling inside training folds only; synthetic samples and their parents must remain in training. Do not use the final test set to select labels, K, features, thresholds, models, or hyperparameters.

If an upstream validity check fails, mark dependent metrics, model rankings, explanations, optimization outputs, figures, and conclusions invalidated. Preserve unaffected audit evidence. Findings must state a defect ID, affected claims, evidence, mechanism, correction, rerun scope, and acceptance condition.

Use `semantic_review_required` for research conclusions, statistical design, data leakage, and interpretation. Follow `orchestrate-work` for task manifests, structured results, review gates, and approval boundaries.
