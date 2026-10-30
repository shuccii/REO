# Long manuscripts (長い原稿の読み方)

概要(日本語): 数万字の修論・論文を、抜けなく、使用量を抑えて点検する手順です。全体の骨格を一度だけ作り、章ごとに読み、最後に章をまたいで照合します。

Use when the material is longer than about 8,000 words or has more than about five chapters.

1. **Skeleton once.** Run `python3 -B <plugin root>/scripts/thesis_skeleton.py <file>` from the user's workspace (Markdown or .docx). Keep its output as the map: headings, first sentences, figure/table captions, strong claim words and long sentences. Do not re-read the whole file to rebuild it.
2. **Claim ledger.** From the abstract, introduction and conclusion, list the central claims with IDs. Every later finding refers to a claim ID.
3. **Number ledger.** While reading, record every reported number that appears in more than one place (sample sizes, metrics, effect sizes, p-values, units) with its location. Numbers are the most common cross-chapter inconsistency.
4. **Chapter passes.** Read chapters in order of their importance to the central claims (methods and results first). For each chapter, record findings with exact locators. If delegation is available, a chapter pass may go to a worker with the claim ledger and number ledger; the lead keeps the cross-chapter checks.
5. **Cross-chapter checks.** Compare the number ledger across chapters; compare each claim in the conclusion with the evidence actually shown in results; check that methods described match those used in results and figures.
6. **Coverage statement.** In 前提, list the chapters read in full, read partly and not read. Do not report a chapter as checked if it was only skimmed through the skeleton.

For a requested repeat review with a dependency ledger, use `tools/reo.py state` as described in `docs/INCREMENTAL_REVIEW.md`. Re-read invalidated nodes and always reconcile abstract/conclusion against results. Unchanged deterministic evidence is only a reuse candidate; previous scientific judgments are never automatically approved. If no trustworthy dependency ledger exists, inspect the relevant full scope rather than assuming a text diff covers all effects.
