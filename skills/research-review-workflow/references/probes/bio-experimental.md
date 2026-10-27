# Biology and wet-lab experiment probes

概要(日本語): 生物・医学・ウェット実験の研究で確認する項目です。対照群、反復の種類、バッチ効果、試薬や細胞株の同一性、統計の多重性などを点検します。

> 注意: この確認項目は文献と一般的な指針から合成した目安で、この分野の専門家による確認はまだ受けていません。分野の慣習と食い違う場合は、指導教員や専門家の判断を優先してください。

Apply when the study is an experiment with samples, cells, organisms, assays or clinical material.

- **Controls**: positive and negative controls, vehicle controls, and the reason each comparison is valid. A treatment without a matched control cannot show a specific effect.
- **Replication**: separate biological replicates (independent organisms, cultures, patients, preparations) from technical replicates (repeated measurements of one sample). Only biological replicates support general claims; pseudoreplication inflates significance.
- **Batch and run effects**: date, operator, reagent lot, plate position, instrument and passage number. Check whether groups were processed together or confounded with batch.
- **Identity and quality**: cell line authentication and mycoplasma status, strain or genotype confirmation, antibody validation and specificity (knockout or peptide controls where relevant), primer specificity and sequence verification.
- **Measurement**: linear range, saturation, background subtraction, normalization method and reference gene or loading control. Check that the normalization does not create the effect.
- **Statistics**: sample size or power justification, pre-specified endpoints, multiple-comparison correction across endpoints and time points, and whether the test matches the data (paired, nested, repeated measures).
- **Sequence and data leakage**: homology or near-duplicate sequences across train and test sets, shared donors or patients across groups, and selection of cases after seeing results.
- **Ethics and biosafety records**: animal or human-subject approval, consent, and the containment level of organisms or genetic modification, as stated in the source. Record "not stated" when absent; do not assume compliance.
- **Interpretation**: association versus mechanism; in vitro effects versus in vivo relevance; dose and time dependence; off-target effects and alternative pathways.
- **Tools** (optional): `tools/power.py` and `tools/multiplicity.py` (`requirements/base.txt`); `tools/sequence_identity.py` for train/test sequence leakage (`requirements/bio.txt`).
