# Output template (出力の型)

概要(日本語): 研究レビューの出力を毎回同じ構成にするための型です。見出しの順番と名前を変えずに使います。該当しない節は「該当なし」と1行書きます。

Use these sections in this order, with these Japanese headings, for every substantive review. Keep each section short; do not add other top-level sections.

```markdown
# <対象>のレビュー

## 前提
- 対象と範囲(読んだファイル・節・版)/ 見ていないもの
- 使ったプロファイル、または推定した分野・手法・段階
- 使った確認項目(probe)と確認ツール。ツールを実行しなかった場合は「未実行」とその理由
- 独立した確認の有無

## 良い点
- 2〜4 項目

## 主張と根拠の対応
| ID | 主張(場所) | 根拠 | 判定 |
|---|---|---|---|
判定は「支持される / 限定的 / 根拠不足 / 矛盾」のいずれか。

## 指摘(重大な順)
### 1. 【致命的|重大|中|軽】<一行の要約>(場所 → 主張ID)
- 問題点: 仕組みと影響
- 別の説明: (該当する場合)
- 計算による確認: 再計算・ツール出力(該当する場合。実行したコマンドと値)
- 修正案:
- 修正できたと判断する条件:

## 前回からの変化
| 前回の指摘 | 今回の状態 | 根拠 |
|---|---|---|
状態は「解消 / 一部改善 / 未対応 / 再発 / 確認できない」。前回のレビューがなければ「前回のレビューなし」と1行書く。

## 10観点の確認状況
評価した / 一部 / 評価していない(理由)

## 次にやること(優先順)
1.

このレビューは助言です。指導教員の判断や承認、提出の可否の代わりにはなりません。
```

Every finding keeps its own `###` heading and both 修正案 and 修正できたと判断する条件, including 中 and 軽 findings near the end. For a 軽 finding one short line each is enough; do not merge minor findings into a bullet list or drop these two lines to save space. If there are many minor points, combine them into one 軽 finding that still has both lines.

Severity: 致命的 = the central conclusion fails; 重大 = a main claim needs new evidence or narrowing; 中 = the claim survives but reporting or comparison is incomplete; 軽 = clarity and reproducibility details.
