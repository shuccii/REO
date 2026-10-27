---
type: llm
weight: 3
---

The response is a review of the manuscript in the prompt. It passes only if it identifies, with the correct mechanism, each defect below, and does not call any decoy (X...) an error.

- G1 condition is completely confounded with library date and sequencing run; ComBat with run as batch cannot separate batch from treatment
- G2 DE defined by unadjusted p < 0.05 while the Abstract claims FDR < 0.05
- G3 circular validation: clustering of genes selected as DE will separate the groups by construction
- G4 replication: two wells per condition from a single donor are not biological replicates; no donor-level inference
- G5 RT-qPCR on the same RNA is not independent validation, and GAPDH (the reference gene) is itself changed (log2FC −0.9)
- G6 enrichment background should be the 11,240 expressed genes, not all 20,000 protein-coding genes
- G7 therapeutic claim for NAFLD goes far beyond an in-vitro, single-donor, single-dose study
- X3 (decoy) DESeq2 applied to raw counts
