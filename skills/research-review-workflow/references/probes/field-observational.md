# Field and observational study probes

概要(日本語): フィールド調査、疫学、生態学、社会調査など観察データの研究で確認する項目です。交絡、標本設計、検出力、多重検定を点検します。

> 注意: この確認項目は文献と一般的な指針から合成した目安で、この分野の専門家による確認はまだ受けていません。分野の慣習と食い違う場合は、指導教員や専門家の判断を優先してください。

Apply to observational, survey, ecological, epidemiological or field-collected data.

- **Sampling design**: how units were selected, sampling frame, response rate or missingness, and whether the sample represents the target population.
- **Confounding**: variables that could drive both exposure and outcome; whether the analysis adjusts for them, and whether the adjustment itself could introduce bias (for example, a collider).
- **Causal language**: association in observational data is not causation. Check whether claims use causal wording and whether the design supports it (randomization, natural experiment, instrument, longitudinal control).
- **Power and sample size**: a priori or post hoc power justification; small samples with large effects reported with wide intervals.
- **Multiple testing**: number of outcomes, subgroups and models examined; correction method (for example, FDR) or explicit exploratory labeling.
- **Measurement validity**: instrument reliability and validity, observer agreement, and changes in measurement over time or site.
- **Temporal and spatial structure**: autocorrelation, clustering by site or time, and whether standard errors account for it.
- **Data handling**: exclusion rules stated before analysis; imputation method and sensitivity analysis when data are missing.
- **Ethics and permissions**: approvals, consent and data-sharing limits as recorded in the source. Record "not stated" when absent.
- **Tools** (optional, `requirements/base.txt`): `tools/power.py` for sample size, `tools/multiplicity.py` for FDR or FWER correction.
