# Expectations by phase (段階ごとの期待水準)

概要(日本語): 学生実験レポートから論文投稿まで、段階によって求める水準を変えます。学部生の卒論に修論や論文と同じ新規性を求めないようにするための基準です。

Use the `phase` from the user profile, or infer it from the material and state the inference. Apply every check that the material makes relevant, but set **severity and the expected standard** by phase. Never lower a standard for correctness: a calculation error, data leakage or a claim the evidence does not support is a finding at every phase.

| Phase | Main question | Expect | Do not require |
|---|---|---|---|
| 学生実験レポート (lab report) | Was the experiment done and reported correctly? | Purpose, principle, method, results, discussion; units, significant figures, error propagation, labelled axes and legends; discussion that compares results with theory or literature values | Novelty; a research question of the student's own |
| 輪講・論文紹介 (journal club) | Did the presenter understand the paper and its evidence? | Main claim in one sentence; the key figure and what it shows; method in the presenter's words; limitations the paper states and ones it does not | Original results |
| 卒論 (bachelor's thesis) | Is the problem clear and the work completed and honestly discussed? | Clear question, completed basic experiment or implementation, appropriate comparison, limitations stated, reproducible method | Academic novelty at publication level; a complete literature survey |
| 修論・学会発表 (master's thesis, conference) | Does the work answer a research question with adequate evidence? | Positioning against prior work, validity of design, uncertainty, alternative explanations addressed, claims matched to evidence | A finished, journal-level story when the thesis states its scope |
| 論文執筆 (journal paper) | Would the claims survive peer review? | Novelty and significance against current literature, strong baselines, ablations, reproducibility package, complete reporting | — |
| 研究の立ち上げ (planning) | Is the plan feasible and able to answer the question? | Question, hypothesis, measurable success criteria, method choice, feasibility, risks and a first experiment | Results |

Report the phase you used at the top of the review. If the phase is unknown, say so and use the 修論 row as the default, marking novelty-related findings as conditional on the phase.
