# Rubric v2 (fixed before any run, 2026-10-27)

Score each defect 2 = identified with the correct mechanism (and, where relevant, the correct numbers), 1 = mentioned vaguely, partly or with a wrong mechanism, 0 = missing.
Decoys are correct practices. A decoy is "falsely flagged" when the output calls it an error, a leak or a flaw. Mentioning it neutrally or positively is fine.

## paper_mat
- P1 random structure-level split with 1,102 structures but only 689 compositions: polymorphs of the same composition can be in train and test; contradicts the "new chemistries" claim in the Discussion
- P2 pretraining on all of OQMD: OQMD contains the same compositions/structures as the Materials Project test set (pretraining leakage)
- P3 test set size: 10% of 1,102 is about 110, not 125
- P4 "24% reduction" is inconsistent with Table 1 (0.031 vs 0.037 is about 16%)
- P5 p = 0.01 is not supported by Table 2 (paired differences give t about 1.9, p about 0.13 with df = 4); or seeds share one test set so the test is not about generalization
- P6 unequal tuning: 200 Bayesian-optimization trials for GAT-TL vs published defaults for the baselines
- P7 empirical coverage 0.81 contradicts "well calibrated" 95% intervals
- P8 discovery claim: predicted E_hull margins (−0.018 to −0.002 eV/atom) are within the model error and interval width; no DFT verification; hull built from training data only
- X1 (decoy) standardization using training-set statistics only
- X2 (decoy) hyperparameters tuned on the validation set, test set used once

## paper_bio
- G1 condition is completely confounded with library date and sequencing run; ComBat with run as batch cannot separate batch from treatment
- G2 DE defined by unadjusted p < 0.05 while the Abstract claims FDR < 0.05
- G3 circular validation: clustering of genes selected as DE will separate the groups by construction
- G4 replication: two wells per condition from a single donor are not biological replicates; no donor-level inference
- G5 RT-qPCR on the same RNA is not independent validation, and GAPDH (the reference gene) is itself changed (log2FC −0.9)
- G6 enrichment background should be the 11,240 expressed genes, not all 20,000 protein-coding genes
- G7 therapeutic claim for NAFLD goes far beyond an in-vitro, single-donor, single-dose study
- X3 (decoy) DESeq2 applied to raw counts

## audit_hard
- A1 repeated measurements of the same film (sample_id, 4 replicates) are split across folds at the row level: group leakage; "new films" claim unsupported
- A2 k is chosen by the best R² on the test fold itself (selection on test data); k = 1 chosen in every fold
- A3 the reported ± is std / sqrt(5), a standard error, but labelled SD
- A4 temperature units are mixed (Lab A in °C, Lab B in K per README) and never converted; this distorts distances and the r = −0.025 claim
- A5 40 exact duplicate rows (440 rows, 400 unique) inflate the data and leak across folds
- A6 the conclusion that temperature does not matter and need not be controlled is wrong/unsupported (with °C conversion r is about +0.31)
- X4 (decoy) the numbers in report.md match the output of analysis.py
- X5 (decoy) standardization within each training fold

## multi_hard
- H1 p1: survey effort differs (10 h vs 2 h), so richness is confounded with effort (needs rarefaction or effort standardization)
- H2 p2: regression to the mean (enrolled at a symptom flare) and a non-comparable historical control (routine visits)
- H3 p3: extrapolation of the S–N curve to 10⁹ cycles from data that end below 10⁶ cycles; no run-outs or very-high-cycle data
- H4 p4: a concentration-independent half-life indicates first-order kinetics, not second order
- H5 p5: the theoretical speed of sound at 25 °C is about 346 m/s, so 343.2 ± 0.4 m/s does not agree (343 m/s corresponds to about 20 °C)
- H6 p6: accuracy 99.1% equals the majority-class baseline (0.9% fraud); precision/recall or PR-AUC is needed
- H7 a comparison table across all six papers is saved in review_summary.md
- H8 the papers are ranked or prioritized by severity in review_summary.md
- X6 (decoy) p5: two resonance lengths remove the need for an end correction
- X7 (decoy) p6: chronological split and tuning inside the training period
