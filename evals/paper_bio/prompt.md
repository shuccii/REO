---
max_turns: 20
allowed_tools: [Read, Glob, Grep, Skill]
---

次の原稿は投稿前の研究論文の原稿です。査読者の立場で、主張と根拠の対応、方法の妥当性、数値の整合性、代替の説明を点検してください。日本語で、重大な指摘から順に、修正案と、修正できたと判断する条件も書いてください。

<manuscript>
# Compound K Reprograms Hepatocyte Energy Metabolism: A Transcriptomic Study

*Fictional manuscript prepared for a review exercise. All data are invented.*

## Abstract

Non-alcoholic fatty liver disease (NAFLD) lacks approved pharmacological treatments. We profiled the transcriptional response of primary human hepatocytes to Compound K, a small molecule identified in a phenotypic screen. RNA sequencing identified 1,523 differentially expressed genes (FDR < 0.05) between Compound K-treated and vehicle-treated cells. Differentially expressed genes were strongly enriched for oxidative phosphorylation (p = 1.2 × 10⁻¹²), and RT-qPCR validated all five genes tested. These results establish Compound K as a promising therapeutic candidate for NAFLD.

## 1. Introduction

Hepatocyte mitochondrial dysfunction contributes to lipid accumulation in NAFLD. Compounds that restore oxidative capacity could therefore slow disease progression. In a phenotypic screen, Compound K reduced lipid droplet area in hepatocytes by 40%. Here we characterize its transcriptional effects.

## 2. Methods

**Cells and treatment.** Cryopreserved primary human hepatocytes from a single donor were thawed and plated in four wells of a collagen-coated plate. After 24 h, two wells were treated with 10 µM Compound K and two wells with 0.1% DMSO (vehicle) for 24 h.

**RNA sequencing.** RNA was extracted, and poly(A) libraries were prepared and sequenced (2 × 100 bp). Sample processing is summarized in Table 1.

Table 1. Sample processing.

| Sample | Condition | Library preparation date | Sequencing run |
|---|---|---|---|
| V1 | Vehicle | 3 March | Run A |
| V2 | Vehicle | 3 March | Run A |
| K1 | Compound K | 17 March | Run B |
| K2 | Compound K | 17 March | Run B |

Reads were aligned to GRCh38 with STAR (default parameters), and gene-level counts were obtained with featureCounts. Genes with fewer than 10 counts in all samples were removed, leaving 11,240 expressed genes. Batch effects were removed with ComBat using sequencing run as the batch variable.

**Differential expression.** Differential expression was tested with DESeq2 on raw counts. Genes with p < 0.05 were considered differentially expressed.

**Clustering.** The differentially expressed genes were clustered hierarchically (Euclidean distance, complete linkage).

**Pathway enrichment.** Enrichment of differentially expressed genes in KEGG pathways was tested with a one-sided hypergeometric test, using all 20,000 human protein-coding genes as the background.

**RT-qPCR.** Five differentially expressed genes were measured by RT-qPCR in the same RNA samples used for sequencing. Expression was normalized to GAPDH using the ΔΔCt method.

## 3. Results

DESeq2 identified 1,523 differentially expressed genes (812 up, 711 down). Table 2 lists selected genes.

Table 2. Selected differentially expressed genes.

| Gene | log2 fold change | p |
|---|---|---|
| NDUFA4 | 1.8 | 3.1 × 10⁻⁴ |
| COX7A2 | 1.6 | 8.0 × 10⁻⁴ |
| ATP5MC1 | 1.4 | 2.2 × 10⁻³ |
| PPARGC1A | 2.1 | 1.5 × 10⁻³ |
| SREBF1 | −1.2 | 4.7 × 10⁻³ |
| GAPDH | −0.9 | 1.9 × 10⁻² |

Hierarchical clustering of the 1,523 differentially expressed genes perfectly separated Compound K-treated from vehicle-treated samples, confirming a robust treatment effect. Oxidative phosphorylation was the most enriched KEGG pathway (p = 1.2 × 10⁻¹²). RT-qPCR confirmed the direction of change for all five genes tested (NDUFA4, COX7A2, ATP5MC1, PPARGC1A, SREBF1).

## 4. Discussion

Compound K induces a coordinated program of mitochondrial gene expression in human hepatocytes, consistent with its effect on lipid droplets. The concordance between RNA-seq and RT-qPCR demonstrates that the findings are robust. Because the cells are of human origin, these results are directly relevant to patients, and Compound K is a promising therapeutic candidate for NAFLD.
</manuscript>
