# Graph-Attention Transfer Learning for Formation Energy Prediction of Ternary Oxides with Calibrated Uncertainty

*Fictional manuscript prepared for a review exercise. All data are invented.*

## Abstract

Accurate prediction of formation energies accelerates the discovery of stable inorganic materials. We present GAT-TL, a graph-attention network pretrained on the Open Quantum Materials Database (OQMD) and fine-tuned on ternary oxides from the Materials Project. GAT-TL achieves a mean absolute error (MAE) of 0.031 eV/atom on a held-out test set, significantly outperforming CGCNN and MEGNet (p = 0.01), and its deep-ensemble prediction intervals are well calibrated. Screening 12,400 hypothetical compositions, we discover 23 new thermodynamically stable ternary oxides.

## 1. Introduction

High-throughput density functional theory (DFT) has produced databases with hundreds of thousands of computed formation energies, yet DFT remains too expensive to screen the combinatorial space of multicomponent oxides. Graph neural networks (GNNs) such as CGCNN and MEGNet learn structure–property relationships directly from crystal graphs. However, ternary oxides are underrepresented in most training sets, and models rarely report whether their uncertainty estimates are reliable. Transfer learning from large databases is a promising way to address the scarcity of ternary-oxide data. Here we (i) pretrain a graph-attention network on OQMD, (ii) fine-tune it on Materials Project ternary oxides, (iii) quantify uncertainty with deep ensembles, and (iv) use the model to search for new stable compounds.

## 2. Data

We collected 1,248 ternary oxide structures from the Materials Project. After removing entries with failed relaxations and exact structural duplicates, 1,102 structures remained, spanning 689 unique compositions. We split the data randomly at the structure level into training (80%), validation (10%) and test (10%) sets; the test set therefore contains 125 structures.

Each structure was converted to a crystal graph with atoms as nodes and neighbours within 8 Å as edges. Node features (element embeddings, electronegativity, covalent radius) and edge features (Gaussian-expanded distances) were standardized using means and standard deviations computed on the training set only.

## 3. Methods

**Pretraining.** GAT-TL was pretrained on all 563,000 formation energies in OQMD for 200 epochs.

**Fine-tuning.** The pretrained network was fine-tuned on the training split. Hyperparameters (learning rate, number of attention heads, dropout, weight decay) were optimized with 200 trials of Bayesian optimization, using MAE on the validation set as the objective. The test set was not used until the final evaluation.

**Baselines.** CGCNN and MEGNet were trained on the same training split with the hyperparameters reported in their original publications.

**Uncertainty.** We trained a deep ensemble of five GAT-TL models with different random seeds and report 95% prediction intervals as the ensemble mean ± 1.96 times the ensemble standard deviation.

**Statistics.** Each model was trained with five random seeds. We compared GAT-TL with each baseline using a paired t-test across seeds.

## 4. Results

### 4.1 Accuracy

Table 1. Test MAE (eV/atom), mean ± standard deviation over five seeds.

| Model | MAE |
|---|---|
| GAT-TL (this work) | 0.031 ± 0.002 |
| CGCNN | 0.037 ± 0.005 |
| MEGNet | 0.036 ± 0.003 |

Table 2. Test MAE (eV/atom) for each seed.

| Seed | GAT-TL | CGCNN |
|---|---|---|
| 1 | 0.029 | 0.036 |
| 2 | 0.033 | 0.031 |
| 3 | 0.030 | 0.038 |
| 4 | 0.034 | 0.035 |
| 5 | 0.029 | 0.045 |

GAT-TL reduces the MAE by 24% relative to CGCNN. A paired t-test across the five seeds gives p = 0.01, confirming that the improvement is statistically significant.

### 4.2 Uncertainty

Table 3. Calibration of the 95% ensemble prediction intervals on the test set.

| Quantity | Value |
|---|---|
| Empirical coverage | 0.81 |
| Mean interval width (eV/atom) | 0.064 |

The ensemble intervals are well calibrated (Table 3), so the model can be trusted to flag unreliable predictions.

### 4.3 Discovery of new stable oxides

We generated 12,400 hypothetical ternary oxide compositions by element substitution into known prototypes. For each composition, we relaxed candidate prototypes with the GAT-TL energy model and kept the lowest-energy structure. Its energy above the convex hull (E_hull) was computed against a hull constructed from the Materials Project training data. Twenty-three candidates have a predicted E_hull below zero (range −0.018 to −0.002 eV/atom) and are therefore thermodynamically stable new compounds.

## 5. Discussion

Because the test set contains compositions not seen during training, these results demonstrate that GAT-TL generalizes to new chemistries. Transfer learning from OQMD supplies chemical knowledge that the small ternary-oxide dataset cannot provide on its own. Combined with calibrated uncertainty, GAT-TL enables reliable discovery of stable materials without additional DFT calculations.

## 6. Conclusion

GAT-TL is an accurate, uncertainty-aware model for formation energies of ternary oxides and has identified 23 new stable compounds.
