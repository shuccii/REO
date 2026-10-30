# 評価用の課題(evals)

Re.O の変更で、指摘の質と出力の形式が落ちていないかを確かめる課題です。入力はすべて架空の原稿・データです。

## Claude Code の評価機能で回す(論文2本と6本の同時点検)

```bash
claude plugin eval . --judge-model opus --runs 2
```

プラグインなしの条件も自動で走り、点数の差が表示されます。`defects` は仕込んだ問題の検出、`format` は出力の型(`output-template.md`)に沿っているかを採点します。

## ファイルを使う課題も含めて比べる(bench)

監査の課題はデータとコードのファイルが必要なので、`evals/bench/` の自前のスクリプトで回します。

```bash
BENCH_MODEL=<固定モデルID> python3 evals/bench/run.py paper_mat,paper_bio,audit_hard,multi_hard 3 6 reo,base
```

```bash
python3 evals/bench/grade.py --model <固定採点モデルID>
```

比較したいプラグインがあれば `COMPARE_PLUGIN=<プラグインのフォルダ>` を付けて、条件に `mi` を加えます。採点基準は `evals/bench/RUBRIC.md` で、実行前に固定しておきます。

## 2026-10-27 の結果

3条件(Re.O 0.9.0、mi-orchestrator 0.3.3、プラグインなし)× 4課題 × 3回で、どの条件も仕込んだ問題をすべて検出し、正しい箇所の誤検出は 0 件でした。今のモデルでは検出力の差は出ないため、以後は出力の形式、計算による確認、費用を主に見ます。

## 2026-10-30 の結果

Re.O 0.12.1 と 0.13.0 で `claude plugin eval` を実行しました。結果と、確かめていないことは [docs/EVALUATION.md](../docs/EVALUATION.md) にまとめています。


## 0.14–0.16の比較基盤

[詳細手順](../docs/BENCHMARK.md)に従い、base / format-only / current / reoを同じ実行条件で比較してください。`BENCH_CURRENT_PLUGIN`は比較元の固定checkoutを指定します。実測usageが取得できない項目はnullです。回数・ツール呼出数でトークンを代用しません。

0.16追加課題: `clean_short,insufficient,partial_pairing,cross_chapter,defense`。[課題の意図と限界](../docs/EVALUATION_CASES.md)を参照。新しい実モデルの結果や削減率はまだありません。
