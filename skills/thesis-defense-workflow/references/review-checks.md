# Tiered review and fine-grained checks

Goal: keep the depth of the assessment while spending less time and fewer tokens. Read the thesis once into a skeleton, check everything cheap on the skeleton, and open the full text only where a check fails or a central claim depends on it. Skipping a check is never the saving; scoping the deep read is.

## Tier 0: skeleton (one command)

```bash
python3 <plugin root>/scripts/thesis_skeleton.py THESIS.docx --out skeleton.md
```

Run it from the user's workspace with the `<plugin root>/` prefix shown above. The skeleton holds the outline, the first sentence of every paragraph, figure/table captions, strong claim wording and overlong sentences. Reuse it for every track and every later round; re-run it only when the thesis file changes (record the file version).

## Tier 1: checks on the skeleton

Mark each item pass / fail / not applicable, with a block or section locator. Any fail moves to Tier 2.

| ID | Check | Look at |
|---|---|---|
| T1 | The introduction's question and the conclusion's answer match | outline, topic sentences of first and last chapters |
| T2 | Topic sentences alone carry the argument; no paragraph opens with detail | topic sentences |
| T3 | Each objective has a result chapter or section and a conclusion | outline vs topic sentences |
| T4 | Strong claim words are supported (developed, established, proved, first, novel) | claims list |
| T5 | One idea per sentence; overlong sentences split | long sentences list |
| T6 | Every figure/table caption states what is shown and under which conditions | captions |
| T7 | Each institutional criterion has a place in the outline | outline vs criteria map |

## Tier 2: targeted deep checks on the full text

Open only the sections a Tier 1 failure points to, plus the sections supporting the one-sentence claim. Each item gets pass / fail / not applicable / unverified, a locator and, for fails, a fix and done condition.

### Figures (each main figure)

| ID | Check |
|---|---|
| F1 | Axes labelled with units; symbols defined |
| F2 | Number of samples (n) stated |
| F3 | Training, validation, test (and extrapolation region, if any) distinguished by color or marker |
| F4 | Error metric defined (RMSE, MAE, R² …) with the split or cross-validation scheme |
| F5 | Uncertainty shown or its absence stated |
| F6 | The figure can be read alone from its caption |

### Methods and process (the most questioned area in thesis defenses)

| ID | Check |
|---|---|
| M1 | Data/material/instrument source, version and quantity stated |
| M2 | Preprocessing, missing values, duplicates and exclusions stated with reasons |
| M3 | Why this method, condition or parameter rather than the simplest alternative |
| M4 | Controls or baselines present and fair |
| M5 | Hyperparameters or experimental settings and how they were chosen |
| M6 | The process could be reproduced from the text plus the stated data/code location |

### Data-driven (machine learning / materials informatics) theses

| ID | Check |
|---|---|
| D1 | Data provenance, count, preprocessing and duplicate removal |
| D2 | Split policy matches the claim (e.g. grouped by composition or structure when claiming generalization); extrapolation evaluated if claimed |
| D3 | Predictive uncertainty handled or its absence stated |
| D4 | Feature importance or model behavior connected to a physical or chemical mechanism, or explicitly left as correlation |
| D5 | No leakage: preprocessing and selection fitted on training data only |

### Interpretation, writing and ethics

| ID | Check |
|---|---|
| I1 | Facts and interpretation separated; alternative explanations considered |
| I2 | Conclusions do not exceed the evidence; limitations stated |
| I3 | Prior work positioned: what was missing and what this work adds |
| E1 | Citations primary and correct; reused figures and text cited and permitted |
| E2 | Reuse of the student's own earlier texts (abstracts, papers) cited and agreed with co-authors |
| E3 | Use of generative AI within what the advisor and institution allow |

For deep validity questions on central claims (statistics, leakage, alternative mechanisms), hand the specific claim to research-review-workflow instead of auditing the whole thesis again.

## Output

One table: ID, status, locator, finding, fix, done condition. Fails go to the issue log. Report the counts per status and which items were unverified and why. Do not report a pass for an item that was not looked at.
