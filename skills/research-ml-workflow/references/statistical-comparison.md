# Statistical comparison and reporting (結果を統計的に示す)

概要(日本語): 予測して終わりにせず、「モデル A は B より良い」「処理で値が変わった」を統計的に示すための手順です。検定の選び方、交差検証の結果の比べ方、ばらつきと測定誤差の示し方、報告の書き方をまとめます。統計は主張を「証明」するものではなく、偶然では説明しにくいという根拠の強さを数値で示すものです。

## 0. Let the tools choose (自動選択)

Run the selector that matches the question before choosing a method by hand, and report its decision path:

| Question | Tool | What it chooses |
|---|---|---|
| How should the model be validated and scored? | `tools/choose_evaluation.py data.csv --target y [--group unit] [--time t]` | Split scheme (group, time, leave-one-out, repeated or plain k-fold), number of repeats, tuning rule, metrics, baselines |
| Is model A better than model B? | `tools/compare_models.py pred.csv --truth y --a A --b B [--fold f] [--group unit]` | Regression or classification from the labels; paired bootstrap CI, Wilcoxon or McNemar, corrected resampled t-test |
| Do conditions differ (treatment vs control, catalysts, time points)? | `tools/auto_test.py data.csv --value y --condition c [--unit u]` | Paired or independent; continuous or binary; Welch / Mann–Whitney / permutation; paired t / Wilcoxon / sign-flip; ANOVA + Tukey / Alexander–Govern + Welch / Kruskal–Wallis; RM-ANOVA / Friedman; Fisher / chi-square / McNemar / Cochran's Q; effect size and Holm-corrected post hoc tests |

Rules for automatic choice:

- The choice depends on the **design** (independent unit, pairing, number of conditions, data type) first, and on diagnostics (normality of standardized residuals or differences, equal variances, sample size) second. Name the independent unit with `--unit` / `--group`; without it every row is treated as independent.
- Run the selector once, before interpreting results. Do not switch to another test because its p-value is smaller. If there is a domain reason to override the choice (an established method in the field, a pre-registered plan), state the reason and report the selector's choice alongside.
- The tools cover the common designs. For nested or crossed random effects, censored data (survival), counts with overdispersion, or spatial/temporal autocorrelation, they say so only indirectly: use a mixed model, survival analysis, a GLM or a spatial model, and note that the tools did not apply.

## 1. Decide before testing

Write these down before looking at the comparison:

- **Claim**: what exactly will be compared (model A vs B on MAE; treatment vs control on yield) and in which direction.
- **Independent unit**: the thing that was sampled independently (film, patient, donor, composition, batch). Rows, replicate measurements, image fields and CV folds are usually not independent units.
- **Primary metric and threshold of practical importance**: the smallest difference that would matter in the application. A significant but tiny difference is reported as such.
- **Number of comparisons**: every model, metric, subgroup and time point that will be tested. Correct for them (`tools/multiplicity.py`) or label the analysis exploratory.

## 2. Choose the test

| Situation | Use | Avoid |
|---|---|---|
| Two models evaluated on the same held-out samples | Paired comparison of per-unit errors: bootstrap CI of the metric difference (resample independent units), Wilcoxon signed-rank on per-unit absolute errors | Comparing two means with an unpaired test |
| Two models compared across CV folds | Corrected resampled t-test (Nadeau and Bengio), with test/train size ratio | Ordinary t-test on fold scores: folds share training data, so it overstates significance |
| Repeated measurements of the same unit | Aggregate to the unit first, or use a mixed model with the unit as a random effect | Treating replicates as n |
| Two independent groups (treatment vs control) | Welch t-test (approximately normal) or Mann–Whitney U; report the difference with its CI | Student t-test with unequal variances |
| More than two groups | ANOVA / Kruskal–Wallis, then corrected post hoc tests (Tukey, Holm) | Many pairwise t-tests without correction |
| Proportions or classification accuracy on the same cases | McNemar test on disagreements | Comparing two accuracies as independent proportions |
| "No meaningful difference" | Equivalence test (TOST) against the practical threshold | Reading p > 0.05 as "no difference" |
| Small samples (n < 10 units) | Report every value and an exact or bootstrap interval; state that tests have little power (`tools/power.py`) | A single p-value as the main evidence |

For two regression models, run `tools/compare_models.py` from the plugin root. It gives the paired bootstrap CI, Wilcoxon test, paired effect size, the corrected resampled t-test with `--fold`, and the comparison with measurement repeatability with `--replicates`. Give `--group` whenever rows are not independent units. For repeated k-fold CV, pass `--test-fraction`.

## 3. Variation and error

- **Seed and split variation**: repeat training with several seeds and, for small data, repeated CV; report mean and SD across repeats, and say which source of variation the SD describes.
- **Interval vs SD**: SD describes spread; SE and CI describe the precision of a mean. Label which one is shown. `std / sqrt(n)` is an SE.
- **Measurement noise**: compare the model's RMSE with the repeatability SD of the measurement (repeated measurements of the same sample). An RMSE below the measurement noise is a warning sign of leakage or evaluation on near-duplicates, not a success.
- **Propagated uncertainty**: when a reported value is computed from measured quantities, propagate their uncertainty (`tools/uncertainty.py`).
- **Calibration of predicted uncertainty**: check that nominal 95% intervals contain about 95% of held-out values.

## 4. Report

Report, for each claim: the effect (difference) with its 95% CI, the test and its assumptions, the p-value, the independent unit and n, the number of comparisons and the correction, and the practical threshold. Example:

> GP の MAE はランダムフォレストより 0.30 eV 小さかった(差の 95% 信頼区間 0.21〜0.40、試料単位のブートストラップ、n = 60 試料)。5 分割交差検証での補正つき反復 t 検定は p = 0.005。両モデルの RMSE は測定の繰り返し誤差(0.32 eV)の 1.8〜2.9 倍であった。

Do not write that a result is "proven". Write what the interval and the test support, and the conditions under which it holds (data range, split design).
