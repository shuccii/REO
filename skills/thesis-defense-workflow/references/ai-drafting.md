# AI drafting mode (opt-in)

By default the student writes and the agent only checks (writing.md). This mode lets the agent draft thesis sections from the student's own material. It is off unless every precondition below is met, and the thesis remains the student's work and responsibility.

## Preconditions (all required)

| ID | Precondition | Where it is recorded |
|---|---|---|
| P1 | The advisor has agreed on the scope of generative-AI use for this thesis (which chapters, drafting vs editing vs translation) | Fact sheet: date, who agreed, scope, as reported by the student |
| P2 | Institutional and program rules on AI use were checked; anything not found is `unconfirmed` and was raised with the advisor | Fact sheet |
| P3 | The student provides the material: results, figures, data and code locations, experimental/computational conditions, notes or an outline in their own words | Input list with file versions |

If P1 or P2 is missing, stop and stay in the default mode. A user's request alone does not satisfy P1.

## What the agent may and may not do

| May | May not |
|---|---|
| Draft a section from the student's outline, notes and results | Add results, numbers, data, references or mechanisms not in the student's material |
| Restructure and reword for logic and clarity | Present uncertain interpretation as established |
| Propose wording at the evidence strength of the material | Write acknowledgments, author contributions or ethics statements beyond the facts given |
| Mark gaps as `[TODO: student]` with what is needed | Fill gaps with plausible content |
| Translate the student's text, marked as such | Submit, upload or send anything |

Every citation in a draft must come from the student's reference list or a source the student confirms; mark any other candidate source as `[CHECK: source]`.

## Ownership loop (per section)

1. **Draft** from the listed inputs only. Each paragraph carries a hidden or bracketed marker `[AI-draft]`.
2. **Trace**: every number, claim and citation in the draft maps to an input (file and location). Untraceable items are removed or marked.
3. **Student rewrite**: the student reads, corrects and rewrites in their own voice; the marker changes to `[student-checked]` only when the student confirms. The agent never changes the marker itself.
4. **Check**: run the tiered review (review-checks.md) on the rewritten section.
5. **Explain test**: in the next question drill, the student explains the section's main claims without the text; failures go to the issue log.

## Record and disclosure

Keep an AI-use log: date, section, inputs used, what was drafted or edited, and the student's confirmation. Remove markers from the submission copy only after all paragraphs are `[student-checked]`. Disclose the use to the advisor, and in the thesis if the program or advisor requires it.

## Done condition

A section is done when every paragraph is `[student-checked]`, every number and citation is traced, the tiered review has no open critical or major item, and the student passed the explain test for that section.
