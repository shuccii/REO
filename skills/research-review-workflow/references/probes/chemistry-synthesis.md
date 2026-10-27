# Chemistry and synthesis probes

概要(日本語): 化学合成、分析、反応の研究で確認する項目です。収率・純度、構造の帰属、再現性、安全性の記載を点検します。

> 注意: この確認項目は文献と一般的な指針から合成した目安で、この分野の専門家による確認はまだ受けていません。分野の慣習と食い違う場合は、指導教員や専門家の判断を優先してください。

Apply to synthesis, reaction studies, spectroscopy, chromatography and chemical analysis.

- **Identity**: evidence that the compound is the one claimed (NMR, MS, IR, elemental analysis, X-ray), with assignments tied to the spectra. Peaks alone without assignment are not identification.
- **Purity and yield**: how purity was measured (HPLC, NMR integration, elemental analysis), whether yield is isolated or crude, and the basis of the yield calculation (limiting reagent, stoichiometry, molar mass).
- **Reproducibility**: exact conditions (temperature, time, atmosphere, concentration, solvent grade, catalyst loading, reagent lot), number of repeats, and error bars. A single run is an observation, not a trend.
- **Side products and mechanism**: unreported by-products, isomers, decomposition, and whether the proposed mechanism is supported by control experiments or only by plausibility.
- **Characterization of properties**: calibration of the measurement, reference standards, measurement conditions (solvent, pH, temperature), and detection limits.
- **Computational support**: basis set and functional stated, comparison with experimental values, and conformer or solvation treatment where relevant.
- **Safety and waste**: hazardous reagents, pressure or temperature risks, and waste handling, as recorded in the source. A missing safety statement is a question, not a finding of misconduct.
- **Data units and significant figures**: consistent units, molar versus mass basis, and figures that match the reported precision.
- **Tools** (optional): `tools/smiles_check.py` for invalid SMILES, duplicates and train/test molecule or scaffold overlap (`requirements/chem.txt`); `tools/uncertainty.py` for propagated errors.
