# Discipline probes (分野別の確認項目)

概要(日本語): 研究分野ごとの確認項目(probe)です。研究の分野と手法に合うファイルだけを読みます。適用しない項目は、その理由を記録します。

Read only the probe files that match the user's field and methods (from `RESEARCH_REVIEW_CONTEXT.md` or the user profile). Record which probes were applied and why others do not apply.

| Field / method | Probe file |
|---|---|
| Materials property prediction, data assimilation, Bayesian optimization | [materials-ml.md](materials-ml.md) |
| Wet-lab, biology, medicine, assays, cell or animal experiments | [bio-experimental.md](bio-experimental.md) |
| Chemistry, synthesis, spectroscopy, reaction analysis | [chemistry-synthesis.md](chemistry-synthesis.md) |
| Physics, mechanical, electrical, civil and other engineering measurements | [physics-engineering.md](physics-engineering.md) |
| Numerical simulation, analytic theory, mathematical models | [simulation-theory.md](simulation-theory.md) |
| Field studies, epidemiology, ecology, social or observational data | [field-observational.md](field-observational.md) |

Rules common to all probes:

- Do not impose a method the study did not use (for example, p-values on a pure proof, or a predictive benchmark on a mechanistic experiment).
- Probes are checklists for finding evidence gaps. A missing item is a question to answer, not proof of an error, unless the source shows the error.
- Domain conventions vary between subfields. When unsure, mark the item "not assessed" and ask the author or a domain expert.
